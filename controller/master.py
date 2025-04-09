import csv
import threading
import time
import math
from datetime import datetime, timezone
from collections import namedtuple

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


def get_motor_positions(x, y): # Placeholder, replace with kinematics
    return {"joint1": 0, "joint2": 0, "joint3": 0}

def send_command(target_position): # Placeholder, replace with serial communication
    print(f"[SERIAL COMMUNICATION] Sending instructions for: {target_position}")
    # TODO: this

def receive_message():
    global TIMEOUT, SERIAL_COMM_RETRIES
    print(f"[SERIAL COMMUNICATION] Awaiting response message from vex brain...")

    for attempt in range(1, SERIAL_COMM_RETRIES + 1):
        print(f"[SERIAL COMMUNICATION] Attempt {attempt} of {SERIAL_COMM_RETRIES}...")

        start_time = time.time()
        while time.time() - start_time < TIMEOUT:
            message = read_serial_message()  # TODO: plug in our serial comm function
            if message:
                print(f"[SERIAL COMMUNICATION] Received message: {message}")
                return message

            time.sleep(0.1)

        print(f"[SERIAL COMMUNICATION] Timeout on attempt {attempt}. Retrying...")

    print(f"[SERIAL COMMUNICATION] All attempts failed after {SERIAL_COMM_RETRIES} tries.")
    return None

def receieve_command(): # Placeholder, replace with serial communcation
    # Here we wait for the vex to report that it has finished moving and is awaiting the next instruction
    print(f"[COMMAND] Awaiting reponse from VEX brain")

def main():
    global objects
    print("[Master] Starting task...")
    print("[Master] Starting object_updater_thread...")
    thread = threading.Thread(target=object_updater_thread, daemon=True)
    thread.start()

    with objects_lock:
        current_objects = objects
    
    lost_connection = False
    while lost_connection is False:
        # Safely copy the current set of objects
        with objects_lock:
            current_objects = list(objects)

        target_order = decide_target_objects_order(current_objects)
        if not target_order:
            print("[Master] No valid targets found.")
            # Optional: send alarm to VEX brain here
            time.sleep(5)
            continue  # Retry after delay

        destinations = decide_target_objects_destination(target_order)

        for current_x, current_y, deadzone_x, deadzone_y, target_x, target_y in destinations:
            # Skip if no target assigned (fallback behavior)
            if target_x is None or target_y is None:
                print(f"[Master] No target assigned for object at ({current_x}, {current_y})")
                continue

            motor_positions_origin = get_motor_positions(current_x, current_y)
            motor_positions_deadzone = get_motor_positions(deadzone_x, deadzone_y)
            motor_positions_dropoff = get_motor_positions(target_x, target_y)

            print(f"[Master] Moving from ({current_x}, {current_y}) to : ({target_x}, {target_y})")

            # Move to object origin
            # TODO: Send motor positions to the robot
            #send_command(motor_positions_origin)
            print(f"[Master] Awaiting vex brain confirmation message...")
            if recieve_message() is None:
                print(f"[Master] Timed out while waiting for vex brain to respond, please check that the vex brain is operating correctly")
                lost_connection = True
                break

            # Move to object deadzone
            # TODO: Send motor positions to the robot
            # send_command(motor_positions_origin)
            if recieve_message() is False:
                print(f"[Master] Timed out while waiting for vex brain to respond, please check that the vex brain is operating correctly")
                lost_connection = True
                break

            current_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

            # Wait for fresh object data with updated object locations
            print("[Master] Waiting for object list update after movement...")

            while True:
                with objects_lock:
                    updated_objects = list(objects)

                if any(o.timestamp > current_timestamp for o in updated_objects):
                    break

                time.sleep(0.5)


            # Create a loop out of this where it retries sending the origin coords (or gets new coords from the found object, the block may have been moved)
            success = False
            while success is False:
                # Check for any object near target origin — assume pickup succeeded if none are near
                found = False
                for obj in updated_objects:
                    dist = ((obj.mid_x - target_x) ** 2 + (obj.mid_y - target_y) ** 2) ** 0.5
                    if dist < 10:
                        found = True
                        print(f"[Master] Object still near origin, retrying pickup...")
                        break

                
                        
            if success:
                print(f"[Master] Successfully picked object from ({current_x}, {current_y}), continuing with instruction...")
            else:
                print(f"[Master] Retry or handle failure case here.")

            # Move to object target
            # TODO: Send motor positions to the robot
            #send_command(motor_positions_origin)
            if recieve_message(timeout) is False:
                print(f"[Master] Timed out while waiting for vex brain to respond, please check that the vex brain is operating correctly")

            # Short cooldown between actions, testing to confirm whether this is needed or not
            time.sleep(1)

        # If we add more afer this, uncomment the following line so that we break out of the loop when the connection to the vex brain has been determined as lost
        # if lost_connection:
        #   continue

if __name__ == "__main__":
    main()
