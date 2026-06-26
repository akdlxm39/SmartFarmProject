import logging
import asyncio
from pymodbus.client import AsyncModbusTcpClient

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("modbus")

# pymodbus 라이브러리 자체의 연결 시도 실패 로그(CRITICAL/ERROR) 도배를 방지하기 위해 로그 레벨을 올립니다.
logging.getLogger("pymodbus").setLevel(logging.WARNING)

# Pymodbus uses zero-based protocol addresses, so 40021 maps to address 20.
REGISTER_CONVEYOR_COMMAND = 20
REGISTER_CONVEYOR_STATUS = 22

COMMAND_STOP = 0
COMMAND_RUN_CLOCKWISE = 1

STATUS_IDLE = 0
STATUS_RUNNING = 1


class ConveyorModbusClient:
    def __init__(self, host='192.168.110.109', port=50200):
        self.host = host
        self.port = port
        self.client = None
        self.is_connected = False
        
        # 실제 장비가 없을 때를 대비한 가상 상태 (Simulation state)
        self.sim_status = "대기중"

    async def connect(self):
        if self.client is None:
            self.client = AsyncModbusTcpClient(self.host, port=self.port, timeout=1.0)
            
        try:
            self.is_connected = await self.client.connect()
            if self.is_connected:
                log.info(f"Connected to Modbus Server at {self.host}:{self.port}")
            else:
                log.warning(f"Failed to connect to Modbus Server at {self.host}:{self.port}. Running in simulation mode.")
        except Exception as e:
            log.error(f"Connection error: {e}")
            self.is_connected = False
        return self.is_connected

    async def read_status(self):
        """컨베이어 상태 읽기 (모드버스 통신)"""
        if not self.is_connected:
            await self.connect()

        if self.is_connected:
            try:
                # 40023 레지스터(address 22)에서 상태 읽기
                result = await self.client.read_holding_registers(REGISTER_CONVEYOR_STATUS, count=1, device_id=1) 
                if result.isError():
                    log.error(f"Error reading holding registers")
                    return "오류"
                else:
                    status_val = result.registers[0]
                    return "운영중" if status_val == STATUS_RUNNING else "대기중"
            except Exception as e:
                log.error(f"Read error: {e}")
                self.is_connected = False
                return "오류"
        else:
            # 장비가 연결되지 않았다면 가상 상태 반환 (디버깅 용도)
            return self.sim_status

    async def read_crop_counts(self):
        """작물 수확 개수(토마토, 무 양품/불량) 읽기"""
        if not self.is_connected:
            await self.connect()

        if self.is_connected:
            try:
                # 40081 (address 80) 부터 12개 레지스터 읽기 (Tomato Good/Bad ~ Radish Good/Bad)
                result = await self.client.read_holding_registers(80, count=12, device_id=1)
                if result.isError():
                    log.error("Error reading crop count registers")
                    return None
                else:
                    regs = result.registers
                    # u32 형식으로 결합: LO + (HI << 16)
                    counts = {
                        "tomato": {
                            "good": regs[0] + (regs[1] << 16),
                            "bad": regs[2] + (regs[3] << 16)
                        },
                        "radish": {
                            "good": regs[8] + (regs[9] << 16),
                            "bad": regs[10] + (regs[11] << 16)
                        }
                    }
                    return counts
            except Exception as e:
                log.error(f"Read crop counts error: {e}")
                self.is_connected = False
                return None
        else:
            return None

    async def write_control(self, is_running: bool):
        """컨베이어 가동/중지 제어 (모드버스 통신)"""
        if not self.is_connected:
            await self.connect()
            
        if self.is_connected:
            try:
                # 40021 레지스터(address 20)에 명령어 쓰기
                command_val = COMMAND_RUN_CLOCKWISE if is_running else COMMAND_STOP
                result = await self.client.write_register(REGISTER_CONVEYOR_COMMAND, command_val, device_id=1)
                if result.isError():
                    log.error(f"Error writing register")
                    return False
                return True
            except Exception as e:
                log.error(f"Write error: {e}")
                self.is_connected = False
                return False
        else:
            # 장비가 연결되지 않았다면 가상 상태 업데이트 (디버깅 용도)
            self.sim_status = "운영중" if is_running else "대기중"
            return True

    async def close(self):
        if self.is_connected:
            close_func = getattr(self.client, "close", None)
            if close_func is not None:
                maybe = close_func()
                if hasattr(maybe, "__await__"):
                    await maybe
            self.is_connected = False
            log.info("Modbus connection closed")

# 싱글톤 인스턴스 생성
modbus_service = ConveyorModbusClient()
