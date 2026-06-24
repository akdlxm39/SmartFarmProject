# 지웅 / Conveyor 작업환경

이 폴더는 SmartFarmProject 컨베이어 파트 작업공간이다.

현재 구현된 도구:

- `scripts/select_conveyor_roi.py`
  - **B안 기준: 실제 ROS `sensor_msgs/Image` topic에서 들어온 프레임을 직접 받음**
  - ROS preview 창에서 `SPACE`를 눌러 현재 프레임을 고정
  - `마우스이벤트1` / `mouse_event_1_topview_quad`로 상단뷰 변환용 4점을 클릭
  - perspective transform으로 top-view 프레임 생성
  - `마우스이벤트2` / `mouse_event_2_conveyor_roi`로 top-view 위 컨베이어 ROI 4점을 클릭
  - 좌표와 preview 이미지를 저장

## 최초 환경 준비

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor
uv venv .venv --python 3.10
source .venv/bin/activate
uv pip install -r requirements.txt
python --version  # Python 3.10.12 권장/확인
```

## ROS 프레임으로 좌표 지정 B안 / 권장

실제 detector도 ROS topic에서 frame을 받을 예정이므로, 좌표 세팅도 같은 ROS topic에서 직접 받은 프레임으로 한다.

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor
source /opt/ros/humble/setup.bash
source .venv/bin/activate
python scripts/select_conveyor_roi.py \
  --ros-topic /camera/camera/color/image_raw \
  --output config/conveyor_roi_topview.json \
  --point-order click
```

만약 top-view 결과가 클릭한 4점보다 안쪽으로 작게 잡히는 느낌이면 아래처럼 2~3% 패딩을 준다.

```bash
python scripts/select_conveyor_roi.py \
  --ros-topic /camera/camera/color/image_raw \
  --output config/conveyor_roi_topview.json \
  --point-order click \
  --source-padding-ratio 0.03
```

만약 `rclpy` import 오류가 나면 ROS Python 버전과 `.venv` Python 버전이 다른 경우일 수 있다. 그때는 ROS 환경을 먼저 확인한다.

```bash
source /opt/ros/humble/setup.bash
python3 -c "import rclpy, sensor_msgs; print('ros python ok')"
```

이 확인이 되는데 `.venv`에서만 실패하면, ROS와 같은 Python 버전으로 venv를 다시 만들거나 ROS 패키지 형태로 옮겨 실행한다.

ROS preview 창에서 `SPACE`를 누르면 현재 ROS frame을 고정한 뒤 좌표 지정 단계로 넘어간다.

이 방식으로 저장된 JSON은 실제 ROS topic frame의 `width`, `height`, `encoding`, `frame_id`, `stamp`를 함께 기록한다. 이후 detector 노드는 JSON의 `raw_frame.width/height`와 실시간 ROS frame 해상도를 비교해서 다르면 좌표 재설정을 요구하면 된다.

top-view 결과 프레임은 기본값으로 원본 ROS 프레임과 같은 크기(`--topview-size-mode raw`)로 생성된다. 그래서 상단뷰 좌표를 좁게 찍어도 다음 ROI 선택 창이 작은 프레임으로 뜨지 않는다. 예전처럼 클릭한 quad 크기만큼만 작게 만들고 싶으면 `--topview-size-mode quad`를 명시한다.

스크린샷 기준으로 확인한 추가 문제는 “창 크기”가 아니라 **지정한 4점보다 안쪽 영역이 top-view로 잡히는 것처럼 보이는 현상**이다. 이를 줄이기 위해 다음을 적용했다.

- 4점 순서는 자동 정렬 대신 기본적으로 사용자가 클릭한 순서(`--point-order click`)를 그대로 신뢰한다.
- 좌표 창은 OpenCV가 임의로 리사이즈하지 않도록 `WINDOW_AUTOSIZE`로 띄운다.
- 화면에 너무 크면 창을 드래그로 줄이지 말고 `--display-scale 0.7`처럼 명시적으로 줄인다.
- 그래도 경계가 조금 잘려 보이면 `--source-padding-ratio 0.02` 또는 `0.03`으로 source quad를 중심 기준으로 살짝 확장한다.

## 샘플 이미지로 좌표 지정 / 보조용

```bash
cd /home/ssafy/work/SmartFarmProject/workspaces/지웅/conveyor
source .venv/bin/activate
python scripts/select_conveyor_roi.py
```

기본 입력 이미지는 프로젝트 샘플 이미지다.

```text
/home/ssafy/work/SmartFarmProject/references/realsense-test-image.png
```

## 실제 카메라로 좌표 지정

```bash
python scripts/select_conveyor_roi.py --camera 0 --output config/conveyor_roi_topview.json
```

카메라 preview 창에서 `SPACE`를 누르면 현재 프레임을 고정한 뒤 좌표 지정 단계로 넘어간다.

## 클릭 순서

각 단계 모두 권장 클릭 순서는 다음과 같다.

```text
좌상단 -> 우상단 -> 우하단 -> 좌하단
```

- 왼쪽 클릭: 점 추가
- 오른쪽 클릭 또는 `u`: 마지막 점 취소
- `r`: 현재 단계 좌표 초기화
- `q` 또는 `ESC`: 종료

## 결과 파일

기본 JSON:

```text
config/conveyor_roi_topview.json
```

preview 이미지:

```text
config/previews/conveyor_roi_topview_raw_topview_quad.png
config/previews/conveyor_roi_topview_topview.png
config/previews/conveyor_roi_topview_topview_roi.png
```

JSON에는 아래 값이 들어간다.

- `topview.source_quad_raw_xy_tl_tr_br_bl`: 원본 프레임 기준 상단뷰 변환 4점
- `topview.size_wh`: 변환된 top-view 크기
- `topview.perspective_matrix_raw_to_topview`: perspective transform matrix
- `conveyor_roi.quad_xy_tl_tr_br_bl`: top-view 기준 컨베이어 ROI 4점
- `conveyor_roi.xyxy`: top-view 기준 ROI bounding box
- `runtime_defaults`: 빨강/초록 큐브 동일 처리, 10프레임 미검출 정지, 시계방향 구동, Modbus TCP + `pymodbus==3.13.1`

## 비대화형 검증

GUI 없이 스크립트 저장/변환 경로만 확인하려면:

```bash
python scripts/select_conveyor_roi.py --self-test --output config/self_test_conveyor_roi_topview.json
```
