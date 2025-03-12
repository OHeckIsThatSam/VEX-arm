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

def serial_monitor():
    try:
      s = open('/dev/serial1','rb')
    except:
      raise Exception('serial port not available')
  
    while True:
        data=s.read(1)
        #print(data)
        if data == b'a' or data == b'A':
            brain.screen.print_at("forward", x=5, y=20)
        if data == b'p' or data == b'P':
            brain.screen.print_at("stop   ", x=5, y=20)
        if data == b'd' or data == b'D':
            brain.screen.print_at("right  ", x=5, y=20)
        if data == b'l' or data == b'L':
            brain.screen.print_at("left   a", x=5, y=20)

t1=Thread(serial_monitor)
