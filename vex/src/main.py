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

# Initialise Constants
SHOULDER_GEAR_RATIO = 2.5
DEFAULT_VELOCITY = 5

SERIAL_PORT = "/dev/serial1"
# Mode is read and write in binary
SERIAL_MODE = "rwb"

# Initialise VEX Arm Components
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
    base.spin_to_position(angles[0], DEGREES, wait=True)
    elbow.spin_to_position(angles[2], DEGREES, wait=True)
    shoulder.spin_to_position(angles[1] * SHOULDER_GEAR_RATIO, DEGREES, wait=True)


def pickup_move(angles):
    magnet.set_power(100)
    magnet.pickup()

    move(angles) 

   
def drop_move(angles):
    move(angles)

    magnet.set_power(100)
    magnet.drop()


def print_message_to_screen(message):
    brain.screen.clear_screen()

    for i in range(len(message)):
        # Screen's cursor is 1 based index
        brain.screen.set_cursor(i + 1, 1)
        brain.screen.print(message[i])

def send_serial_message():
    pass

aThread = None
alarm_running = False
alarm_message = None

def alarm_monitor():
    global alarm_running, alarm_message
    while alarm_running:
        print_message_to_screen(alarm_message)
        brain.play_sound(SoundType.ALARM)
        wait(100, MSEC)

def serial_monitor():
    try:
      serial = open(SERIAL_PORT, SERIAL_MODE)
    except:
      raise Exception("Serial port not available")
  
    global alarm_running
    global alarm_message

    while True:
        data = serial.readline()
        
        if data == None:
            continue
        
        data_array = data.split()

        # Length 1 = Error message
        # Otherwise the message is normal
        if len(data_array) == 1:
            alarm_running = True
            alarm_message = data_array
        else:
            alarm_running = False
            alarm_message = None
            joint_angles = []
            for angle in data_array[:3]:
                joint_angles.append(float(angle))
            
            is_pickup = data_array[3]
            
            brain.screen.clear_screen()
            brain.screen.set_cursor(1, 1)
            brain.screen.print(is_pickup)
            brain.screen.set_cursor(2,1)
            brain.screen.print(joint_angles)
            
            if is_pickup == b'True':
                pickup_move(joint_angles)
            else:
                drop_move(joint_angles)

        serial.write("Done".encode())


try:
    alarm_thread=Thread(alarm_monitor)
    t1=Thread(serial_monitor)
except Exception as ex:
    handle_exception(ex)
