import os, csv, threading, time, math, config
from datetime import datetime, timezone
from collections import namedtuple
from arm_model import ArmModel
import serial_communication as serial


# Log of objects seen by vision system
OBJECT_LOG_PATH = os.path.join(os.getcwd(), "object_log.csv") 

# Filtering rules, these are used to ensure that objects detected at least match the expected size, values in CM
MIN_WIDTH = 6.0
MAX_WIDTH = 9.0
MIN_HEIGHT = 6.0
MAX_HEIGHT = 9.0
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
    print("[Master] Starting task...")

    print("[Master] Initialising VEX arm model...")
    arm = ArmModel(config.X_LIMIT, config.Y_LIMIT, config.Z_LIMIT)
     
    lost_connection = False
    while lost_connection is False:       
        objects = read_objects()

        target_objects = decide_target_objects_order(objects)
        if not target_objects:
            print("[Master] No valid targets found.")
            time.sleep(2)
            continue  # Retry after delay

        destinations = decide_target_objects_destination(target_objects)

        for object_x, object_y, destination_x, destination_y in destinations:
            # Skip if no target assigned (fallback behaviour)
            if destination_x is None or destination_y is None:
                print(f"[Master] No target position assigned for object at ({object_x}, {object_y})")
                continue
            
            is_unreachable = False
            is_picked_up = False
            while is_picked_up is False:
                print("[Master] Calculating angles for pickup...")
                joint_angles_pickup = arm.calc_joint_degrees(object_x, object_y, config.Z_AXIS_TOLERANCE)

                if not joint_angles_pickup[0]:
                    print(f"[Master] Pickup position ({object_x}, {object_y}) is unreachable")
                    is_unreachable = True
                    break

                print("[Master] Sending command to VEX...")
                print(f"[Master] Command {joint_angles_pickup[1]} {joint_angles_pickup[2]} {joint_angles_pickup[3]} {True}")
                # Send command from joint angles and set pickup to be true
                serial.send_data(f"{joint_angles_pickup[1]} {joint_angles_pickup[2]} {joint_angles_pickup[3]} {True}")

                print(f"[Master] Awaiting vex brain confirmation message for origin...")
                response = serial.receive_data(VEX_TIMEOUT)
                if response == "":
                    print(f"[Master] Timed out while waiting for vex brain to respond, please check that the vex brain is operating correctly")
                    lost_connection = True
                    break

                # Send command to Move arm to deadzone to unblock view for camera go to closest facing direction on the x axis
                if abs(joint_angles_pickup[1]) >= 270 or abs(joint_angles_pickup[1]) <= 90:
                    print(f"[Master] Moving to deadzone: RIGHT")
                    serial.send_data(f"{0} {90} {0} {True}")
                else:
                    print(f"[Master] Moving to deadzone: LEFT")
                    serial.send_data(f"{180} {90} {0} {True}")

                print(f"[Master] Awaiting vex brain confirmation message for deadzone...")
                response = serial.receive_data(VEX_TIMEOUT)
                if response == "":
                    print(f"[Master] Timed out while waiting for vex brain to respond, please check that the vex brain is operating correctly")
                    lost_connection = True
                    break

                current_timestamp = datetime.now(tz=timezone.utc)

                print("[Master] Waiting for object list update after movement...")
                updated = False
                for i in range(CAMRULER_TIMEOUT):
                    updated_objects = read_objects()

                    # Find objects added to object log by camera after movement timestamp
                    if any(o.timestamp > current_timestamp for o in updated_objects) or len(updated_objects) == 0:
                        print(f"[Master] No objects detected near origin")
                        updated = True
                        break

                    print(f"[Master] Objects does not have an updated list of detected objects - iteration: {i}")
                    time.sleep(1)

                if updated is False:
                    #serial.send_data("Object list never updated")
                    raise TimeoutError("Object list never updated")    

                print(f"[Master] length of updated objects: {len(updated_objects)}")
                if len(updated_objects) == 0:
                    is_picked_up = True

                # Check for any object near target origin — assume pickup succeeded if none are near
                for obj in updated_objects:
                    dist = ((obj.mid_x - object_x) ** 2 + (obj.mid_y - object_y) ** 2) ** 0.5
                    print(obj)
                    print(dist)
                    if dist < 10:
                        is_picked_up = False
                        print(f"[Master] Object still near origin, pickup failed...")
                        break
                    else:
                        is_picked_up = True
                
                if is_picked_up:
                    print(f"[Master] No objects still near origin, pickup succeeded...")

            if is_unreachable:
                print("[MASTER] Unreachable object, skipping to next object...")
                continue

            print("[MASTER] calculating drop off joint angles...")
            joint_angles_dropoff = arm.calc_joint_degrees(0, 13, config.Z_AXIS_TOLERANCE + 5)

            if not joint_angles_dropoff[0]:
                print(f"[Master] Drop off position ({destination_x}, {destination_y}) is unreachable")
                continue

            serial.send_data(f"{joint_angles_dropoff[1]} {joint_angles_dropoff[2]} {joint_angles_dropoff[3]} {False}")
            print(f"[Master] Awaiting vex brain confirmation message for target...")
            response = serial.receive_data(VEX_TIMEOUT)
            if response == "":
                print(f"[Master] Timed out while waiting for vex brain to respond, please check that the vex brain is operating correctly")
                lost_connection = True
                break

            # Short cool down between actions
            time.sleep(1)
        
        time.sleep(1)

if __name__ == "__main__":
    main()
