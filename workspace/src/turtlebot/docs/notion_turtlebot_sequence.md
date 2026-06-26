# Notion TurtleBot SLAM / Navigation 절차 요약

출처: Notion `260511 / SLAM` 및 하위 TurtleBot 관련 페이지  
정리일: 2026-06-25

## 1. 설치/환경 핵심

Remote PC:

```bash
sudo apt install ros-humble-gazebo-*
sudo apt install ros-humble-cartographer ros-humble-cartographer-ros
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup
source /opt/ros/humble/setup.bash
mkdir -p ~/turtlebot3_ws/src
cd ~/turtlebot3_ws/src
git clone -b humble https://github.com/ROBOTIS-GIT/DynamixelSDK.git
git clone -b humble https://github.com/ROBOTIS-GIT/turtlebot3_msgs.git
git clone -b humble https://github.com/ROBOTIS-GIT/turtlebot3.git
cd ~/turtlebot3_ws
colcon build --symlink-install
echo 'source ~/turtlebot3_ws/install/setup.bash' >> ~/.bashrc
echo 'export ROS_DOMAIN_ID=30 #TURTLEBOT3' >> ~/.bashrc
echo 'source /usr/share/gazebo/setup.sh' >> ~/.bashrc
```

현재 실기기 확인 결과는 `ROS_DOMAIN_ID=32`이므로 이 프로젝트 작업공간은 32를 기본값으로 사용한다.

## 2. Bringup

사전 확인:

- Remote PC와 TurtleBot이 같은 무선 네트워크에 있어야 한다.
- Remote PC와 TurtleBot SBC의 `ROS_DOMAIN_ID`가 같아야 한다.

TurtleBot SBC:

```bash
ssh turtlebot2@192.168.110.172
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_bringup robot.launch.py
```

Remote PC:

```bash
ros2 topic list
ros2 service list
ros2 launch turtlebot3_bringup rviz2.launch.py
```

## 3. Basic operation

Remote PC:

```bash
export TURTLEBOT3_MODEL=waffle_pi
ros2 run turtlebot3_teleop teleop_keyboard
```

키:

- `w` / `x`: 직진 / 후진 속도 조절
- `a` / `d`: 좌회전 / 우회전 속도 조절
- `space` / `s`: 정지

## 4. SLAM 실제 로봇

주의:

- SLAM은 Remote PC에서 실행한다.
- TurtleBot SBC에는 GUI tool이 없으므로 시각화는 Remote PC에서 처리한다.
- SLAM 전에 TurtleBot SBC bringup이 먼저 실행되어야 한다.

Remote PC:

```bash
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_cartographer cartographer.launch.py
```

Teleop:

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

Map 저장:

```bash
ros2 run nav2_map_server map_saver_cli -f ~/<map_file_name>
```

## 5. Navigation 실제 로봇

주의:

- 로봇은 반드시 바닥에 놓고 실행한다.
- Navigation 실행 전 map이 준비되어 있어야 한다.
- map 경로는 절대 경로 사용을 권장한다.

TurtleBot SBC:

```bash
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_bringup robot.launch.py
```

Remote PC:

```bash
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_navigation2 navigation2.launch.py map:=/home/ssafy/map.yaml
```

RViz:

1. `2D Pose Estimate` 클릭
2. 실제 로봇 위치와 방향을 map 위에 지정
3. LDS scan과 map이 겹치는지 확인
4. `Nav2 Goal` 클릭 후 목표 위치/방향 지정

## 6. Gazebo SLAM simulation

```bash
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=True
ros2 run turtlebot3_teleop teleop_keyboard
ros2 run nav2_map_server map_saver_cli -f ~/map_gazebo
```

## 7. Gazebo Navigation simulation

```bash
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=true map:=/home/ssafy/my_map.yaml
```

RViz에서 2D Pose Estimate → Nav2 Goal 순서로 확인한다.

## 8. 관통 프로젝트 메모

Notion 관통 프로젝트 메모:

1. `ros2 launch turtlebot3_gazebo turtlebot_world.launch.py`
2. `ros2 launch turtlebot3_navigation2 navigation2.launch.py map:=/home/ssafy/my_map.yaml`
3. `ssafy_ws`에 `turtlebot` package 생성
4. `turtlebot` package 안의 `__init__.py`가 있는 폴더에 공유 파일 이동

현 작업 반영:

- 이 프로젝트에서는 `workspaces/지웅/turtlebot/ros2_ws/src/turtlebot`로 package를 생성했다.
- Notion의 `turtlebot_world.launch.py`는 실제 설치 패키지 기준으로 `turtlebot3_world.launch.py`를 사용한다.
- MM 공유 파일은 현재 이 작업공간에서 확인할 수 없어, 우선 프로젝트용 heartbeat/status smoke node를 `turtlebot`에 생성했다.
