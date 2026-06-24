import gpiod
import time
import threading

# GPIO pin numbers
DIR_PIN = 17
STEP_PIN = 27
ENABLE_PIN = 22
BUTTON1_PIN = 23
BUTTON2_PIN = 24

# Open GPIO chip
chip = gpiod.Chip('gpiochip0')

# Get GPIO lines
dir_line = chip.get_line(DIR_PIN)
step_line = chip.get_line(STEP_PIN)
enable_line = chip.get_line(ENABLE_PIN)
button1_line = chip.get_line(BUTTON1_PIN)
button2_line = chip.get_line(BUTTON2_PIN)

# Setup GPIO lines for buttons
dir_line.request(consumer="dir", type=gpiod.LINE_REQ_DIR_OUT)
step_line.request(consumer="step", type=gpiod.LINE_REQ_DIR_OUT)
enable_line.request(consumer="enable", type=gpiod.LINE_REQ_DIR_OUT)
button1_line.request(consumer="button1", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)
button2_line.request(consumer="button2", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)

# Move control variables
motor_running = False
motor_direction = 1
current_button = None

def step_motor():
    global motor_running
    while motor_running:
        step_line.set_value(1)
        time.sleep(0.0001)
        step_line.set_value(0)
        time.sleep(0.0001)

last_button1_state = 1
last_button2_state = 1

def print_motor_status():
    print(f"Motor Running: {motor_running}, Direction: {'CW' if motor_direction == 0 else 'CCW'}")

try:
    while True:
        button1_state = button1_line.get_value()
        button2_state = button2_line.get_value()

        if button1_state != last_button1_state:
            print(f"Button 1: {'pressed' if button1_state == 0 else 'Released'}")
            if button1_state == 0: # pressed
                if current_button == 1:
                    print("Stopping motor")
                    motor_running = False
                    enable_line.set_value(1)
                    current_button = None
                else: # First pressed - CW
                    print("Starting motor CW")
                    motor_direction = 0
                    dir_line.set_value(motor_direction)
                    enable_line.set_value(0) # Enable motor
                    motor_running = True
                    current_button = 1
                    threading.Thread(target=step_motor).start()
                print_motor_status()

        if button2_state != last_button2_state:
            print(f"Button 2: {'pressed' if button2_state == 0 else 'Released'}")
            if button2_state == 0: # pressed
                if current_button == 2:
                    print("Stopping motor")
                    motor_running = False
                    enable_line.set_value(1)
                    current_button = None
                else: # First pressed - CCW
                    print("Starting motor CCW")
                    motor_direction = 1
                    dir_line.set_value(motor_direction)
                    enable_line.set_value(0) # Enable motor
                    motor_running = True
                    current_button = 2
                    threading.Thread(target=step_motor).start()
                print_motor_status()

        last_button1_state = button1_state
        last_button2_state = button2_state

        time.sleep(0.1)

except KeyboardInterrupt:
    print("program terminated")

finally:
    motor_running = False
    time.sleep(0.1)
    enable_line.set_value(1)

    dir_line.release()
    step_line.release()
    enable_line.release()
    button1_line.release()
    button2_line.release()
