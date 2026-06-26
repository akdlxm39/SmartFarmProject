import gpiod
import time

# GPIO pin numbers
SERVO_PIN = 18

# Servo angle constants
MIN_ANGLE = 95
MAX_ANGLE = 175

# Open GPIO chip
chip = gpiod.Chip('gpiochip0')

# Get GPIO lines
servo_line = chip.get_line(SERVO_PIN)

# Setup GPIO lines for buttons
servo_line.request(consumer="servo", type=gpiod.LINE_REQ_DIR_OUT)

# angle = 0 -> pulse_width = 0.0005
# angle = 270 -> pulse_width = 0.0025

def set_servo(angle):
    pulse_width = (angle/270) * (0.0025 - 0.0005) + 0.0005

    for _ in range(10):
        servo_line.set_value(1) # 서보를 움직이겠다
        time.sleep(pulse_width) # pulse_width 만큼 움직이겠다
        servo_line.set_value(0)
        time.sleep(0.02 - pulse_width) # 서보모터의 총 주기

try:
    while True:
        user_input = input("Enter value(95~175): ")
        if not user_input.isdigit() or not (MIN_ANGLE <= int(user_input) <= MAX_ANGLE) :
            print("Wrong input. Please ", end="")
            continue
        angle = int(user_input)
        print(f"Moving servo to {angle} degrees")
        set_servo(angle)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("program terminated")

finally:
    servo_line.release()
