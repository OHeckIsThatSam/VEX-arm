# -------------------------------------------------------------
# Adapted from: https://gitlab.com/duder1966/youtube-projects
# Original Project: camruler (OpenCV-based measurement tool)
# Author: duder1966
# -------------------------------------------------------------

import os,sys,time,traceback
from math import hypot
import numpy as np
import cv2

import frame_capture
import frame_draw

import csv
from datetime import datetime

# --- Object logging ---
object_log = []
log_interval = 5  # seconds
last_log_time = time.time()
log_file = "object_log.csv"
iteration = 0

# Delete contents of log_file
if os.path.exists(log_file):
    open(log_file, 'w').close()

# Config fallbacks
camera_id = 0
camera_width = 1920
camera_height = 1080
camera_frame_rate = 30
camera_fourcc = cv2.VideoWriter_fourcc(*"MJPG")

# Auto measure mouse events
auto_percent = 0.2 
auto_threshold = 127
auto_blur = 5

# normalization mouse events
norm_alpha = 0
norm_beta = 255

#-------------------------------
# read config file
#-------------------------------

# you can make a config file "camruler_config.csv"
# this is a comma-separated file with one "item,value" pair per line
# you can also use a "=" separated pair like "item=value"
# you can use # to comment a line
# the items must be named like the default variables above

# read local config values
configfile = 'camruler_config.csv'
if os.path.isfile(configfile):
    with open(configfile) as f:
        for line in f:
            line = line.strip()
            if line and line[0] != '#' and (',' in line or '=' in line):
                if ',' in line:
                    item,value = [x.strip() for x in line.split(',',1)]
                elif '=' in line:
                    item,value = [x.strip() for x in line.split('=',1)]
                else:
                    continue                        
                if item in 'camera_id camera_width camera_height camera_frame_rate camera_fourcc auto_percent auto_threshold auto_blur norm_alpha norm_beta'.split():
                    try:
                        exec(f'{item}={value}')
                        print('CONFIG:',(item,value))
                    except:
                        print('CONFIG ERROR:',(item,value))

#-------------------------------
# camera setup
#-------------------------------

# camera thread setup
camera = frame_capture.Camera_Thread()
camera.camera_source = camera_id
camera.camera_width  = camera_width
camera.camera_height = camera_height
camera.camera_frame_rate = camera_frame_rate
camera.camera_fourcc = camera_fourcc

camera.start()

width  = camera.camera_width
height = camera.camera_height
area = width*height
cx = int(width/2)
cy = int(height/2)
dm = hypot(cx,cy) # max pixel distance
frate  = camera.camera_frame_rate

#-------------------------------
# frame drawing/text module 
#-------------------------------

draw = frame_draw.DRAW()
draw.width = width
draw.height = height

#-------------------------------
# conversion (pixels to measure)
#-------------------------------

unit_suffix = 'mm'

# calibrate every N pixels
pixel_base = 5

# maximum field of view from center to farthest edge
cal_range = 28

# initial calibration values table {pixels:scale}
# this is based on the frame size and the cal_range
cal = dict([(x,cal_range/dm) for x in range(0,int(dm)+1,pixel_base)])

# calibration loop values
# inside of main loop below
cal_base = 5
cal_last = None

def cal_update(x,y,unit_distance):

    pixel_distance = hypot(x,y)
    scale = abs(unit_distance/pixel_distance)
    target = baseround(abs(pixel_distance),pixel_base)

    # low-high values in distance
    low  = target*scale - (cal_base/2)
    high = target*scale + (cal_base/2)

    # get low start point in pixels
    start = target
    if unit_distance <= cal_base:
        start = 0
    else:
        while start*scale > low:
            start -= pixel_base

    # get high stop point in pixels
    stop = target
    if unit_distance >= baseround(cal_range,pixel_base):
        high = max(cal.keys())
    else:
        while stop*scale < high:
            stop += pixel_base

    # set scale
    for x in range(start,stop+1,pixel_base):
        cal[x] = scale
        print(f'CAL: {x} {scale}')

# read local calibration data
calfile = 'camruler_cal.csv'
if os.path.isfile(calfile):
    with open(calfile) as f:
        for line in f:
            line = line.strip()
            if line and line[0] in ('d',):
                axis,pixels,scale = [_.strip() for _ in line.split(',',2)]
                if axis == 'd':
                    print(f'LOAD: {pixels} {scale}')
                    cal[int(pixels)] = float(scale)

# convert pixels to units
def conv(x,y):
    d = distance(0,0,x,y)

    scale = cal[baseround(d,pixel_base)]

    return x*scale,y*scale

# round to a given base
def baseround(x,base=1):
    return int(base * round(float(x)/base))

# distance formula 2D
def distance(x1,y1,x2,y2):
    return hypot(x1-x2,y1-y2)

#-------------------------------
# define frames
#-------------------------------

# define display frame
framename = "Robot Vision"
cv2.namedWindow(framename,flags=cv2.WINDOW_NORMAL|cv2.WINDOW_GUI_NORMAL)

#-------------------------------
# key events
#-------------------------------

key_last = 0
key_flags = {'config':False, # c key
             'auto':False,   # a key
             'thresh':False, # t key
             'percent':False,# p key
             'norms':False,  # n key
             'rotate':False, # r key
             'lock':False,   # 
             }

def key_flags_clear():
    global key_flags

    for key in list(key_flags.keys()):
        if key not in ('rotate',):
            key_flags[key] = False

def key_event(key):
    global key_last
    global key_flags
    global mouse_mark
    global cal_last

    # config mode
    if key == 99:
        if key_flags['config']:
            key_flags['config'] = False
        else:
            key_flags_clear()
            key_flags['config'] = True
            cal_last,mouse_mark = 0,None

    # normilization mode
    elif key == 110:
        if key_flags['norms']:
            key_flags['norms'] = False
        else:
            key_flags['thresh'] = False
            key_flags['percent'] = False
            key_flags['lock'] = False
            key_flags['norms'] = True
            mouse_mark = None

    # rotate
    elif key == 114:
        if key_flags['rotate']:
            key_flags['rotate'] = False
        else:
            while start * scale > low:
                start -= self.pixel_base

        stop = target
        if unit_distance >= self.maths.baseround(self.cal_range, self.pixel_base):
            high = max(self.values.keys())
        else:
            while stop * scale < high:
                stop += self.pixel_base

        for px in range(int(start), int(stop) + 1, self.pixel_base):
            self.values[px] = scale
            print(f'CAL: {px} {scale}')

class App:
    def __init__(self):
        self.config = Config()
        self.maths = Maths()
        self.calibration = None
        self.key_flags = {
            'config': False,
            'cal_range_config': False,
            'auto': False,
            'thresh': False,
            'percent': False,
            'norms': False,
            'rotate': False,
            'lock': False
        }
        self.mouse_raw = (0, 0)
        self.mouse_now = (0, 0)
        self.mouse_mark = None
        self.cal_last = None
        self.detected_objects = []

    def key_event(self, key):
        if key == ord('c'):
            self.key_flags['config'] = not self.key_flags['config']
            self.cal_last, self.mouse_mark = (0, None) if self.key_flags['config'] else (None, self.mouse_mark)
        elif key == ord('n'):
            self.key_flags_clear()
            self.key_flags['norms'] = True
        elif key == ord('r'):
            self.key_flags['rotate'] = not self.key_flags['rotate']
        elif key == ord('a'):
            self.key_flags_clear()
            self.key_flags['auto'] = True
        elif key == ord('p') and self.key_flags['auto']:
            self.key_flags['percent'] = not self.key_flags['percent']
        elif key == ord('t') and self.key_flags['auto']:
            self.key_flags['thresh'] = not self.key_flags['thresh']

    def key_flags_clear(self):
        for key in self.key_flags:
            if key != 'rotate':
                self.key_flags[key] = False

    def setup(self):
        self.camera = frame_capture.Camera_Thread()
        self.camera.camera_source = self.config['camera_id'] # type: ignore
        self.camera.camera_width = self.config['camera_width'] # type: ignore
        self.camera.camera_height = self.config['camera_height'] # type: ignore
        self.camera.camera_frame_rate = self.config['camera_frame_rate'] # type: ignore
        self.camera.camera_fourcc = self.config['camera_fourcc']
        self.camera.start()

        self.width = self.camera.camera_width
        self.height = self.camera.camera_height
        self.cx = int(self.width / 2)
        self.cy = int(self.height / 2)
        self.dm = hypot(self.cx, self.cy)

        self.calibration = Calibration(
            self.maths,
            self.dm,
            self.config['pixel_base'],
            self.config['cal_base'],
            self.config['cal_range']
        )
        self.maths.calibration = self.calibration
        self.draw = frame_draw.DRAW()
        self.draw.width = self.width
        self.draw.height = self.height

    def process_frame(self, frame):
        # Normalize
        cv2.normalize(frame, frame, self.config["norm_alpha"], self.config["norm_beta"], cv2.NORM_MINMAX)
        if self.key_flags['rotate']:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur_size = max(1, int(self.config["auto_blur"]) | 1)
        frame_blur = cv2.GaussianBlur(frame_gray, (blur_size, blur_size), 0)
        thresh = cv2.threshold(frame_blur, self.config["auto_threshold"], 255, cv2.THRESH_BINARY)[1]
        thresh = ~thresh  # Invert

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        objects = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            percent = 100 * area / (self.width * self.height)

            if percent < self.config.get("auto_percent") or percent > 60:
                continue

            cx_pixel = x + w / 2
            cy_pixel = y + h / 2

            # Convert to center-origin
            x_centered = cx_pixel - self.cx
            y_centered = (cy_pixel - self.cy) * -1
            x_real, y_real = self.maths.conv(x_centered, y_centered)

            objects.append((x_real, y_real))

        # find contours on thresholded image
        contours,nada = cv2.findContours(frame1,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        
        # small crosshairs (after getting frame1)
        draw.crosshairs(frame0,5,weight=2,color='green')    

        object_log.clear()

        # loop over the contours
        for c in contours:

        frame = self.camera.next(wait=1)
        if frame is None:
            return []

        return self.process_frame(frame)

    def run(self):
        print("[App] Starting...")
        self.setup()
        
        while 1:
            frame0 = self.camera.next(wait=1)
            if frame0 is None:
                time.sleep(0.1)
                continue

            # normalize
            cv2.normalize(frame0,frame0,self.config["norm_alpha"],self.config["norm_beta"],cv2.NORM_MINMAX)

            # percent area
            percent = 100*w*h/area
            
            # if the contour is too small, ignore it
            if percent < auto_percent:
                    continue

            # camera text
            fps = self.camera.current_frame_rate
            text.append(f'CAMERA: {self.config["camera_id"]} {self.width}x{self.height} {fps}FPS')

            # convert to center, then distance
            x1c,y1c = conv(x1-(cx),y1-(cy))
            x2c,y2c = conv(x2-(cx),y2-(cy))
            xlen = abs(x1c-x2c)
            ylen = abs(y1c-y2c)
            alen = 0
            if max(xlen,ylen) > 0 and min(xlen,ylen)/max(xlen,ylen) >= 0.95:
                alen = (xlen+ylen)/2              
            carea = xlen*ylen

            # log object data
            object_log.append({
                "iteration": iteration,
                "mid_x": round(x3c, 2),
                "mid_y": round(y3c, 2),
                "width": round(xlen, 2),
                "height": round(ylen, 2),
                "area": round(carea, 2)
            })

            # plot
            draw.rect(frame0,x1,y1,x2,y2,weight=2,color='red')

            # add dimensions
            draw.add_text(frame0,f'{xlen:.2f}',x1-((x1-x2)/2),min(y1,y2)-8,center=True,color='red')
            draw.add_text(frame0,f'Area: {carea:.2f}',x3,y2+8,center=True,top=True,color='red')
            if alen:
                draw.add_text(frame0,f'Avg: {alen:.2f}',x3,y2+34,center=True,top=True,color='green')
            if x1 < width-x2:
                draw.add_text(frame0,f'{ylen:.2f}',x2+4,(y1+y2)/2,middle=True,color='red')
            else:
                draw.add_text(frame0,f'{ylen:.2f}',x1-4,(y1+y2)/2,middle=True,right=True,color='red')

    #-------------------------------
    # dimension mode
    #-------------------------------
    else:

        # small crosshairs
        draw.crosshairs(frame0,5,weight=2,color='green')    

        # mouse cursor lines
        draw.vline(frame0,mouse_raw[0],weight=1,color='green')
        draw.hline(frame0,mouse_raw[1],weight=1,color='green')
       
        # draw
        if mouse_mark:

            # locations
            x1,y1 = mouse_mark
            x2,y2 = mouse_now

            # convert to distance
            x1c,y1c = conv(x1,y1)
            x2c,y2c = conv(x2,y2)
            xlen = abs(x1c-x2c)
            ylen = abs(y1c-y2c)
            llen = hypot(xlen,ylen)
            alen = 0
            if max(xlen,ylen) > 0 and min(xlen,ylen)/max(xlen,ylen) >= 0.95:
                alen = (xlen+ylen)/2              
            carea = xlen*ylen

            # print distances
            text.append('')
            if not mouse_mark:
                text.append(f'LAST CLICK: NONE')
            else:
                draw.add_text(frame0,f'{ylen:.2f}',x1-4,(y1+y2)/2,middle=True,right=True,color='red')
                draw.add_text(frame0,f'{llen:.2f}',x2+8,y2-4,color='green')
    
    # check if it's time to write the log
    if time.time() - last_log_time > log_interval and object_log:
        write_header = not os.path.exists(log_file)

        with open(log_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["iteration", "mid_x", "mid_y", "width", "height", "area"])
            if write_header:
                writer.writeheader()
            writer.writerows(object_log)

        print(f"[LOG] Wrote {len(object_log)} objects to {log_file}")
        object_log.clear()
        last_log_time = time.time()
        iteration += 1

    # add usage key
    text.append('')
    text.append(f'Q = QUIT')
    text.append(f'R = ROTATE')
    text.append(f'N = NORMALIZE')
    text.append(f'A = AUTO-MODE')
    if key_flags['auto']:
        text.append(f'P = MIN-PERCENT')
        text.append(f'T = THRESHOLD')
        text.append(f'T = GAUSS BLUR')
    text.append(f'C = CONFIG-MODE')
    
    # draw top-left text block
    draw.add_text_top_left(frame0,text)

    # Get scale near center (mm per pixel)
    try:
        scale_at_center = cal.get(0) or cal[pixel_base]  # use center scale or close to it
        px_per_cm = int(round(1 / scale_at_center))     # pixels per 10mm = 1cm
    except (KeyError, ZeroDivisionError, TypeError):
        px_per_cm = None

    # Draw centimeter grid if calibration is valid
    if px_per_cm and px_per_cm > 0:
        for x in range(cx, width, px_per_cm):
            draw.vline(frame0, x, weight=1, color='orange')
        for x in range(cx, 0, -px_per_cm):
            draw.vline(frame0, x, weight=1, color='orange')
        for y in range(cy, height, px_per_cm):
            draw.hline(frame0, y, weight=1, color='orange')
        for y in range(cy, 0, -px_per_cm):
            draw.hline(frame0, y, weight=1, color='orange')

    # display
    cv2.imshow(framename,frame0)

    # key delay and action
    key = cv2.waitKey(1) & 0xFF

    # esc ==  27 == quit
    # q   == 113 == quit
    if key in (27,113):
        break

    # key data
    #elif key != 255:
    elif key not in (-1,255):
        key_event(key)

#-------------------------------
# kill sequence
#-------------------------------

# close camera thread
camera.stop()

# close all windows
cv2.destroyAllWindows()

# done
exit()
