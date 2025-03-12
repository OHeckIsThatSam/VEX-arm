from arm_model import ArmModel
import serial_communication
import numpy as np


def main():
    model = ArmModel()

    x = 0.2
    y = 0.2
    z = 0.3
    
    results = model.calc_joint_degrees(x, y, z)
    
    data = f"{round(results[1], 1)} {round(results[2], 1)} {round(results[3],1)}"

    serial_communication.send_data(data)
    
    print(np.array2string(results))
    model.show()


if __name__ == "__main__":
    main()
