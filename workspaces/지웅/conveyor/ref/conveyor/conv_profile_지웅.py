# -*- coding: utf-8 -*-
import gpiod
import time
import threading

# GPIO pin numbers
DIR_PIN = 17
STEP_PIN = 27
ENABLE_PIN = 22 
btn1 = 23
btn2 = 24

# Open GPIO chip
chip = gpiod.Chip('gpiochip0')

# Get GPIO lines and set up
dir_line = chip.get_line(DIR_PIN)
step_line = chip.get_line(STEP_PIN)
enable_line = chip.get_line(ENABLE_PIN)
button1_line = chip.get_line(btn1)
button2_line = chip.get_line(btn2)

dir_line.request(consumer="dir", type=gpiod.LINE_REQ_DIR_OUT)
step_line.request(consumer="step", type=gpiod.LINE_REQ_DIR_OUT)
enable_line.request(consumer="enable", type=gpiod.LINE_REQ_DIR_OUT)
button1_line.request(consumer="button1", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)
button2_line.request(consumer="button2", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)

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

lastButton1State = 1
lastButton2State = 1

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
   print(f"Motor Running: {motor_running}, Direction: {'CW' if motor_direction == 1 else 'CCW' if motor_direction == -1 else 'Stop'}, Speed: {Speed:.6f}")

try:
   while True:
       button1_state = button1_line.get_value()
       button2_state = button2_line.get_value()
       
       # Button 1 (CW)
       if button1_state != lastButton1State:
           print(f"Button 1: {'Pressed' if button1_state == 0 else 'Released'}")
           if button1_state == 0:  # Pressed
               if current_button == 1:  # Same button pressed again - stop
                   print("Stopping motor")
                   target_direction = 0
                   motor_direction = 0
                   current_button = None
               else:  # Start CW
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
       
       # Button 2 (CCW)
       if button2_state != lastButton2State:
           print(f"Button 2: {'Pressed' if button2_state == 0 else 'Released'}")
           if button2_state == 0:  # Pressed
               if current_button == 2:  # Same button pressed again - stop
                   print("Stopping motor")
                   target_direction = 0
                   motor_direction = 0
                   current_button = None
               else:  # Start CCW
                   print("Starting motor CCW")
                   target_direction = -1
                   motor_direction = -1
                   dir_line.set_value(1)
                   isAccelerating = True
                   Speed = InitialSpeed
                   enable_line.set_value(0)  # Enable motor
                   current_button = 2
                   if not motor_running:
                       motor_running = True
                       threading.Thread(target=step_motor).start()
               print_motor_status()
       
       lastButton1State = button1_state
       lastButton2State = button2_state
       
       time.sleep(0.1)

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
