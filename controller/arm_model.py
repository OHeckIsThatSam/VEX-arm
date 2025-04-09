import numpy as np
from visual_kinematics.RobotSerial import *

class ArmModel():
    def __init__(self, x_limit, y_limit, z_limit):
        # Using Denavit-Hartenberg (DH) notation for representation of arm's construction
        # DH modelling file found in /DH/ArmDH.kinbin, used by "Robotic Arm Kinematic GUI - Part of MRPT"
        #                      [d, a, alpha, theta]
        dh_params = np.array([[17.0, 0., 90.0 * pi / 180, 0.],
                          [0., 11.5, 0., 3 * pi / 180],
                          [0., 11.0, 0., -90.0 * pi / 180]])

        # Electro magnet tool DH is unused by the model as the joint self orientates down.
        # It's height is factored into the target coordinates resulting in the target being reached
        # with the tool directly above regardless of the orientation of the end frame.
        # [0., 7.6, 0., 37 * pi / 180]

        self.model = RobotSerial(
            dh_params=dh_params,
            plot_xlim=x_limit,
            plot_ylim=y_limit,
            plot_zlim=z_limit,
            max_iter=1000)


    def calc_joint_degrees(self, x, y, z, dec_places=1) -> list:
        """
            Uses inverse kinematics to calculate the angles at each joint for the manipulators
            end frame to reach the supplied coordinates. Returns best attempt if coordinates
            are unreachable.

            Parameters
            ----------
            x: float
                Target x coordinate.
            y: float
                Target y coordinate.
            z: float
                Target z coordinate.
            
            Returns
            -------
            angles: list 
                List containing joint angels and if position reachable [bool, float, float, float]
        """
        self.model.forward([self.determine_quadrant_angle(x,y), 0, 0])

        target_position = np.array([[x], [y], [z]])
        # a, b, c - degrees of rotation of the z, y, x axes from the base axes
        # default to 0 i.e tool always faces same as x in default position 
        target_tool_rotation = np.array([0., 0., 0.])

        end = Frame.from_euler_3(target_tool_rotation, target_position)
        self.model.inverse(end)

        axis_values = self.model.axis_values
        base_rotation = rad_to_deg(axis_values[0])
        elbow_rotation = rad_to_deg(axis_values[1])
        wrist_rotation = rad_to_deg(axis_values[2])
        return [
            self.model.is_reachable_inverse, 
            round(base_rotation, dec_places), 
            round(elbow_rotation, dec_places), 
            round(wrist_rotation, dec_places)
        ]

    
    def determine_quadrant_angle(_self, x: float, y: float) -> float:
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


def rad_to_deg(rad):
    return (rad * 180) / pi
