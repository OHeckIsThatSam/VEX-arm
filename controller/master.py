import csv
import threading
import time
import math
import os
from datetime import datetime, timezone
from collections import namedtuple
import config
from arm_model import ArmModel
import serial_communication as serial
from time import sleep


# Config file name
OBJECT_LOG_PATH = "object_log.csv"

# Filtering rules, these are used to ensure that objects detected at least match the expected size, values in CM
MIN_WIDTH = 3.0
MAX_WIDTH = 8.0
MIN_HEIGHT = 3.0
MAX_HEIGHT = 8.0
MIN_AREA = MIN_WIDTH * MIN_HEIGHT
MAX_AREA = MAX_WIDTH * MAX_HEIGHT

# Destination rules, these are used to ensure govern how the grid of destinations is generated, and that destinations are valid and wont conflict with other blocks
MIN_DIST=10
FORBIDDEN_Y_RANGE=(-10, 10)
GRID_STEP=5
GRID_LIMIT=100

# Serial communication globals
TIMEOUT = 30
SERIAL_COMM_RETRIES = 3

# CSV data structure, must match camruler.py output to object_log.csv
DetectedObject = namedtuple("DetectedObject", ["timestamp", "iteration", "mid_x", "mid_y", "width", "height", "area"])

# Shared object store
objects = []
tracked_objects = []
objects_lock = threading.Lock()

def read_objects():
    global OBJECT_LOG_PATH, objects
    local_objects = []
    with open(OBJECT_LOG_PATH, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            obj = DetectedObject(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                iteration=row["iteration"],
                mid_x=float(row["mid_x"]),
                mid_y=float(row["mid_y"]),
                width=float(row["width"]),
                height=float(row["height"]),
                area=float(row["area"])
            )

            # Only import objects which meet the criteria set above
            if (
                MIN_WIDTH <= obj.width <= MAX_WIDTH and
                MIN_HEIGHT <= obj.height <= MAX_HEIGHT and
                MIN_AREA <= obj.area <= MAX_AREA
            ):
                local_objects.append(obj)

    # Filter to only latest iteration
    if local_objects:
        local_objects.sort(key=lambda o: o.iteration)
        max_iteration = local_objects[-1].iteration
        local_objects = [obj for obj in local_objects if obj.iteration == max_iteration]
    
    print(f"[Object Updater Thread] {len(local_objects)} have passed validation and been added to objects")

    objects.append(local_objects)

def object_updater_thread(log_path):
    global objects
    print("[Object Updater Thread] Started...")
    while True:
        updated = read_objects()
        with objects_lock:
            objects = updated
        time.sleep(0.5)


def decide_target_objects_order(objects):
    if not objects:
        return []

    # Sort objects by distance from center (0,0)
    sorted_objects = sorted(
        objects,
        key=lambda o: o.mid_x**2 + o.mid_y**2  # Distance squared from center
    )

    print(f"[Master] Target object order decided")
    i = 1
    for obj in sorted_objects:
        print(f"[Master] Object {i}: mid_x:{obj.mid_x} mid_y{obj.mid_y}")
        i += 1

    return sorted_objects

def decide_target_objects_destination(objects):
    global MIN_DIST, FORBIDDEN_Y_RANGE, GRID_STEP, GRID_LIMIT
    destinations = []
    assigned_targets = []

    def is_valid_target(tx, ty, obj):
        if FORBIDDEN_Y_RANGE[0] <= ty <= FORBIDDEN_Y_RANGE[1]:
            return False

        for other in objects:
            if other is obj:
                continue
            dist = math.hypot(tx - other.mid_x, ty - other.mid_y)
            if dist < MIN_DIST:
                return False

        for _, _, atx, aty in assigned_targets:
            dist = math.hypot(tx - atx, ty - aty)
            if dist < MIN_DIST:
                return False

        return True

    potential_targets = [
        (x, y)
        for x in range(-GRID_LIMIT, GRID_LIMIT + 1, GRID_STEP)
        for y in range(-GRID_LIMIT, GRID_LIMIT + 1, GRID_STEP)
    ]

    for obj in objects:
        for tx, ty in potential_targets:
            if is_valid_target(tx, ty, obj):
                assigned_targets.append((obj.mid_x, obj.mid_y, tx, ty))
                break
        else:
            assigned_targets.append((obj.mid_x, obj.mid_y, None, None))

    return assigned_targets


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
