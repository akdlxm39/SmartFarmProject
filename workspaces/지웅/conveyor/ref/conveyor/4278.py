# -*- coding: utf-8 -*-
import gpiod
import time
import threading

# GPIO pin numbers
SERVO_PIN = 18
DIR_PIN = 17
STEP_PIN = 27
ENABLE_PIN = 22
btn1 = 23
btn2 = 24

# Servo angle constants
CENTER_ANGLE = 135
RIGHT_ANGLE = 175
LEFT_ANGLE = 95

# Open GPIO chip
chip = gpiod.Chip("gpiochip0")

# Get GPIO lines and set up
servo_line = chip.get_line(SERVO_PIN)
dir_line = chip.get_line(DIR_PIN)
step_line = chip.get_line(STEP_PIN)
enable_line = chip.get_line(ENABLE_PIN)
button1_line = chip.get_line(btn1)
button2_line = chip.get_line(btn2)

# Setup GPIO lines for buttons
servo_line.request(consumer="servo", type=gpiod.LINE_REQ_DIR_OUT)
dir_line.request(consumer="dir", type=gpiod.LINE_REQ_DIR_OUT)
step_line.request(consumer="step", type=gpiod.LINE_REQ_DIR_OUT)
enable_line.request(consumer="enable", type=gpiod.LINE_REQ_DIR_OUT)
button1_line.request(
    consumer="button1",
    type=gpiod.LINE_REQ_DIR_IN,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP,
)
button2_line.request(
    consumer="button2",
    type=gpiod.LINE_REQ_DIR_IN,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP,
)

# Motor control variables
motor_running = False
motor_direction = 0
target_direction = 0
TargetSpeed = 0.0001
InitialSpeed = 0.0005
Speed = InitialSpeed
RATIO = 0.0000005
isAccelerating = False
current_button = None

last_button1_state = 1
last_button2_state = 1


def set_servo(angle):
    pulse_width = (angle / 270) * (0.0025 - 0.0005) + 0.0005
    for _ in range(10):
        servo_line.set_value(1)  # 서보를 움직이겠다
        time.sleep(pulse_width)  # pulse_width 만큼 움직이겠다
        servo_line.set_value(0)
        time.sleep(0.02 - pulse_width)  # 서보모터의 총 주기


def end_2sec():
    global current_button
    time.sleep(2)
    print(f"Moving servo to {CENTER_ANGLE} degrees")
    set_servo(CENTER_ANGLE)
    current_button = None


def step_motor():
    global motor_running, Speed, isAccelerating, target_direction
    while motor_running:
        if motor_direction != target_direction:
            if target_direction == 0:
                Speed += RATIO
                if Speed >= InitialSpeed:
                    motor_running = False
                    enable_line.set_value(1)
            else:
                isAccelerating = True
                Speed = InitialSpeed
        elif motor_direction == 0:
            Speed += RATIO
            if Speed >= InitialSpeed:
                motor_running = False
                enable_line.set_value(1)
        else:
            if isAccelerating:
                if Speed > TargetSpeed:
                    Speed -= RATIO
                else:
                    Speed = TargetSpeed
                    isAccelerating = False

        step_line.set_value(1)
        time.sleep(Speed)
        step_line.set_value(0)
        time.sleep(Speed)


def print_motor_status():
    print(
        f"Motor Running: {motor_running}, Direction: {'CW' if motor_direction == 1 else 'CCW' if motor_direction == -1 else 'Stop'}, Speed: {Speed:.6f}"
    )


try:
    while True:
        button1_state = button1_line.get_value()
        button2_state = button2_line.get_value()

        if button1_state != last_button1_state and button2_state != last_button2_state:
            if button1_state == 0 and button2_state == 0:
                print("special message")
                if motor_running:
                    print("Stopping motor")
                    target_direction = 0
                    motor_direction = 0
                else:
                    print("Starting motor CW")
                    target_direction = 1
                    motor_direction = 1
                    dir_line.set_value(0)
                    isAccelerating = True
                    Speed = InitialSpeed
                    enable_line.set_value(0)  # Enable motor
                    current_button = 1
                    if not motor_running:
                        motor_running = True
                        threading.Thread(target=step_motor).start()
                print_motor_status()
        else:
            if button1_state != last_button1_state:
                print(f"Button 1: {'pressed' if button1_state == 0 else 'Released'}")
                if button1_state == 0 and current_button != 1:
                    print(f"Moving servo to {LEFT_ANGLE} degrees")
                    set_servo(LEFT_ANGLE)
                    current_button = 1
                    threading.Thread(target=end_2sec).start()
                elif button1_state == 1 and current_button == 1:
                    print(f"Moving servo to {CENTER_ANGLE} degrees")
                    set_servo(CENTER_ANGLE)
                    current_button = None

            if button2_state != last_button2_state:
                print(f"Button 2: {'pressed' if button2_state == 0 else 'Released'}")
                if button2_state == 0 and current_button != 2:
                    print(f"Moving servo to {RIGHT_ANGLE} degrees")
                    set_servo(RIGHT_ANGLE)
                    current_button = 2
                    threading.Thread(target=end_2sec).start()
                elif button2_state == 1 and current_button == 2:
                    print(f"Moving servo to {CENTER_ANGLE} degrees")
                    set_servo(CENTER_ANGLE)
                    current_button = None

        last_button1_state = button1_state
        last_button2_state = button2_state

        time.sleep(0.2)

except KeyboardInterrupt:
    print("Program terminated")

finally:
    motor_running = False
    time.sleep(0.1)
    enable_line.set_value(1)
    dir_line.release()
    step_line.release()
    enable_line.release()
    button1_line.release()
    button2_line.release()
