import csv
from datetime import datetime
from collections import namedtuple

# Config file name
LOG_FILE = "object_log.csv"

# Filtering rules, these are used to ensure that objects detected at least match the expected size, values in MM
MIN_WIDTH = 30.0
MAX_WIDTH = 80.0
MIN_HEIGHT = 30.0
MAX_HEIGHT = 80.0
MIN_AREA = 200.0
MAX_AREA = 1000.0

# CSV data structure, must match camruler.py output to object_log.csv
DetectedObject = namedtuple("DetectedObject", ["iteration", "mid_x", "mid_y", "width", "height", "area"])

# --- Functions ---

def read_objects(log_path):
    # Here we read in the latest objects written to the object log
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

def get_motor_positions(): # Placeholder, replace with kinematics
    return {"joint1": 0, "joint2": 0, "joint3": 0}

def send_command(target_position): # Placeholder, replace with serial communication
    print(f"[COMMAND] Moving to: {target_position}")

def receieve_command(): # Placeholder, replace with serial communcation
    # Here we wait for the vex to report that it has finished moving and is awaiting the next instruction
    print(f"[COMMAND] Awaiting reponse from VEX brain")

def main():
    print("[Master] Starting task...")
    objects = read_objects(LOG_FILE)
    print(f"[Master] Read {len(objects)} objects from log")

    filtered = filter_objects(objects)
    print(f"[Master] {len(filtered)} objects passed filtering")

    target = choose_target_object(filtered)
    if not target:
        print("[Master] No valid targets found.")
        return

    print(f"[Master] Chosen target at ({target.mid_x}, {target.mid_y}), area={target.area}")

    motor_positions = get_motor_positions()
    print(f"[Master] Current motor state: {motor_positions}")

    send_command((target.mid_x, target.mid_y))

if __name__ == "__main__":
    main()
