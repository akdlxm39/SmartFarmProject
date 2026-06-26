# SmartFarmProject TurtleBot SLAM / Navigation 작업공간

작성일: 2026-06-25  
작업 경로: `/home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot`

## 1. 목적

이 작업공간은 Notion `260511 / SLAM` 자료의 순서를 기준으로 TurtleBot3 Waffle Pi의 SLAM, Navigation2, 프로젝트용 배송 상태 연동을 정리한다.

범위:

1. Remote PC 환경 확인
2. TurtleBot SBC bringup 확인
3. SLAM / Cartographer 실행
4. Teleop으로 지도 작성
5. map 저장
6. Navigation2 실행
7. RViz에서 초기 자세 추정 및 Nav2 Goal 이동
8. 프로젝트 확장용 `turtlebot` ROS2 package와 TurtleBot Modbus heartbeat/status smoke client 준비

## 2. 현재 확인된 환경

### TurtleBot SBC

- SSH: `ssh turtlebot2@192.168.110.172`
- 모델: `TURTLEBOT3_MODEL=waffle_pi`
- ROS: Humble
- Remote 확인 결과: `ROS_DOMAIN_ID=32`
- `turtlebot3_bringup robot.launch.py` 실행 중 확인됨
- `/scan`, `/odom`, `/imu`, `/battery_state`, `/cmd_vel`, `/tf` 등 핵심 topic이 Remote PC에서 확인됨

> Notion 설치 가이드에는 `ROS_DOMAIN_ID=30` 예시가 있지만, 실제 TurtleBot SBC는 `32`로 설정되어 있었다. 이 작업공간의 기본값은 실제 장비 기준 `32`다.

### Remote PC

- ROS 2 Humble 사용
- TurtleBot3 패키지 설치 위치: `/home/ssafy/ros2/turtlebot3_ws/install/setup.bash`
- 확인된 패키지:
  - `turtlebot3_cartographer`
  - `turtlebot3_navigation2`
  - `turtlebot3_gazebo`
  - `turtlebot3_teleop`

## 3. 디렉터리 구조

```text
turtlebot/
├── README.md
├── docs/
│   ├── notion_turtlebot_sequence.md
│   └── runbook.md
├── map/
│   ├── pjt_map.yaml
│   └── pjt_map.pgm
├── ros2_ws/
│   └── src/turtlebot/
├── scripts/
│   ├── env.sh
│   ├── ssh_turtlebot.sh
│   ├── check_topics.sh
│   ├── start_slam_real.sh
│   ├── start_teleop.sh
│   ├── save_map.sh
│   ├── start_nav_real.sh
│   ├── start_sim_world.sh
│   ├── start_slam_sim.sh
│   └── start_nav_sim.sh
└── config/
    └── waypoints.yaml
```

## 4. 실제 TurtleBot SLAM 순서

터미널을 여러 개 열고 아래 순서대로 실행한다.

### 4.1 TurtleBot SBC bringup

```bash
ssh turtlebot2@192.168.110.172
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_bringup robot.launch.py
```

이미 실행 중이면 새로 실행하지 않는다.

### 4.2 Remote PC 환경 로드

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
```

### 4.3 Topic 확인

```bash
./scripts/check_topics.sh
```

핵심 확인 topic:

- `/scan`
- `/odom`
- `/imu`
- `/battery_state`
- `/cmd_vel`
- `/tf`

### 4.4 SLAM 실행

```bash
./scripts/start_slam_real.sh
```

### 4.5 Teleop으로 지도 탐색

새 터미널:

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
./scripts/start_teleop.sh
```

주의:

- 직진/회전 속도를 급격하게 바꾸지 않는다.
- 가능한 모든 구석을 천천히 스캔한다.
- 충돌 위험이 있으면 `space` 또는 `s`로 즉시 정지한다.

### 4.6 map 저장

```bash
./scripts/save_map.sh map/pjt_map_new
```

기존 map을 덮어쓰려면 명시적으로:

```bash
./scripts/save_map.sh map/pjt_map
```

## 5. Navigation 실행 순서

Navigation은 저장된 map이 있어야 실행한다.

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
./scripts/start_nav_real.sh map/pjt_map.yaml
```

RViz에서 반드시 수행:

1. `2D Pose Estimate`로 실제 위치와 방향 지정
2. LDS scan이 map과 겹치는지 확인
3. 필요 시 teleop으로 제자리 회전하여 AMCL particle 수렴 확인
4. `Nav2 Goal`로 단일 목표 이동 테스트

## 6. 프로젝트용 ROS2 package

Notion 관통 프로젝트 메모에 따라 `turtlebot` package를 준비했다.

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot/ros2_ws
colcon build --symlink-install --packages-select turtlebot
source install/setup.bash
```

현재 포함 기능:

- `turtlebot_modbus_heartbeat`: TurtleBot 상태/배터리/heartbeat를 Modbus `40051~40070` TurtleBot block에 쓰기 위한 smoke client

Dry-run 예시:

```bash
ros2 run turtlebot turtlebot_modbus_heartbeat --once --dry-run
```

실제 Modbus server write 예시:

```bash
ros2 run turtlebot turtlebot_modbus_heartbeat --host 192.168.110.109 --port 50200
```

## 7. 다음 작업

1. 실제 SLAM 실행 후 새 map 저장
2. `map/pjt_map.yaml` 또는 새 map으로 Navigation 실행
3. Nav2 Goal 단일 이동 성공 확인
4. TurtleBot Modbus heartbeat를 dry-run → 실제 server 순서로 검증
5. 배송 waypoint(`home`, `pickup_wait`, `delivery_goal`) 실측 좌표로 갱신
