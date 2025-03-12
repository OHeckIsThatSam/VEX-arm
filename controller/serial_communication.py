import serial
from time import sleep
ser = serial.Serial('COM4', 115200)
while True:
    ser.write("d".encode())
    sleep(0.01)