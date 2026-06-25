# Conveyor

컨베이어의 Raspberry Pi 제어와 GPIO 진단, Modbus client를 모아둔 비ROS 영역입니다.

## 구조

- `pi_controller/`: 저수준 motor/button helper, motion profile, 단위 테스트
- `gpio/`: Raspberry Pi GPIO/Smart Factory Shield actuator diagnostic scripts
- `modbus_client/`: shared Modbus server를 읽고 실제 conveyor GPIO를 구동하는 client/controller

공통 Modbus TCP server/register map은 `workspace/src/modbus/shared_server/`를 기준으로 합니다.
