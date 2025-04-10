# Set distances defined by camera config
X_LIMIT = [-47, 47] # 51cm max
Y_LIMIT = [-27, 27] # 26cm max
Z_LIMIT = [0, 69]

# Set calculations config
DECIMAL_PLACES = 1
# Positive tolerance to increase coords by due to flex, tool configuration and target item height
Z_AXIS_TOLERANCE = 8

# Serial Port config
# Usually COM4 for wireless connection with controller and
# COM6 for wired connection with VEX brain but check before running app
SERIAL_PORT = "COM4"
SERIAL_BAUDRATE = 115200
