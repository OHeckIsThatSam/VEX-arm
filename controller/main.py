from arm_model import ArmModel
import numpy as np

def main():
    model = ArmModel()

    x = 0.2
    y = 0.2
    z = 0.3
    
    results = model.calc_joint_degrees(x, y, z)

    print(np.array2string(results))
    model.show()


if __name__ == "__main__":
    main()
