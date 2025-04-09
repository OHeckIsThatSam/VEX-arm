import csv
import os
from datetime import datetime
from collections import namedtuple
import config
from arm_model import ArmModel
import serial_communication as serial
from time import sleep


# Config file name
LOG_FILE = os.path.join(os.getcwd(), 'object_log.csv')

# Filtering rules, these are used to ensure that objects detected at least match the expected size, values in MM
MIN_WIDTH = 4.0
MAX_WIDTH = 8.0
MIN_HEIGHT = 5
MAX_HEIGHT = 8.0
MIN_AREA = 20.0
MAX_AREA = 100.0

# CSV data structure, must match camruler.py output to object_log.csv
DetectedObject = namedtuple("DetectedObject", ["iteration", "mid_x", "mid_y", "width", "height", "area"])

# --- Functions ---

def read_objects(log_path):
    # Here we read in the latest objects written to the object log
    print(f"Reading from path: {log_path}")
    objects = []
    with open(log_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            obj = DetectedObject(
                iteration=row["iteration"],
                mid_x=float(row["mid_x"]),
                mid_y=float(row["mid_y"]),
                width=float(row["width"]),
                height=float(row["height"]),
                area=float(row["area"])
            )
            objects.append(obj)

        objects.sort(key=lambda o: o.iteration)
        max_iteration = objects[-1].iteration
        objects = [obj for obj in objects if obj.iteration == max_iteration]
        
    return objects

def filter_objects(objects):
    # Here we filter out objects as best we can using the values defined at the top so only valid objects are left
    return [
        obj for obj in objects
        if MIN_WIDTH <= obj.width <= MAX_WIDTH
        and MIN_HEIGHT <= obj.height <= MAX_HEIGHT
        and MIN_AREA <= obj.area <= MAX_AREA
    ]

def choose_target_object(filtered_objects):
    if not filtered_objects:
        return None

    # Currently picks the closest object, this will only work for a few times until one object cannot be placed further away then the others and will always be picked
    # I propose that we order the objects by closest -> further on load and that's the order we go with, or we could pick randomly, but for now this will do until we
    # decide on what the system should achieve with the blocks
    return min(filtered_objects, key=lambda o: (o.mid_x**2 + o.mid_y**2))

def send_command(joint_commands): # Placeholder, replace with serial communication
    print(f"[COMMAND] Moving to: {joint_commands}")
    serial.send_data(joint_commands)

def receive_command():
    print(f"[COMMAND] Awaiting response from VEX brain")
    response = serial.receive_data()

    if response is "":
        print("[COMMAND] Communication port couldn't be opened")
        return
    
    # Temp print response (do whatever necessary with response)
    print(f"[COMMAND] Response received: {response}")

def main():
    arm = ArmModel(config.X_LIMIT, config.Y_LIMIT, config.Z_LIMIT)

    print("[Master] Starting task...")
    while True:
        objects = read_objects(LOG_FILE)
        print(f"[Master] Read {len(objects)} objects from log")

        filtered = filter_objects(objects)
        print(f"[Master] {len(filtered)} objects passed filtering")

        target = choose_target_object(filtered)
        if not target:
            print("[Master] No valid targets found.")
            sleep(1)
            continue

        print(f"[Master] Chosen target at ({target.mid_x}, {target.mid_y}), area={target.area}")

        motor_positions = arm.calc_joint_degrees(x=target.mid_x, y=target.mid_y, z=config.Z_AXIS_TOLERANCE)
        print(f"[Master] Current motor state: {motor_positions}")

        if not motor_positions[0]:
            print("[Master] Can't move to location")
            sleep(5)
            continue
        
        base_angle = round(motor_positions[1], 1)
        shoulder_angle = round(motor_positions[2], 1)
        elbow_angle = round(motor_positions[3], 1)
        is_pickup = True
        
        send_command(f"{base_angle} {shoulder_angle} {elbow_angle} {is_pickup}")

        # Wait for response
        receive_command()

if __name__ == "__main__":
    main()
