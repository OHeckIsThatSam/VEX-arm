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

SHOULDER_GEAR_RATIO = 2.5
DEFAULT_VELOCITY = 5

brain = Brain()
base = Motor(Ports.PORT1, True)
shoulder = Motor(Ports.PORT2, True)
elbow = Motor(Ports.PORT3, False)
magnet = Electromagnet(Ports.PORT6)

arm = MotorGroup(base, shoulder, elbow)
arm.set_stopping(HOLD)
arm.set_velocity(DEFAULT_VELOCITY, PERCENT)


def handle_exception(ex):
    brain.screen.clear_screen()
    brain.screen.set_cursor(1,1)
    brain.screen.print(ex)
    print(ex)


def move(angles):
    # Move to neutral position
    shoulder.spin_to_position(90 * SHOULDER_GEAR_RATIO, DEGREES)
    elbow.spin_to_position(0, DEGREES)

    # Move to target position
    base.spin_to_position(angles[0], DEGREES)
    elbow.spin_to_position(angles[2], DEGREES)
    shoulder.spin_to_position(angles[1] * SHOULDER_GEAR_RATIO, DEGREES)


def pickup_move(angles):
    if magnet.installed():
        magnet.pickup()

    move(angles) 

   
def drop_move(angles):
    move(angles)

    if magnet.installed():
        magnet.drop(duration=250, units=MSEC, power=99)


def print_message_to_screen(message):
    brain.screen.clear_screen()

    for i in range(len(message)):
        # Screen's cursor is 1 based index
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
        
        data_array = data.split()

        joint_angles = []
        for angle in data_array[:3]:
            joint_angles.append(float(angle))
        
        is_pickup = data_array[3]
        
        brain.screen.clear_screen()
        brain.screen.set_cursor(1, 1)
        brain.screen.print(is_pickup)
        brain.screen.set_cursor(2,1)
        brain.screen.print(joint_angles)
        
        if is_pickup:
            pickup_move(joint_angles)
        else:
            drop_move(joint_angles)


try:
    t1=Thread(serial_monitor)
except Exception as ex:
    handle_exception(ex)
