# conveyor_vision_test

D435i color topic을 받아서 기존 `conveyor_roi_topview.json` 기준으로 top-view 변환을 수행하고, top-view 창에 컨베이어 ROI와 빨간색/초록색 물체 bounding box를 표시하는 간단 테스트 ROS2 패키지다.

## 빌드

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select conveyor_vision_test
source install/setup.bash
```

## 실행

기본값은 다음을 사용한다.

- image topic: `/camera/camera/color/image_raw`
- ROI config: `/home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor/config/conveyor_roi_topview.json`
- annotated publish topic: `/conveyor/topview_annotated`

```bash
ros2 run conveyor_vision_test topview_color_detector
```

창이 너무 크면:

```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p display_scale:=0.7
```

토픽이나 설정 파일을 바꾸려면:

```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p image_topic:=/camera/camera/color/image_raw \
  -p config_path:=/home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor/config/conveyor_roi_topview.json
```

GUI 없이 annotated image topic만 publish하려면:

```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p show_windows:=false
```

## Modbus TCP 연동

`pymodbus==3.13.1`를 사용한다. 현재 환경에는 아래처럼 설치했다.

```bash
/usr/bin/python3 -m pip install --user pymodbus==3.13.1
```

안전을 위해 `modbus_enabled` 기본값은 `false`다. 실제 컨베이어 서버로 쓰려면 명시적으로 켠다.

```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p modbus_enabled:=true \
  -p modbus_host:=192.168.110.109 \
  -p modbus_port:=50200 \
  -p conveyor_run_command:=run_clockwise \
  -p conveyor_speed_cmd:=100
```

반시계 방향으로 돌리고 싶으면:

```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p modbus_enabled:=true \
  -p conveyor_run_command:=run_counter_clockwise
```

실제 TCP 연결 없이 로그만 확인하려면:

```bash
ros2 run conveyor_vision_test topview_color_detector --ros-args \
  -p modbus_enabled:=true \
  -p modbus_dry_run:=true \
  -p show_windows:=false
```

### Holding register map

pymodbus에는 기본적으로 `40021`을 protocol address `20`으로 변환해서 쓴다. 컨베이어는 `40021~40030`을 사용하며, ROS 비전 노드는 command/vision register만 쓰고 Pi가 실제 물리 상태 register를 쓴다. 서버가 literal `40021` 주소를 요구하면 `modbus_zero_based_addresses:=false`로 바꾼다.

| Register | Name | Owner | 값 |
|---:|---|---|---|
| 40021 | `conveyor_command` | PC/ROS vision 또는 manual client write, Pi read | `0 stop`, `1 run_clockwise`, `2 run_counter_clockwise`, `3 reset`, `4 emergency_stop` |
| 40022 | `conveyor_speed_cmd` | PC/ROS vision 또는 manual client write, Pi read | 속도 명령값 |
| 40023 | `conveyor_status` | Pi write, PC/ROS vision read | `0 idle`, `1 running`, `2 delivered`, `3 error`, `4 emergency_stopped` |
| 40024 | `conveyor_error_code` | Pi write, PC/ROS vision read | `0 none`, `1 modbus_write_failed`, `2 invalid_command`, `6 local_emergency_stop` |
| 40025 | `cube_detected` | PC/ROS vision write | `0 false`, `1 true` |
| 40026 | `cube_color` | PC/ROS vision write | `0 none`, `1 red`, `2 green`, `3 unknown` |
| 40027 | `last_vision_event` | PC/ROS vision write | `0 none`, `1 cube_detected`, `2 cube_lost`, `3 delivered`, `4 error`, `5 emergency_stop` |
| 40028~40030 | reserved | future | 컨베이어 확장 예비 |

노드 상태 흐름:

1. 매 Modbus write 직전에 Pi-owned `40023/40024`를 읽는다.
2. 빨강/초록 큐브 감지: status가 `idle/running/delivered`이면 `40021=run_clockwise/run_counter_clockwise`, `40022=speed`, `40025=1`, `40026=red/green`, `40027=cube_detected`를 쓴다.
3. 일시 미검출: status가 허용 상태이면 `40021` run을 유지하고, `40025=0`, `40027=cube_lost`를 쓴다.
4. `disappear_stable_frames` 기본 10프레임 연속 미검출: status가 허용 상태이면 `40021=stop`, `40025=0`, `40027=delivered`를 쓴다.
5. Pi가 `40023=emergency_stopped`이면 **명령 register(40021/40022)를 쓰지 않고**, vision register(40025~40027)만 갱신한다.
6. Pi가 `40023=error`이면 비전 노드는 run/reset을 내리지 않고, stop 요청만 허용한다. status를 읽지 못하면 fail-safe로 command 없이 vision register만 쓴다.

### 수동 명령

긴급정지/리셋/수동 구동은 별도 명령으로 바로 보낼 수 있다.

```bash
ros2 run conveyor_vision_test conveyor_modbus_command emergency_stop
ros2 run conveyor_vision_test conveyor_modbus_command reset
ros2 run conveyor_vision_test conveyor_modbus_command run_clockwise --speed 100
ros2 run conveyor_vision_test conveyor_modbus_command run_counter_clockwise --speed 100
ros2 run conveyor_vision_test conveyor_modbus_command stop
```

## 동작

1. `sensor_msgs/Image`를 OpenCV BGR frame으로 변환한다.
2. JSON의 `topview.perspective_matrix_raw_to_topview`와 `topview.size_wh`로 top-view 이미지를 만든다.
3. JSON의 `conveyor_roi.quad_xy_tl_tr_br_bl` 또는 `conveyor_roi.xyxy`를 top-view ROI로 표시한다.
4. ROI 내부에서 HSV 기준 빨강/초록 blob을 찾고 bounding box를 그린다.
5. 결과 이미지를 OpenCV 창에 표시하고 `/conveyor/topview_annotated`로 publish한다.

## 주요 파라미터

| 파라미터 | 기본값 | 설명 |
|---|---:|---|
| `image_topic` | `/camera/camera/color/image_raw` | D435i color image topic |
| `config_path` | conveyor ROI JSON 절대경로 | top-view/ROI 보정 파일 |
| `show_windows` | `true` | OpenCV 창 표시 여부 |
| `publish_annotated` | `true` | annotated image publish 여부 |
| `annotated_topic` | `/conveyor/topview_annotated` | 결과 이미지 topic |
| `display_scale` | `1.0` | 창 표시 배율 |
| `min_area` | `250.0` | bounding box로 인정할 최소 contour area |
| `morph_kernel_size` | `5` | 노이즈 제거용 morphology kernel 크기 |
| `allow_dimension_mismatch` | `false` | live frame 해상도와 calibration 해상도가 달라도 임시 실행할지 여부 |
| `disappear_stable_frames` | `10` | 연속 미검출 후 delivered/stop 처리할 프레임 수 |
| `modbus_enabled` | `false` | Modbus TCP 쓰기 활성화 여부 |
| `modbus_host` | `192.168.110.109` | Modbus TCP server IP |
| `modbus_port` | `50200` | Modbus TCP server port |
| `modbus_unit_id` | `1` | Modbus unit/slave id |
| `modbus_zero_based_addresses` | `true` | 40021을 pymodbus address 20으로 변환할지 여부 |
| `modbus_dry_run` | `false` | 실제 TCP 연결 없이 로그만 남길지 여부 |
| `conveyor_run_command` | `run_clockwise` | 감지 시 보낼 구동 방향: `run_clockwise` 또는 `run_counter_clockwise` |
| `conveyor_speed_cmd` | `100` | 40022 속도 명령값 |
| `modbus_shutdown_command` | `stop` | 노드 종료 시 보낼 명령: `stop` 또는 `emergency_stop` |

## 주의

- live frame 해상도와 calibration JSON의 `raw_frame.width/height`가 다르면 기본적으로 처리를 중단한다. 이 경우 `select_conveyor_roi.py`를 다시 실행해서 좌표를 재설정한다.
- 지금 노드는 분류기가 아니라 컨베이어 ROI/색상 검출 smoke test 용도다.
