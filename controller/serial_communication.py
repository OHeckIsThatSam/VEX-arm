import serial, time, config


def send_data(data: str):
    data += "\r\n"

    ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUDRATE)
    
    if ser.is_open:
        ser.write(data.encode())
        ser.close()


def receive_data(timeout=20) -> str:
    ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUDRATE)
    
    if not ser.is_open:
        return ""
    
    for i in range(timeout):
        size = ser.inWaiting()
        if size != 0:
            data = ser.read(size)
            message = data.decode()
            print(f"[Serial Communication] Message received from VEX")
            print(f"[Serial Communication] Message: {message}")
            return message
        else:
            time.sleep(1)
    return ""
