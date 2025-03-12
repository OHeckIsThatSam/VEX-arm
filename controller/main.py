from arm_model import ArmModel
import serial_communication as ser
import numpy as np


DECIMAL_PLACES = 1

def main():
    model = ArmModel()

    x = 0.24
    y = 0.35
    z = 0.18
    
    results = model.calc_joint_degrees(x, y, z)

    base_angle = round(results[1], DECIMAL_PLACES)
    # Construction of the arm means the elbow motor turns anti clockwise compared to the model
    elbow_angle = -round(results[2], DECIMAL_PLACES)
    wrist_angle = round(results[3], DECIMAL_PLACES)
    
    print(np.array2string(results))
    model.show()

    # Hold for user input
    input()

    ser.send_data(f"{base_angle} {elbow_angle} {wrist_angle}")
    

if __name__ == "__main__":
    main()
