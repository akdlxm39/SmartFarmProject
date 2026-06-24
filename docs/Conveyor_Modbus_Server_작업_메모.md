# Conveyor Modbus Server 작업 메모

작성일: 2026-06-24  
범위: 이 문서는 이 쓰레드에서 집중 관리할 **Modbus TCP server / shared register layer** 실행 메모다.

## 1. 문서 검토 기준
검토한 문서:
- `README.md`
- `docs/진행_로그.md`
- `docs/작업_결정_메모.md`
- `docs/R&R_초안.md`
- `docs/WBS_검토_메모.md`
- `docs/WBS_재검토_메모.md`
- `docs/Conveyor_작업_메모.md`
- `docs/Conveyor_ROI_Modbus_구현_계획.md`
- `docs/Conveyor_Modbus_Async_RaspberryPi_전환_계획.md`
- `docs/Conveyor_Pi_Modbus_Client_Controller_구현_계획.md`
- `workspaces/지웅/conveyor/README.md`
- `workspaces/지웅/conveyor/pi_controller/README.md`

## 2. 이 쓰레드의 집중 범위
이 쓰레드에서는 **컨베이어 Modbus TCP server와 shared register map**만 집중해서 정리한다.

### 직접 다룰 것
- Modbus server endpoint와 네트워크 접근성
- holding register `40021~40030` 주소/enum/소유권
- PC vision client와 Raspberry Pi client가 같은 server를 볼 때 생기는 race condition 방지
- `pymodbus==3.13.1` 기준 API와 zero-based address 변환
- server smoke test, read/write 검증, 장애 시 확인 순서

### 인터페이스 수준에서만 언급할 것
- PC/ROS2 D435i/OpenCV 감지 노드 내부 구현
- Raspberry Pi GPIO motor controller 내부 구현
- Dobot 수확/적재 시퀀스
- Django/Vue 대시보드 화면 구현

## 3. 현재 확정된 구조
- Modbus server endpoint는 `192.168.110.109:50200`이다.
- Raspberry Pi 5(`ssafy@192.168.110.139`)는 **Modbus server가 아니라 client**다.
- PC/ROS2 vision node도 Modbus client다.
- server는 장치 제어 로직을 직접 수행하지 않고, shared holding register 상태를 유지하는 중심 레이어로 둔다.
- 컨베이어 실제 GPIO 제어와 실제 모터 상태 판정은 Raspberry Pi client가 담당한다.
- 큐브 감지 결과와 운전 명령은 PC vision/manual client가 server register에 쓴다.
- 기준 라이브러리는 `pymodbus==3.13.1`이다.

## 4. Register map / ownership
| Register | Protocol address | Name | 주 쓰기 주체 | 주 읽기 주체 | 값/비고 |
|---:|---:|---|---|---|---|
| 40021 | 20 | `conveyor_command` | PC vision 또는 manual client | Raspberry Pi | `0 stop`, `1 run_clockwise`, `2 run_counter_clockwise`, `3 reset`, `4 emergency_stop` |
| 40022 | 21 | `conveyor_speed_cmd` | PC vision 또는 manual client | Raspberry Pi | MVP에서는 `0=default`, `1~100=속도 scale` |
| 40023 | 22 | `conveyor_status` | Raspberry Pi | PC/dashboard | `0 idle`, `1 running`, `2 delivered`, `3 error`, `4 emergency_stopped` |
| 40024 | 23 | `conveyor_error_code` | Raspberry Pi | PC/dashboard | `0 none`, `1 modbus_connect_failed`, `2 read_failed`, `3 write_failed`, `4 gpio_init_failed`, `5 invalid_command`, `6 local_emergency_stop` |
| 40025 | 24 | `cube_detected` | PC vision | Raspberry Pi/dashboard | `0/1` |
| 40026 | 25 | `cube_color` | PC vision | Raspberry Pi/dashboard | `0 none`, `1 red`, `2 green`, `3 unknown` |
| 40027 | 26 | `last_vision_event` | PC vision | Raspberry Pi/dashboard | `0 none`, `1 cube_detected`, `2 cube_lost`, `3 delivered`, `4 error`, `5 emergency_stop` |
| 40028 | 27 | `reserved_conveyor_1` | reserved | reserved | heartbeat/sequence 후보 |
| 40029 | 28 | `reserved_conveyor_2` | reserved | reserved | Pi uptime/local emergency 후보 |
| 40030 | 29 | `reserved_conveyor_3` | reserved | reserved | 확장 예비 |

주소 변환 기준:
- 문서 표기는 일반 holding register 번호 `40021~40030`을 사용한다.
- `pymodbus` protocol address는 zero-based 기준 `20~29`를 사용한다.
- 실제 server가 literal `40021` 주소를 요구하는 특수 구현이면 client 옵션에서 zero-based 변환을 끄고 재검증한다.

## 5. Server 관점 안전 규칙
1. `40023/40024`는 Raspberry Pi가 실제 모터 상태 기준으로 갱신한다.
2. PC vision/manual client는 `40023/40024`를 덮어쓰지 않는다.
3. server는 여러 client가 붙을 수 있으므로, 쓰기 주체를 register별로 명확히 분리한다.
4. emergency stop은 PC manual command(`40021=4`)와 Pi local button latch를 모두 허용하되, Pi local emergency latch가 켜져 있으면 run command를 무시한다.
5. server 연결 실패 시 Raspberry Pi는 모터를 안전 정지하고 reconnect backoff를 둔다.

## 6. 현재 확인된 상태
2026-06-24 이 PC에서 TCP 접근성을 확인한 결과:

```text
192.168.110.109:50200 CONNECT FAIL TimeoutError: timed out
192.168.110.139:22 CONNECT FAIL TimeoutError: timed out
```

해석:
- 현재 이 실행 환경에서는 Modbus server와 Raspberry Pi SSH 모두 TCP 연결이 닿지 않는다.
- 이전 Pi 배포 로그의 `No route to host`와 같은 계열의 네트워크/라우팅/전원/방화벽 문제로 보고, 실제 server 연동은 네트워크 확인 후 재검증해야 한다.

## 7. 다음 검증 순서
1. `192.168.110.109` 장비/프로세스가 실제로 켜져 있는지 확인한다.
2. server 장비에서 `50200/tcp` listen 상태를 확인한다.
3. PC와 Pi가 같은 네트워크/VLAN에 있고 `192.168.110.0/24` 대역으로 route가 잡히는지 확인한다.
4. PC에서 `192.168.110.109:50200` TCP connect를 먼저 확인한다.
5. `pymodbus==3.13.1` client로 `40021~40030` read smoke test를 수행한다.
6. dry-run manual write로 `40021 stop/run/emergency_stop`을 쓰고 다시 읽어 값 보존을 확인한다.
7. Pi controller를 `--dry-run-motor`로 실행해 command polling과 `40023/40024` status write를 확인한다.
8. 마지막에 실제 GPIO 구동을 연결한다.

## 8. 열려 있는 질문
- `192.168.110.109`의 Modbus server는 이미 별도 장비에서 제공되는가, 아니면 프로젝트에서 직접 실행해야 하는가?
- server 구현이 `pymodbus` zero-based address(`20~29`)를 쓰는가, literal register(`40021~40030`)를 쓰는가?
- server가 여러 client 동시 접속/write를 허용하는가?
- dashboard/백엔드는 Modbus server에 직접 붙을 것인가, 아니면 ROS/DB를 통해 읽을 것인가?
