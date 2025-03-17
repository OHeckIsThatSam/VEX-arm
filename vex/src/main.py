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
motor1 = Motor(Ports.PORT1, False)
motor2 = Motor(Ports.PORT2, False)
motor3 = Motor(Ports.PORT3, False)

motors = [motor1, motor2, motor3]

def validate():
    pass

def parse_serial_message():
    pass

def handle_exception(ex):
    brain.screen.clear_screen()
    brain.screen.set_cursor(1,1)
    brain.screen.print(ex)
    print(ex)

def move(data):
    motor1.spin_to_position(int(data[0]), DEGREES)
    motor2.spin_to_position(data[1], DEGREES)
    motor3.spin_to_position(data[2], DEGREES)

def print_message_to_screen(message):
    brain.screen.clear_screen()
    i = 1
    for value in message:
        brain.screen.set_cursor(i, 1)
        brain.screen.print(value)
        i = i + 1

def serial_monitor():
    try:
      s = open('/dev/serial1','rb')
    except:
      raise Exception('serial port not available')
  
    while True:
        data=s.readline()
        if data == None:
            continue

        message = data.split()
        messageints = []

        for m in message:
            messageints.append(float(m))
        brain.screen.set_cursor(1, 1)
        brain.screen.print(messageints)
        move(messageints)

try:
    for motor in motors:
        motor.set_stopping(HOLD)
        motor.set_velocity(10, PERCENT)
    t1=Thread(serial_monitor)
except Exception as ex:
    handle_exception(ex)
