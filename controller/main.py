from arm_model import ArmModel
import serial_communication as serial
import numpy as np
import config


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

        results = model.calc_joint_degrees(x, y, z)

        base_angle = round(results[1], config.DECIMAL_PLACES)
        shoulder_angle = round(results[2], config.DECIMAL_PLACES)
        elbow_angle = round(results[3], config.DECIMAL_PLACES)

        # If the position entered cannot be reached by the arm then continue
        if (results[0] == False):
            continue

        print(np.array2string(results))
        model.show()

        print(f"{base_angle} {shoulder_angle} {elbow_angle} {is_pickup}")

        # Hold for user input
        input()

        serial.send_data(f"{base_angle} {shoulder_angle} {elbow_angle} {is_pickup}")


if __name__ == "__main__":
    main()
