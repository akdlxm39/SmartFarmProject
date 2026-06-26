# -*- coding: utf-8 -*-
import gpiod
import time
import numpy as np

# GPIO 핀 설정
DIR_PIN = 17
STEP_PIN = 27
ENABLE_PIN = 22

# GPIO 칩 및 라인 초기화
chip = gpiod.Chip("gpiochip0")
dir_line = chip.get_line(DIR_PIN)
step_line = chip.get_line(STEP_PIN)
enable_line = chip.get_line(ENABLE_PIN)

dir_line.request(consumer="dir", type=gpiod.LINE_REQ_DIR_OUT)
step_line.request(consumer="step", type=gpiod.LINE_REQ_DIR_OUT)
enable_line.request(consumer="enable", type=gpiod.LINE_REQ_DIR_OUT)


def generate_spline_trajectory(waypoints, time_points, dt):
    """
    numpy만 사용하여 Catmull-Rom 3차 스플라인 궤적을 생성하는 함수
    """
    # 곡선 계산을 위해 시작과 끝에 임의의 제어점 패딩(Padding) 추가
    p = np.array([waypoints[0]] + waypoints + [waypoints[-1]], dtype=float)
    t_points = np.array(time_points, dtype=float)

    t_fine = np.arange(t_points[0], t_points[-1] + dt, dt)
    target_positions = np.zeros_like(t_fine)

    for idx, current_t in enumerate(t_fine):
        # 마지막 시간 예외 처리
        if current_t >= t_points[-1]:
            target_positions[idx] = waypoints[-1]
            continue

        # 현재 시간(current_t)이 속한 구간 인덱스 탐색
        i = np.searchsorted(t_points, current_t, side="right") - 1
        if i < 0:
            i = 0

        # 해당 구간 내에서의 정규화된 진행도 (0.0 ~ 1.0)
        t_start = t_points[i]
        t_end = t_points[i + 1]
        local_t = (current_t - t_start) / (t_end - t_start)

        # 3차 다항식 계산을 위한 인접 4개 제어점 (p0, p1, p2, p3)
        p0, p1, p2, p3 = p[i], p[i + 1], p[i + 2], p[i + 3]

        # Catmull-Rom Spline 수식 적용
        t2 = local_t * local_t
        t3 = t2 * local_t

        pos = 0.5 * (
            (2 * p1)
            + (-p0 + p2) * local_t
            + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
            + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
        )
        target_positions[idx] = pos

    return t_fine, target_positions


# ==========================================
# 1. Waypoint 및 스플라인 곡선 프로파일 생성
# ==========================================
waypoints = [0, 1000, 6000, 3500, 0]
time_points = [0, 2, 4, 6, 8]
dt = 0.05  # 제어 주기 (50ms)

# scipy 대신 직접 구현한 함수로 궤적 생성
t_fine, target_positions = generate_spline_trajectory(waypoints, time_points, dt)

# ==========================================
# 2. 모터 위치 제어 및 실시간 추종 로직
# ==========================================
current_position = 0
pulse_delay = 0.0001

print("--- 컨베이어 벨트 Spline Curve 모션 시작 ---")
enable_line.set_value(0)

try:
    for i, current_time in enumerate(t_fine):
        target_pos = int(np.round(target_positions[i]))
        steps_to_move = target_pos - current_position

        # 1. 방향 설정
        if steps_to_move > 0:
            dir_line.set_value(0)  # CW
        elif steps_to_move < 0:
            dir_line.set_value(1)  # CCW

        # 2. 스텝 구동
        abs_steps = abs(steps_to_move)
        for _ in range(abs_steps):
            step_line.set_value(1)
            time.sleep(pulse_delay)
            step_line.set_value(0)
            time.sleep(pulse_delay)

        current_position = target_pos

        # 3. 실시간 위치 출력
        print(f"[Time: {current_time:.2f}s] Target Position: {target_pos}")

        # 4. 제어 주기 동기화
        step_execution_time = abs_steps * (pulse_delay * 2)
        sleep_time = dt - step_execution_time

        if sleep_time > 0:
            time.sleep(sleep_time)

    print("--- 모션 프로파일 종료 ---")

except KeyboardInterrupt:
    print("\n프로그램 종료")

finally:
    enable_line.set_value(1)
    dir_line.release()
    step_line.release()
    enable_line.release()
