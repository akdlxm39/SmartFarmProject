# SmartFarm Backend

`workspaces/효진/smartfarm-pjt/backend/`에서 1차 승격한 backend prototype입니다.

## 포함 파일

- `main.py`: backend entry point
- `modbus_client.py`: Modbus client helper
- `modbus_server.py`: prototype Modbus server
- `requirements.txt`: Python dependency list
- `통신구조.png`: 통신 구조 참고 이미지

## 실행 메모

현재는 prototype 상태입니다. 통합 단계에서는 `workspace/src/modbus/shared_server/`의 공통 register map과 endpoint 기준으로 backend Modbus 연동을 맞춥니다.
