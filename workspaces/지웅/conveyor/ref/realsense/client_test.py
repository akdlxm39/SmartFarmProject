from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient("127.0.0.1", port=502)

client.connect()

# HR 0 읽기
result = client.read_holding_registers(
    address=0,
    count=10,
    device_id=1    
)
'''
result = client.read_input_registers(
    address=0,
    count=10,
    device_id=1    
)
'''

print(result.registers)
print(result.registers[0])

client.close()


'''
result = client.write_register(
    address=0,
    value=123,
    device_id=1
'''