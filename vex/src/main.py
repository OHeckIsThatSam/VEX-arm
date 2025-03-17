# ---------------------------------------------------------------------------- #
#                                                                              #
# 	Module:       main.py                                                      #
# 	Author:       sam                                                          #
# 	Created:      3/3/2025, 5:32:05 PM                                         #
# 	Description:  EXP project                                                  #
#                                                                              #
# ---------------------------------------------------------------------------- #
#vex:disable=repl

# Library imports
from vex import *

brain = Brain()
base = Motor(Ports.PORT1, False)
elbow = Motor(Ports.PORT2, False)
wrist = Motor(Ports.PORT3, False)

arm = MotorGroup(base, elbow, wrist)
arm.set_stopping(HOLD)
arm.set_velocity(10, PERCENT)

def handle_exception(ex):
    brain.screen.clear_screen()
    brain.screen.set_cursor(1,1)
    brain.screen.print(ex)
    print(ex)

def move(data):
    elbow.spin_to_position(data[1], DEGREES, wait=True)
    wrist.spin_to_position(data[2], DEGREES, wait=True)
    base.spin_to_position(data[0], DEGREES, wait=True)

def print_message_to_screen(message):
    brain.screen.clear_screen()

    for i in range(len(message)):
        # Screen's cursor has 1 based index
        brain.screen.set_cursor(i + 1, 1)
        brain.screen.print(message[i])

def serial_monitor():
    try:
      serial = open('/dev/serial1','rb')
    except:
      raise Exception('serial port not available')
  
    while True:
        data = serial.readline()
        
        if data == None:
            continue

        joint_angles = []
        for angle in data.split():
            joint_angles.append(float(angle))
            
        brain.screen.set_cursor(1, 1)
        brain.screen.print(joint_angles)
        move(joint_angles)

try:
    t1=Thread(serial_monitor)
except Exception as ex:
    handle_exception(ex)
