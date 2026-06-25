import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from modbus_client import modbus_service

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

async def status_poller():
    while True:
        # 모드버스를 통해 컨베이어 상태 조회
        status = modbus_service.read_status()
        
        # 현재 시간 문자열 포맷
        now_str = datetime.now().strftime("%H:%M:%S")
        
        await manager.broadcast({
            "type": "conveyor_status",
            "data": {
                "status": status,
                "timestamp": now_str
            }
        })
        
        # 1초 주기로 폴링 (필요 시 조절 가능)
        await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 모드버스 클라이언트 초기 연결 시도
    modbus_service.connect()
    # 백그라운드에서 주기적으로 모드버스 상태를 읽어 프론트엔드로 브로드캐스팅
    poller_task = asyncio.create_task(status_poller())
    yield
    # 서버 종료 시 백그라운드 태스크 취소 및 모드버스 통신 안전 종료
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass
    modbus_service.close()

app = FastAPI(lifespan=lifespan)

# 프론트엔드 연동을 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """프론트엔드(Vue.js)와 실시간 양방향 통신을 담당하는 웹소켓 엔드포인트"""
    await manager.connect(websocket)
    try:
        while True:
            # 프론트엔드에서 보낸 메시지(제어 명령) 수신
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "control_conveyor":
                action = message.get("action")  # 'start' or 'stop'
                is_running = (action == "start")
                
                # 모드버스 제어 코일 쓰기
                success = modbus_service.write_control(is_running)
                
                # 제어 결과를 클라이언트들에게 알림
                await manager.broadcast({
                    "type": "control_result",
                    "data": {
                        "device": "conveyor",
                        "success": success,
                        "action": action
                    }
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

