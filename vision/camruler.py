import os
import sys
import time
from math import hypot
import numpy as np
import cv2

import frame_capture
import frame_draw

class Maths:
    def __init__(self, calibration=None):
        self.calibration = calibration

    def conv(self, x, y):
        d = self.distance(0, 0, x, y)
        if self.calibration is None:
            raise Exception("[Maths] calibration is None")
        scale = self.calibration.values[self.baseround(d, self.calibration.pixel_base)]
        return x * scale, y * scale

    def baseround(self, x, base=1):
        return int(base * round(float(x) / base))

    def distance(self, x1, y1, x2, y2):
        return hypot(x1 - x2, y1 - y2)

class Config:
    def __init__(self):
        self.required_keys = dict(
            camera_id=(int, 0),
            camera_width=(int, 1920),
            camera_height=(int, 1080),
            camera_frame_rate=(int, 30),
            camera_fourcc=(str, cv2.VideoWriter_fourcc(*"MJPG")), # type: ignore
            auto_percent=(float, 0.2),
            auto_threshold=(int, 127),
            auto_blur=(int, 5),
            norm_alpha=(int, 0),
            norm_beta=(int, 255),
            cal_range=(int, 30),
            cal_base=(int, 5),
            pixel_base=(int, 5),
            unit_suffix=(str, "mm")
        )
        self.filepath = f"{os.getcwd()}\\camruler_config.txt"
        self.values = dict()
        self.load()

    def load(self):
        self.values = {k: v[1] for k, v in self.required_keys.items()}
        if not os.path.isfile(self.filepath):
            print(f"[Config] No config file found at {self.filepath}. Default values will be used.")
            return
        with open(self.filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or ',' not in line:
                    continue
                key, val = [x.strip() for x in line.split(',', 1)]
                if key not in self.required_keys:
                    print(f"[Config] Unknown key: {key}")
                    continue
                expected_type = self.required_keys[key][0]
                try:
                    self.values[key] = expected_type(val)
                except ValueError:
                    print(f"[Config] Invalid type for key '{key}': expected {expected_type.__name__}")

    def save(self):
        with open(self.filepath, 'w') as f:
            for key in self.required_keys:
                f.write(f"{key},{self.values[key]}\n")

    def get(self, key):
        if key not in self.values:
            raise KeyError(f"[Config] Tried to access missing key: {key}")
        return self.values[key]

    def __getitem__(self, key):
        return self.get(key)

class Calibration:
    def __init__(self, maths, diagonal_frame_size, pixel_base, cal_base, cal_range):
        self.maths = maths
        self.pixel_base = pixel_base
        self.cal_base = cal_base
        self.cal_range = cal_range
        self.filepath = f"{os.getcwd()}\\camruler_calibration.txt"
        self.diagonal_frame_size = diagonal_frame_size
        self.values = dict()
        self.load()

    def load(self):
        if not os.path.isfile(self.filepath):
            print("[Calibration] No calibration file found. Generating default.")
            self.values = {
                x: self.cal_range / self.diagonal_frame_size
                for x in range(0, int(self.diagonal_frame_size) + 1, self.pixel_base)
            }
            self.save()
            return

        with open(self.filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or ',' not in line:
                    continue
                try:
                    key, val = line.split(',', 1)
                    self.values[int(key)] = float(val)
                except ValueError:
                    print(f"[Calibration] Invalid line: {line}")

    def save(self):
        with open(self.filepath, 'w') as f:
            for k, v in self.values.items():
                f.write(f"{k},{v}\n")

    def update(self, x, y, unit_distance):
        pixel_distance = hypot(x, y)
        scale = abs(unit_distance / pixel_distance)
        target = self.maths.baseround(abs(pixel_distance), self.pixel_base)

        low = target * scale - (self.cal_base / 2)
        high = target * scale + (self.cal_base / 2)

        start = target
        if unit_distance <= self.cal_base:
            start = 0
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

        return objects
    
    def get_detected_objects(self):
        if not hasattr(self, "camera"):
            self.setup()

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

            # rotate 180
            if self.key_flags['rotate']:
                frame0 = cv2.rotate(frame0,cv2.ROTATE_90_CLOCKWISE)

            text = []

            # camera text
            fps = self.camera.current_frame_rate
            text.append(f'CAMERA: {self.config["camera_id"]} {self.width}x{self.height} {fps}FPS')

            # mouse text
            text.append('')
            if not mouse_mark:
                text.append(f'LAST CLICK: NONE')
            else:
                text.append(f'LAST CLICK: {mouse_mark} PIXELS')
            text.append(f'CURRENT XY: {self.mouse_now} PIXELS')

            #-------------------------------
            # normalize mode
            #-------------------------------
            if self.key_flags['norms']:

                # print
                text.append('')
                text.append(f'NORMILIZE MODE')
                text.append(f'ALPHA (min): {self.config["norm_alpha"]}')
                text.append(f'BETA (max): {self.config["norm_beta"]}')
                
            #-------------------------------
            # config mode
            #-------------------------------
            if self.key_flags['config']:

                # quadrant crosshairs
                self.draw.crosshairs(frame0,5,weight=2,color='red',invert=True)

                # crosshairs aligned (rotated) to maximum distance 
                self.draw.line(frame0,self.cx,self.cy, self.cx+self.cx, self.cy+self.cy,weight=1,color='red')
                self.draw.line(frame0,self.cx,self.cy, self.cx+self.cy, self.cy-self.cx,weight=1,color='red')
                self.draw.line(frame0,self.cx,self.cy,-self.cx+self.cx,-self.cy+self.cy,weight=1,color='red')
                self.draw.line(frame0,self.cx,self.cy, self.cx-self.cy, self.cy+self.cx,weight=1,color='red')

                # mouse cursor lines (parallel to aligned crosshairs)
                mx,my = self.mouse_raw
                self.draw.line(frame0,mx,my,mx+self.dm,my+(self.dm*( self.cy/self.cx)),weight=1,color='green')
                self.draw.line(frame0,mx,my,mx-self.dm,my-(self.dm*( self.cy/self.cx)),weight=1,color='green')
                self.draw.line(frame0,mx,my,mx+self.dm,my+(self.dm*(-self.cx/self.cy)),weight=1,color='green')
                self.draw.line(frame0,mx,my,mx-self.dm,my-(self.dm*(-self.cx/self.cy)),weight=1,color='green')
            
                # config text data
                text.append('')
                text.append(f'CONFIG MODE')

                # start cal
                if not cal_last:
                    cal_last = self.config.get("cal_base")
                    caltext = f'CONFIG: Click on D = {cal_last}'

                # continue cal
                elif cal_last <= self.config.get("cal_range"):
                    if mouse_mark:
                        calibration.update(*mouse_mark,cal_last) # type: ignore
                        cal_last += self.config.get("cal_base")
                    caltext = f'CONFIG: Click on D = {cal_last}'

                # done
                else:
                    self.key_flags_clear()
                    self.calibration.save() # type: ignore
                    caltext = f'CONFIG: Complete.'

                # add caltext
                self.draw.add_text(frame0,caltext,(self.cx)+100,(self.cy)+30,color='red')

                # clear mouse
                mouse_mark = None     

            #-------------------------------
            # auto mode
            #-------------------------------
            elif self.key_flags['auto']:
                
                mouse_mark = None

                # auto text data
                text.append('')
                text.append(f'AUTO MODE')
                text.append(f'UNITS: {self.config.get("unit_suffix")}')
                text.append(f'MIN PERCENT: {self.config.get("auto_percent"):.2f}')
                text.append(f'THRESHOLD: {self.config.get("auto_threshold")}')
                text.append(f'GAUSS BLUR: {auto_blur}')
                
                # gray frame
                frame1 = cv2.cvtColor(frame0,cv2.COLOR_BGR2GRAY)

                # blur frame
                auto_blur = max(1, int(auto_blur) | 1) # auto_blue must be at least 1 and odd to be a valid kernal size
                frame1 = cv2.GaussianBlur(frame1,(auto_blur,auto_blur),0)

                # threshold frame n out of 255 (85 = 33%)
                frame1 = cv2.threshold(frame1,self.config.get("auto_threshold"),255,cv2.THRESH_BINARY)[1]

                # invert
                frame1 = ~frame1 # type: ignore

                # find contours on thresholded image
                contours,nada = cv2.findContours(frame1,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                
                # small crosshairs (after getting frame1)
                self.draw.crosshairs(frame0,5,weight=2,color='green')    
            
                # loop over the contours
                for c in contours:

                    # contour data (from top left)
                    x1,y1,w,h = cv2.boundingRect(c)
                    x2,y2 = x1+w,y1+h
                    x3,y3 = x1+(w/2),y1+(h/2)

                    # convert to center-origin coordinates
                    x3r = x3 - self.cx
                    y3r = (y3 - self.cy) * -1

                    # convert to real-world units (mm → cm)
                    x3c, y3c = self.maths.conv(x3r, y3r)

                    # display coordinate label
                    self.draw.add_text(frame0, f'({x3c:.1f}cm, {y3c:.1f}cm)', x3, y3 - 12, center=True, color='blue')

                    # percent area
                    area = self.width*self.height
                    percent = 100*w*h/area
                    
                    # if the contour is too small, ignore it
                    if percent < self.config.get("auto_percent"):
                        continue

                    # if the contour is too large, ignore it
                    elif percent > 60:
                        continue

                    # convert to center, then distance
                    x1c,y1c = self.maths.conv(x1-(self.cx),y1-(self.cy))
                    x2c,y2c = self.maths.conv(x2-(self.cx),y2-(self.cy))
                    xlen = abs(x1c-x2c)
                    ylen = abs(y1c-y2c)
                    alen = 0
                    if max(xlen,ylen) > 0 and min(xlen,ylen)/max(xlen,ylen) >= 0.95:
                        alen = (xlen+ylen)/2              
                    carea = xlen*ylen

                    # plot
                    self.draw.rect(frame0,x1,y1,x2,y2,weight=2,color='red')

                    # add dimensions
                    self.draw.add_text(frame0,f'{xlen:.2f}',x1-((x1-x2)/2),min(y1,y2)-8,center=True,color='red')
                    self.draw.add_text(frame0,f'Area: {carea:.2f}',x3,y2+8,center=True,top=True,color='red')
                    if alen:
                        self.draw.add_text(frame0,f'Avg: {alen:.2f}',x3,y2+34,center=True,top=True,color='green')
                    if x1 < self.width-x2:
                        self.draw.add_text(frame0,f'{ylen:.2f}',x2+4,(y1+y2)/2,middle=True,color='red')
                    else:
                        self.draw.add_text(frame0,f'{ylen:.2f}',x1-4,(y1+y2)/2,middle=True,right=True,color='red')

            #-------------------------------
            # dimension mode
            #-------------------------------
            else:

                # small crosshairs
                self.draw.crosshairs(frame0,5,weight=2,color='green')    

                # mouse cursor lines
                self.draw.vline(frame0,self.mouse_raw[0],weight=1,color='green')
                self.draw.hline(frame0,self.mouse_raw[1],weight=1,color='green')
            
                # draw
                if mouse_mark:

                    # locations
                    x1,y1 = mouse_mark # type: ignore
                    x2,y2 = self.mouse_now

                    # convert to distance
                    x1c,y1c = self.maths.conv(x1,y1)
                    x2c,y2c = self.maths.conv(x2,y2)
                    xlen = abs(x1c-x2c)
                    ylen = abs(y1c-y2c)
                    llen = hypot(xlen,ylen)
                    alen = 0
                    if max(xlen,ylen) > 0 and min(xlen,ylen)/max(xlen,ylen) >= 0.95:
                        alen = (xlen+ylen)/2              
                    carea = xlen*ylen

                    # print distances
                    text.append('')
                    text.append(f'X LEN: {xlen:.2f}{self.config.get("unit_suffix")}')
                    text.append(f'Y LEN: {ylen:.2f}{self.config.get("unit_suffix")}')
                    text.append(f'L LEN: {llen:.2f}{self.config.get("unit_suffix")}')

                    # convert to plot locations
                    x1 += self.cx
                    x2 += self.cx
                    y1 *= -1
                    y2 *= -1
                    y1 += self.cy
                    y2 += self.cy
                    x3 = x1+((x2-x1)/2)
                    y3 = max(y1,y2)

                    # line weight
                    weight = 1
                    if self.key_flags['lock']:
                        weight = 2

                    # plot
                    self.draw.rect(frame0,x1,y1,x2,y2,weight=weight,color='red')
                    self.draw.line(frame0,x1,y1,x2,y2,weight=weight,color='green')

                    # add dimensions
                    self.draw.add_text(frame0,f'{xlen:.2f}',x1-((x1-x2)/2),min(y1,y2)-8,center=True,color='red')
                    self.draw.add_text(frame0,f'Area: {carea:.2f}',x3,y3+8,center=True,top=True,color='red')
                    if alen:
                        self.draw.add_text(frame0,f'Avg: {alen:.2f}',x3,y3+34,center=True,top=True,color='green')           
                    if x2 <= x1:
                        self.draw.add_text(frame0,f'{ylen:.2f}',x1+4,(y1+y2)/2,middle=True,color='red')
                        self.draw.add_text(frame0,f'{llen:.2f}',x2-4,y2-4,right=True,color='green')
                    else:
                        self.draw.add_text(frame0,f'{ylen:.2f}',x1-4,(y1+y2)/2,middle=True,right=True,color='red')
                        self.draw.add_text(frame0,f'{llen:.2f}',x2+8,y2-4,color='green')

            # add usage key
            text.append('')
            text.append(f'Q = QUIT')
            text.append(f'R = ROTATE')
            text.append(f'N = NORMALIZE')
            text.append(f'A = AUTO-MODE')
            if self.key_flags['auto']:
                text.append(f'P = MIN-PERCENT')
                text.append(f'T = THRESHOLD')
                text.append(f'T = GAUSS BLUR')
            text.append(f'C = CONFIG-MODE')
            
            # draw top-left text block
            self.draw.add_text_top_left(frame0,text)

            # Get scale near center (mm per pixel)
            try:
                scale_at_center = self.calibration.values.get(0) or self.config.get("pixel_base")  # type: ignore # use center scale or close to it
                px_per_cm = int(round(1 / scale_at_center)) # pixels per 10mm = 1cm
            except (KeyError, ZeroDivisionError, TypeError):
                px_per_cm = None

            # Draw centimeter grid if calibration is valid
            if px_per_cm and px_per_cm > 0:
                for x in range(self.cx, self.width, px_per_cm):
                    self.draw.vline(frame0, x, weight=1, color='orange')
                for x in range(self.cx, 0, -px_per_cm):
                    self.draw.vline(frame0, x, weight=1, color='orange')
                for y in range(self.cy, self.height, px_per_cm):
                    self.draw.hline(frame0, y, weight=1, color='orange')
                for y in range(self.cy, 0, -px_per_cm):
                    self.draw.hline(frame0, y, weight=1, color='orange')

            # display
            framename = "Robot Vision"
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
                self.key_event(key)

            # Teardown
            self.camera.stop()
            cv2.destroyAllWindows()
            print("[App] Shutdown complete.")

if __name__ == "__main__":
    app = App()
    app.run()
