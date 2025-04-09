from arm_model import ArmModel
import serial_communication as serial
import numpy as np
import config
from math import pi


def main():
    model = ArmModel(config.X_LIMIT, config.Y_LIMIT, config.Z_LIMIT)

    while True:
        x = 0
        y = 0
        z = 0 + config.Z_AXIS_TOLERANCE
        is_pickup = False
        try:
            x = float(input("Enter X: "))
            y = float(input("Enter y: "))
            z = float(input("Enter z: ")) + config.Z_AXIS_TOLERANCE
            is_pickup = bool(input("Is pickup? (t/or blank): "))
        except (TypeError, ValueError):
            print("Invalid input: Could not be parsed.")
            continue

        # Alter model's default position to the middle of targets quadrant 
        # to help reduce erroneous inverse solutions
        model.model.forward([determine_quadrant(x, y) * pi / 180, 0, 0])  
        print(model.model.axis_values)

        results = model.calc_joint_degrees(x, y, z)

        base_angle = round(results[1], config.DECIMAL_PLACES)
        shoulder_angle = round(results[2], config.DECIMAL_PLACES)
        elbow_angle = round(results[3], config.DECIMAL_PLACES)

        model.model.show(True, True)
        print(results)       
        print(f"{base_angle} {shoulder_angle} {elbow_angle} {is_pickup}")

        # If the position entered cannot be reached by the arm then continue
        if (results[0] == False):
            continue

        # Hold for user input
        input()
        
        serial.send_data(f"{base_angle} {shoulder_angle} {elbow_angle} {is_pickup}")


def determine_quadrant(x: float, y: float) -> float:
    """
    Calculates the angle of the base joint which would put the arm in the middle of the targets quadrant.
    Given the arms centre (the axis the base revolves around) is 0,0. The base's plane is split into the
    quadrants as if looking top-down onto this plane.
    
    Parameters
    ----------
    x: float
        The targets x coordinate.
    y: float
        The targets y coordinate.

    Returns
    -------
    angle: float
        The degrees of rotation on for the base joint.
    """
    if x >= 0 and y >= 0:
        return 45.0
    elif x >= 0 and y < 0:
        return -45.0
    elif x < 0 and y >= 0:
        return 135
    else:
        return -135


if __name__ == "__main__":
    main()
