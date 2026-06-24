import gpiod
import time

# GPIO pin numbers
btn1 = 23
btn2 = 24

# Open GPIO chip
chip = gpiod.Chip('gpiochip0')

# Get GPIO lines
button1_line = chip.get_line(btn1)
button2_line = chip.get_line(btn2)

# Setup GPIO lines for buttons
button1_line.request(consumer="button1", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)
button2_line.request(consumer="button2", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)

last_button1_state = 1
last_button2_state = 1

try:
    while True:
        button1_state = button1_line.get_value()
        button2_state = button2_line.get_value()

        if button1_state != last_button1_state:
            print(f"Button 1: {'pressed' if button1_state == 0 else 'Released'}")
        if button2_state != last_button2_state:
            print(f"Button 2: {'pressed' if button2_state == 0 else 'Released'}")
        
        if button1_state != last_button1_state and button2_state != last_button2_state:
            if button1_state == 0 and button2_state == 0:
                print("special message")

        
        last_button1_state = button1_state
        last_button2_state = button2_state

        

        time.sleep(0.2)

except KeyboardInterrupt:
    print("program terminated")

finally:
    button1_line.release()
    button2_line.release()