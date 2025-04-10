import os, csv, threading, time, math, config
from datetime import datetime
from collections import namedtuple
from arm_model import ArmModel
import serial_communication as serial


# Config file name
OBJECT_LOG_PATH = os.path.join(os.getcwd(), "object_log.csv") 

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
GRID_LIMIT=25

# Serial communication globals
VEX_TIMEOUT = 30
SERIAL_COMM_RETRIES = 3

CAMRULER_TIMEOUT = 30

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
    
    #print(f"[Object Updater Thread] {len(local_objects)} have passed validation and been added to objects")

    return local_objects

def object_updater_thread():
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

def main():
    global objects
    print("[Master] Starting task...")

    print("[Master] Initialising VEX arm model...")
    arm = ArmModel(config.X_LIMIT, config.Y_LIMIT, config.Z_LIMIT)
   
    print("[Master] Starting object_updater_thread...")
    thread = threading.Thread(target=object_updater_thread, daemon=True)
    thread.start()
    
    lost_connection = False
    while lost_connection is False:
        # Safely copy the current set of objects
        with objects_lock:
            current_objects = objects

        target_objects = decide_target_objects_order(current_objects)
        if not target_objects:
            print("[Master] No valid targets found.")
            # Optional: send alarm to VEX brain here
            time.sleep(5)
            continue  # Retry after delay

        destinations = decide_target_objects_destination(target_objects)

        for object_x, object_y, destination_x, destination_y in destinations:
            # Skip if no target assigned (fallback behaviour)
            if destination_x is None or destination_y is None:
                print(f"[Master] No target position assigned for object at ({object_x}, {object_y})")
                continue
            
            print("[Master] Calculating angles for pickup...")
            joint_angles_pickup = arm.calc_joint_degrees(object_x, object_y, config.Z_AXIS_TOLERANCE)

            if not joint_angles_pickup[0]:
                print(f"[Master] Pickup position ({object_x}, {object_y}) is unreachable")
                continue
                
            print("[Master] Sending command to VEX...")
            # Send command from joint angles and set pickup to be true
            serial.send_data(f"{joint_angles_pickup[1]} {joint_angles_pickup[2]} {joint_angles_pickup[3]} {True}")

            print(f"[Master] Awaiting vex brain confirmation message...")
            response = serial.receive_data(VEX_TIMEOUT)
            if response == "":
                print(f"[Master] Timed out while waiting for vex brain to respond, please check that the vex brain is operating correctly")
                lost_connection = True
                break
                
            # Send command to Move arm to deadzone to unblock view for camera
            # TODO: Calculate deadzone angles for arm, currently use defaults
            serial.send_data(f"{0} {90} {0} {True}")
            
            print(f"[Master] Awaiting vex brain confirmation message...")
            response = serial.receive_data(VEX_TIMEOUT)
            if response == "":
                print(f"[Master] Timed out while waiting for vex brain to respond, please check that the vex brain is operating correctly")
                lost_connection = True
                break

            current_timestamp = datetime.now()

            print("[Master] Waiting for object list update after movement...")
            updated = False
            for i in range(CAMRULER_TIMEOUT):
                with objects_lock:
                    updated_objects = objects

                print(updated_objects)

                # Find objects added to object log by camera after movement timestamp
                if any(datetime.fromisoformat(o.timestamp) > current_timestamp for o in updated_objects):
                    updated = True
                    break
                
                print(f"[Master] Objects does not have an updated list of detected objects - iteration: {i}")

                time.sleep(1)
            
            if updated is False:
                serial.send_data("Object list never updated")
                raise TimeoutError("Object list never updated")

            # TODO: Loop resend pickup coords if object has not been picked up. May need some retry algo that hones in on the object
            # Create a loop out of this where it retries sending the origin coords (or gets new coords from the found object, the block may have been moved)
            # success = False
            # while success is False:
            #     # Check for any object near target origin — assume pickup succeeded if none are near
            #     found = False
            #     for obj in updated_objects:
            #         dist = ((obj.mid_x - destination_x) ** 2 + (obj.mid_y - destination_y) ** 2) ** 0.5
            #         if dist < 10:
            #             found = True
            #             print(f"[Master] Object still near origin, retrying pickup...")
            #             break

            # if success:
            #     print(f"[Master] Successfully picked object from ({object_x}, {object_y}), continuing with instruction...")
            # else:
            #     print(f"[Master] Retry or handle failure case here.")

            print("[MASTER] calculating drop off joint angles...")
            joint_angles_dropoff = arm.calc_joint_degrees(destination_x, destination_y, config.Z_AXIS_TOLERANCE)

            if not joint_angles_dropoff[0]:
                print(f"[Master] Drop off position ({destination_x}, {destination_y}) is unreachable")
                continue

            serial.send_data(f"{joint_angles_dropoff[1]} {joint_angles_dropoff[2]} {joint_angles_dropoff[3]} {False}")
            print(f"[Master] Awaiting vex brain confirmation message...")
            response = serial.receive_data(VEX_TIMEOUT)
            if response == "":
                print(f"[Master] Timed out while waiting for vex brain to respond, please check that the vex brain is operating correctly")
                lost_connection = True
                break

            # Short cool down between actions, testing to confirm whether this is needed or not
            time.sleep(1)
        # Slight break between iterations
        time.sleep(1)
        # If we add more after this, uncomment the following line so that we break out of the loop when the connection to the vex brain has been determined as lost
        # if lost_connection:
        #   continue

if __name__ == "__main__":
    main()
