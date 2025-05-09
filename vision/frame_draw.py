# -------------------------------------------------------------
# Adapted from: https://gitlab.com/duder1966/youtube-projects
# Original Project: camruler (OpenCV-based measurement tool)
# Author: duder1966
# -------------------------------------------------------------

import cv2

class DRAW:

    # config fallback
    width = 1920
    height = 1080

    # colors B-G-R
    colors = {'red'   :(  0,  0,255),
              'green' :(  0,255,  0),
              'blue'  :(255,  0,  0),
              'yellow':(  0,255,255),
              'gray'  :(200,200,200),
              }

    def add_text_top_left(self,frame,text):

        if type(text) not in (list,tuple):
            text = text.split('\n')
        text = [line.rstrip() for line in text]
        
        color = self.colors.get('blue',(0,255,255))
            
        lineloc = 10
        lineheight = 30

        for line in text:
            lineloc += lineheight
            cv2.putText(frame,
                        line,
                        (10,lineloc), # location
                        cv2.FONT_HERSHEY_SIMPLEX, # font
                        0.8, # size
                        color, # color
                        1, # line width
                        cv2.LINE_AA,
                        False)

    # add text anywhere
    def add_text(self,frame,text,x,y,size=0.8,color='yellow',center=False,middle=False,top=False,right=False):

        color = self.colors.get(color,(0,255,255))
        font = cv2.FONT_HERSHEY_SIMPLEX

        textsize = cv2.getTextSize(text,font,size,1)[0]

        if center:
            x -= textsize[0]/2
        elif right:
            x -= textsize[0]
        if top:
            y += textsize[1]
        elif middle:
            y += textsize[1]/2

        cv2.putText(frame,
                    text,
                    (int(x),int(y)),
                    font,
                    size,
                    color,
                    1, # line width
                    cv2.LINE_AA,
                    False)

    # line
    def line(self,frame,x1,y1,x2,y2,weight=1,color='green'):
        cv2.line(frame,(int(x1),int(y1)),(int(x2),int(y2)),self.colors.get(color,(0,255,0)),weight)

    # vertical line
    def vline(self,frame,x=0,weight=1,color='green'):
        if x <= 0:
            x = self.width/2
        x = int(x)
        cv2.line(frame,(x,0),(x,self.height),self.colors.get(color,(0,255,0)),weight)
        
    # horizontal line
    def hline(self,frame,y=0,weight=1,color='green'):
        if y <= 0:
            y = self.height/2
        y = int(y)
        cv2.line(frame,(0,y),(self.width,y),self.colors.get(color,(0,255,0)),weight)

    # rectangle
    def rect(self,frame,x1,y1,x2,y2,weight=1,color='green',filled=False,mark_center=True):
        if filled:
            weight = -1

        cv2.rectangle(frame,(int(x1),int(y1)),(int(x2),int(y2)),self.colors.get(color,(0,255,0)),weight)

        # mark center point
        if mark_center:
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            cv2.circle(frame, (cx, cy), 3, self.colors.get(color,(0,255,0)), -1)


    # circle
    def circle(self,frame,x1,y1,x2,y2,r,weight=1,color='green',filled=False):
        if filled:
            weight = -1
        cv2.circle(frame,(int(x1),int(y1)),(int(x2),int(y2)),int(r),self.colors.get(color,(0,255,0)),weight)

    # centered crosshairs full frame
    def crosshairs_full(self,frame,weight=1,color='green'):
        self.vline(frame,0,weight,color)
        self.hline(frame,0,weight,color)

    # centered crosshairs
    def crosshairs(self,frame,offset=10,weight=1,color='green',invert=False):
        offset = self.width*offset/200
        xcenter = self.width/2
        ycenter = self.height/2
        if invert:
            self.line(frame,0,ycenter,xcenter-offset,ycenter,weight,color)
            self.line(frame,xcenter+offset,ycenter,self.width,ycenter,weight,color)
            self.line(frame,xcenter,0,xcenter,ycenter-offset,weight,color)
            self.line(frame,xcenter,ycenter+offset,xcenter,self.height,weight,color)
        else:
            self.line(frame,xcenter-offset,ycenter,xcenter+offset,ycenter,weight,color)
            self.line(frame,xcenter,ycenter-offset,xcenter,ycenter+offset,weight,color)      
