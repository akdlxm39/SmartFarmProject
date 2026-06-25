import logging
from pymodbus.client import ModbusTcpClient

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("modbus")

# pymodbus 라이브러리 자체의 연결 시도 실패 로그(CRITICAL/ERROR) 도배를 방지하기 위해 로그 레벨을 올립니다.
logging.getLogger("pymodbus").setLevel(logging.WARNING)


class ConveyorModbusClient:
    def __init__(self, host='192.168.110.107', port=50200):
        self.host = host
        self.port = port
        # pymodbus 3.x 에서는 ModbusTcpClient를 사용합니다.
        self.client = ModbusTcpClient(self.host, port=self.port)
        self.is_connected = False
        
        # 실제 장비가 없을 때를 대비한 가상 상태 (Simulation state)
        self.sim_status = "대기중"

    def connect(self):
        try:
            self.is_connected = self.client.connect()
            if self.is_connected:
                log.info(f"Connected to Modbus Server at {self.host}:{self.port}")
            else:
                log.warning(f"Failed to connect to Modbus Server at {self.host}:{self.port}. Running in simulation mode.")
        except Exception as e:
            log.error(f"Connection error: {e}")
            self.is_connected = False
        return self.is_connected

    def read_status(self):
        """컨베이어 상태 읽기 (모드버스 통신)"""
        if not self.is_connected:
            self.connect()

        if self.is_connected:
            try:
                # [수정 필요] 실제 컨베이어 장비의 상태를 읽어올 코일(Coil) 번호를 입력하세요.
                # 예시: 0번지 코일 1개를 읽어옴
                result = self.client.read_coils(0, count=1) 
                if result.isError():
                    log.error(f"Error reading coils")
                    return "오류"
                else:
                    is_running = result.bits[0]
                    return "운영중" if is_running else "대기중"
            except Exception as e:
                log.error(f"Read error: {e}")
                self.is_connected = False
                return "오류"
        else:
            # 장비가 연결되지 않았다면 가상 상태 반환 (디버깅 용도)
            return self.sim_status

    def write_control(self, is_running: bool):
        """컨베이어 가동/중지 제어 (모드버스 통신)"""
        if not self.is_connected:
            self.connect()
            
        if self.is_connected:
            try:
                # [수정 필요] 실제 컨베이어를 제어할 코일 번호를 입력하세요.
                # 예시: 0번지 코일에 제어값(True/False) 쓰기
                result = self.client.write_coil(0, is_running)
                if result.isError():
                    log.error(f"Error writing coil")
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

    def close(self):
        if self.is_connected:
            self.client.close()
            self.is_connected = False
            log.info("Modbus connection closed")

# 싱글톤 인스턴스 생성
modbus_service = ConveyorModbusClient()
