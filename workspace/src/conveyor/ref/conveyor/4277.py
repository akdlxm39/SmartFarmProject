import gpiod
import time
import threading

# GPIO pin numbers
DIR_PIN = 17
STEP_PIN = 27
ENABLE_PIN = 22

# Open GPIO chip
chip = gpiod.Chip('gpiochip0')

# Get GPIO lines
dir_line = chip.get_line(DIR_PIN)
step_line = chip.get_line(STEP_PIN)
enable_line = chip.get_line(ENABLE_PIN)

# Setup GPIO lines for buttons
dir_line.request(consumer="dir", type=gpiod.LINE_REQ_DIR_OUT)
step_line.request(consumer="step", type=gpiod.LINE_REQ_DIR_OUT)
enable_line.request(consumer="enable", type=gpiod.LINE_REQ_DIR_OUT)

# Move control variables
motor_running = False
motor_direction = 1

def step_motor():
    global motor_running
    while motor_running:
        step_line.set_value(1)
        time.sleep(0.0001)
        step_line.set_value(0)
        time.sleep(0.0001)

try:
    while True:
        user_input = input("Enter value('cw'/'ccw' 1~30 eg. cw 5): ").split()
        if len(user_input) != 2:
            print("잘못된 입력입니다.")
            continue
        dir, dur = user_input
        dir = dir.lower()
        if dir not in ("cw", "ccw") or not dur.isdigit():
            print("잘못된 입력입니다.")
            continue
        dur = float(dur)
        if not (1.0 <= dur <= 30.0):
            print("잘못된 입력입니다.")
            continue
        # start
        print(f"Start motor {dir.upper()}")
        motor_direction = 0 if dir=="cw" else 1
        dir_line.set_value(motor_direction)
        enable_line.set_value(0)
        motor_running = True
        threading.Thread(target=step_motor).start()
        # run
        time.sleep(dur)
        # stop
        print("Stopping motor")
        motor_running = False
        enable_line.set_value(1)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nprogram terminated")

finally:
    motor_running = False
    time.sleep(0.1)
    enable_line.set_value(1)

    dir_line.release()
    step_line.release()
    enable_line.release()