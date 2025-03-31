import numpy as np
from visual_kinematics.RobotSerial import *

class ArmModel():
    def __init__(self, x_limit, y_limit, z_limit):
        # Using Denavit-Hartenberg (DH) notation for representation of arm properties
        # DH modelling file found in /DH/ArmDH.kinbin, used by "Robotic Arm Kinematic GUI - Part of MRPT"
        #                      [d, a, alpha, theta]
        dh_params = np.array([[17.5, 0., 90.0 * pi / 180, 0.],
                          [0., 15, 0., 3 * pi / 180],
                          [0., 11.2, 0., -90.0 * pi / 180]])

        # Electro magnet tool DH
        # [0., 7.3, 0., 0.]

        self.model = RobotSerial(
            dh_params=dh_params,
            plot_xlim=x_limit,
            plot_ylim=y_limit,
            plot_zlim=z_limit,
            max_iter=1000)


    def calc_joint_degrees(self, x, y, z):
        """
            Uses inverse kinematics to calculate the angles at each joint for the manipulators
            end frame to reach the supplied coordinates. Returns best attempt if coordinates
            are unreachable.
            Returns: array [bool for if reachable, joint 1 angle, joint 2 angle 2, joint 3 angle ]  
        """
        target_position = np.array([[x], [y], [z]])
        # a, b, c - degrees of rotation of the z, y, x axes from the base axes
        # default to 0 i.e tool always faces same as x in default position 
        target_tool_rotation = np.array([0., 0., 0.])

        end = Frame.from_euler_3(target_tool_rotation, target_position)
        self.model.inverse(end)

        axis_values = self.model.axis_values
        base_rotation = self.rad_to_deg(axis_values[0])
        elbow_rotation = self.rad_to_deg(axis_values[1])
        wrist_rotation = self.rad_to_deg(axis_values[2])
        return np.array(
            [
                self.model.is_reachable_inverse, 
                base_rotation, 
                elbow_rotation, 
                wrist_rotation
            ])


    def rad_to_deg(_self, rad):
        return (rad * 180) / pi
    
    
    # Visual representation temporary for debug
    def show(self):
        self.model.show()
