import serial


def send_data(data):
    data += "\r\n"
    # COM4 for wireless connection with controller
    # COM6 for wired connection with VEX brain
    ser = serial.Serial('COM4', 115200)
    # Temp test data written
    ser.write(data.encode())
