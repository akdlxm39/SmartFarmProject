#pip install pymodbus==3.13.1
import asyncio
import logging

from pymodbus.server import StartAsyncTcpServer
from pymodbus.simulator import SimData, SimDevice, DataType

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# Holding Register 100개 생성
hr_block = SimData(address=0, values=[1]*110, datatype=DataType.REGISTERS)
ir_block = SimData(address=0, values=[22]*10, datatype=DataType.REGISTERS)

device = SimDevice(
    id=1,
    simdata=(
        [SimData(0, count=100, values=False, datatype=DataType.BITS)],          # coils
        [SimData(0, count=100, values=False, datatype=DataType.BITS)],          # discrete inputs
        [hr_block],  # holding registers
        [ir_block],  # input registers
    )
)

async def main():
    await StartAsyncTcpServer(
        context=[device],
        address=("127.0.0.1", 502)
    )

if __name__ == "__main__":
    asyncio.run(main())


'''
device = SimDevice(
    id=1,
    simdata=(
        [SimData(0, count=100, values=False, datatype=DataType.BITS)],       # coils
        [SimData(0, count=100, values=False, datatype=DataType.BITS)],       # discrete inputs
        [SimData(0, count=100, values=0, datatype=DataType.REGISTERS)],      # holding registers
        [SimData(0, count=100, values=0, datatype=DataType.REGISTERS)],      # input registers
    )
)

튜플순서
(coils, discrete_inputs, holding_registers, input_registers)
데이터 넣기 100개 
hr_block = SimData(
    address=0,
    values=[1, 2, 3] + [0] * 97,
    datatype=DataType.REGISTERS,
)
'''