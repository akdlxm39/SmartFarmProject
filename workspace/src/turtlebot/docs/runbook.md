# TurtleBot 실행 Runbook

## 빠른 시작: 실제 로봇 SLAM

터미널 1 — TurtleBot SBC:

```bash
ssh turtlebot2@192.168.110.172
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_bringup robot.launch.py
```

터미널 2 — Remote PC SLAM:

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
./scripts/check_topics.sh
./scripts/start_slam_real.sh
```

터미널 3 — Teleop:

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
./scripts/start_teleop.sh
```

터미널 4 — Map 저장:

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
./scripts/save_map.sh map/pjt_map_new
```

## 빠른 시작: 실제 로봇 Navigation

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/turtlebot
source scripts/env.sh
./scripts/start_nav_real.sh map/pjt_map.yaml
```

RViz:

1. `2D Pose Estimate`
2. scan/map 겹침 확인
3. `Nav2 Goal`
4. 단일 목표 이동 확인

## 검증 체크리스트

- [ ] Remote PC와 TurtleBot이 같은 네트워크에 있다.
- [ ] Remote PC와 TurtleBot의 `ROS_DOMAIN_ID`가 같다. 현재 장비 기준 `32`.
- [ ] TurtleBot SBC에서 `robot.launch.py`가 실행 중이다.
- [ ] Remote PC에서 `/scan` topic이 보인다.
- [ ] Remote PC에서 `/odom`, `/tf`, `/battery_state` topic이 보인다.
- [ ] Teleop 정지키 `space` / `s`가 동작한다.
- [ ] SLAM map 저장 후 `.yaml`과 `.pgm`이 함께 생성된다.
- [ ] Navigation 실행 시 map 절대 경로를 사용한다.
- [ ] RViz에서 초기 자세 추정 후 scan과 map이 겹친다.
