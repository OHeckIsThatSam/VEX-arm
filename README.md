# VEX-arm

## Introduction

This codebase contains the code to control a 3 axis robotic arm. The arm is a custom design constructed from [VEX EXP](https://www.vexrobotics.com/exp) parts. The arm and vision system is capable of picking up metal objects with an electro magnet tool in a 20x20cm workspace. Due to the motors and axles within the kit each joint has roughly 15 degrees of free play making precision movements and cm accuracy unachievable. Accounting for this in the controller logic and adding a retry mechanism, if a pickup is sensed as a failure, gives a near 100% accuracy when moving jam jar lids.

This codebases structure is as follows:

- controller - Overall logic controller, parses objects identified by the vision module and computes poses to pickup and drop off the objects.
- vex/src - A VEX project running on the embedded "VEX Brain" awaiting Bluetooth communication from the controller and moving the joints' motor angles.
- vision - Identified objects within a camera feed, and using pixel locations, their coordinates. Results are written to a object_log.csv.

## Setup

Install a local copy of this repository on a **Windows 11** machine.

### Vision Configuration

Either connect a webcam or set up an app like DroidCam with an android phone. Position the camera 70cm directly above the centre of the arm's workspace. Follow the configuration steps bellow to account for object detection with different lenses and backgrounds. **Please Note** you may need to update the camera_id located within the vision/camruler.py file (line 30). By default integrated webcams have an id of 0... if you do not have an integrated webcam or more than one this number will differ.

Run the vision/camruler.py file to start the vision module, this may take some time.

Once the window containing the video feed appears press c to enter config mode. Take a ruler or tape measure and align it along the longest diagonal red line.

Click on the window at every 5cm interval indicated along the tape measure or ruler.

Once the indicated intervals have stopped proceed to the next step. If the edge of the camera feed is reached before then press c again to exit config mode.

Press a to start recognising objects. If a large amount of blue label noise is seen press t and, with the mouse within the window, move it around until object have clear precise red indicators. Once this occurs click the mouse to exit threshold adjustment.  

### VEX Brain

The VEX project can be pushed to the vex brain using the [vex-vs-extension](https://github.com/VEX-Robotics/vex-vsc-extension) for Visual Studio Code.

Turn on and pair the VEX's controller to the brain, more info [here](https://kb.vex.com/hc/en-us/articles/4414780904468-Wirelessly-Pairing-an-EXP-Controller-to-an-EXP-Brain).

Connect the controller to the main PC using the USB. Make note of the COM port it's connected on. If it is not COM4 then update the controller/config.py (line 14).

Now **disable** and restart the vex vs extension otherwise it will lock the com port and not allow the master control application to connect to the controller.

On the VEX Brain run the loaded program.

### Master Controller

Run the controller/master.py file to start picking up and dropping off objects.

## Demonstration Video

A video demonstrating the capabilities of the system, covering the constraints of the design and the subsequent error cases and recovery.

[Video](https://youtu.be/OErSkC1RVZI)

## Future Work

The hardware of the arm was a heavy limitation in the accuracy of the robot. Within the given use case this was acceptable however improving the motors, axles and bearings would drastically make the arm more versatile.
The "Vex Brian" has little to no support for large external packages and strict resource limitations so most heavy processing must be done on a separate device. An embedded device with more resources would allow the consolidation of modules into a single device heavily reducing the complexity of setup and operation.

## Resources

### Kinematics

[Visual Kinematics package](https://github.com/dbddqy/visual_kinematics/tree/master)

Other investigated kinematic package options:

- [Robotics Toolbox for Python](https://petercorke.github.io/robotics-toolbox-python/index.html)
- [dkt](https://github.com/jhavl/dkt)
- [pybotics](https://github.com/engnadeau/pybotics)
- [pykin](https://github.com/jdj2261/pykin/tree/main)

[DH parameters](https://forum.robotsinarchitecture.org/index.php?topic=292.0)

Kinematics (background reading):

- [foundations](https://rpal.cs.cornell.edu/foundations/kinematics.pdf)
- [pmdcorp](https://www.pmdcorp.com/resources/type/articles/resources/get/motion-kinematics-article)
- [velocity-kinematics-and-statics](https://modernrobotics.northwestern.edu/nu-gm-book-resource/velocity-kinematics-and-statics/)
- [readthedocs](https://walter.readthedocs.io/en/latest/Kinematics/)
- [machinekit](https://www.machinekit.io/docs/motion/kinematics/)

### Vision

[OpenCV package](https://opencv.org/)

### Vex

[VEX EXP API](https://api.vex.com/exp/home/)
[VEX Serial](https://www.vexforum.com/t/how-can-i-read-the-serial-port-of-my-vex-exp-using-a-usb-cable/122553/3)
[VEX import modules](https://www.vexforum.com/t/how-do-i-download-modules-to-the-brain/123402)

### Other

[pySerial](https://pythonhosted.org/pyserial/shortintro.html)
[DroidCam](https://droidcam.app/)
[Stack overflow](https://stackoverflow.com/questions/25187488/python-strftime-utc-offset-not-working-as-expected-in-windows)
[Python docs](https://docs.python.org/3/c-api/buffer.html)
