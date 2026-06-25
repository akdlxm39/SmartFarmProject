import asyncio
import logging
from pymodbus.server import StartAsyncTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("modbus_server")

async def run_server():
    # Coils(co) 데이터 스토어 생성: 0번지 주소부터 시작하여 기본값 False로 100개 초기화
    # 0번 Coil: 컨베이어 가동 여부 (True: 운영중, False: 대기중)
    store = ModbusSlaveContext(
        co=ModbusSequentialDataBlock(0, [False] * 100),
        di=ModbusSequentialDataBlock(0, [0] * 100),
        hr=ModbusSequentialDataBlock(0, [0] * 100),
        ir=ModbusSequentialDataBlock(0, [0] * 100)
    )
    context = ModbusServerContext(slaves=store, single=True)
    
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'SSAFY'
    identity.ProductCode = 'SmartFarm'
    identity.VendorUrl = 'http://ssafy.com/'
    identity.ProductName = 'SmartFarm Conveyor Simulator'
    identity.ModelName = 'ConveyorSim'
    identity.MajorMinorRevision = '1.0'
    
    log.info("Starting Modbus TCP Server on 192.168.110.107:50200...")
    
    # 127.0.0.1의 50200 포트로 Modbus TCP 서버 실행
    await StartAsyncTcpServer(
        context=context,
        identity=identity,
        address=("192.168.110.107", 50200)
    )

if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        log.info("Modbus TCP Server stopped by user.")
