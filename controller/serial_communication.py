import serial
from time import sleep

# COM4 for wireless connection with controller
# COM6 for wired connection with VEX brain
ser = serial.Serial('COM4', 115200)
while True:
    # Temp test data written
    ser.write("d".encode())
    sleep(0.01)
