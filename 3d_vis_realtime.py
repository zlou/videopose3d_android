'''
Realtime 3D Human Reconstruction using Posenet and Facebook's VideoPose3D
3D drawing using pygtagrph based on OpenGL
Speed: TBD
'''
import os
import sys
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.opengl as gl
import pyqtgraph as pg
from pyqtgraph.opengl import *
from argparse import ArgumentParser
import cv2
from tqdm import tqdm
import numpy as np
import time
import math

#Load the models
from joints_detectors.openpose.main import load_model as Model2Dload
model2D = Model2Dload()

from joints_detectors.openpose.main import generate_frame_kpt as OpenPoseInterface
interface2D = OpenPoseInterface

from tools.utils import videopose_model_load as Model3Dload

#Load the VideoPose3D model
model3D = Model3Dload()

from tools.utils import interface as interface3d

from tools.utils import draw_3Dimg, draw_2Dimg, videoInfo, resize_img, common


common = common()
item = 0
item_num = 0
pos_init = np.zeros(shape=(17,3))


class Visualizer(object):
    def __init__(self, input_video):
        #initialize traces to blank dict
        self.traces = dict()


        self.app = QtGui.QApplication(sys.argv)
        self.w = gl.GLViewWidget()

        self.w.opts['distance'] = 45.0       #Distance of camera from center
        self.w.opts['fov'] = 60              #Horizontal field of view in degrees
        self.w.opts['elevation'] = 10       #Camera's angle of elevation in degrees
        self.w.opts['azimuth'] = 90         #Camera's azimuthal angle in degrees

        self.w.setWindowTitle('pyqtgraph example: GLLinePlotItem')
        self.w.setGeometry(450, 700, 980, 700) 
        self.w.show()

        #Create the background grids
        gx = gl.GLGridItem()
        gx.rotate(90, 0, 1, 0)
        gx.translate(-10, 0, 0)
        self.w.addItem(gx)
        gy = gl.GLGridItem()
        gy.rotate(90, 1, 0, 0)
        gy.translate(0, -10, 0)
        self.w.addItem(gy)
        gz = gl.GLGridItem()
        gz.translate(0, 0, -10)
        self.w.addItem(gz)

        #Special settings

        #Open up a VideoCapture for live frame feed
        self.cap = cv2.VideoCapture(input_video)

        #set video name
        self.video_name = input_video.split('/')[-1].split('.')[0]

        #intialize 2D keypoints to empty array
        self.kpt2Ds = []

        pos = pos_init

        for j, j_parent in enumerate(common.skeleton_parents):
            if j_parent == -1:
                continue

            x = np.array([pos[j, 0], pos[j_parent, 0]]) * 10
            y = np.array([pos[j, 1], pos[j_parent, 1]]) * 10
            z = np.array([pos[j, 2], pos[j_parent, 2]]) * 10 - 10
            pos_total = np.vstack([x,y,z]).transpose()

            self.traces[j] = gl.GLLinePlotItem(pos=pos_total, color=pg.glColor((j, 10)), width=6,  antialias=True)
            self.w.addItem(self.traces[j])


    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()


    def set_plotdata(self, name, points, color, width):
        self.traces[name].setData(pos=points, color=color, width=width)


    def update(self):
        global item
        global item_num
        num = item/2
        azimuth_value = abs(num%120 + math.pow(-1, int((num/120))) * 120) % 120

        self.w.opts['azimuth'] = azimuth_value

        print(item, '  ')

        #read in a frame from the VideoCapture
        _, frame = self.cap.read()


        if item % 2 != 1:
            frame, W, H = resize_img(frame)
            joint2D = interface2D(frame, model2D)
            img2D  = draw_2Dimg(frame, joint2D, 1)
            if item == 0:
                for _ in range(30):
                    self.kpt2Ds.append(joint2D)
            elif item < 30:
                self.kpt2Ds.append(joint2D)
                self.kpt2Ds.pop(0)
            else:
                self.kpt2Ds.append(joint2D)
                self.kpt2Ds.pop(0)

            item += 1

            #run 2D-3D inference using VideoPose3D model
            joint3D = interface3D(model3D, np.array(self.kpt2Ds), W, H)

            pos = joint3D[-1] #(17, 3)

            for j, j_parent in enumerate(common.skeleton_parents):
                if j_parent == -1:
                    continue
                x = np.array([pos[j, 0], pos[j_parent, 0]]) * 10
                y = np.array([pos[j, 1], pos[j_parent, 1]]) * 10
                z = np.array([pos[j, 2], pos[j_parent, 2]]) * 10 - 10
                pos_total = np.vstack([x,y,z]).transpose()


                self.set_plotdata(
                    name=j, points=pos_total,
                    color=pg.glColor((j, 10)),
                    width=6)

            #Save
            if item_num < 10:
                name = '000' + str(item_num)

            elif item_num < 100:
                name = '00' + str(item_num)

            elif item_num < 1000:
                name = '0' + str(item_num)

            else:
                name = str(item_num)
            im3Dname = 'VideoSave/' + '3D_'+ name + '.png'
            d = self.w.renderToArray((img2D.shape[1], img2D.shape[0]))#(W, H)
            print('Save 3D image: ', im3Dname)
            pg.makeQImage(d).save(im3Dname)

            im2Dname = 'VideoSave/' + '2D_'+ name + '.png'
            print('Save 2D image: ', im2Dname)
            cv2.imwrite(im2Dname, img2D)

            item_num += 1
        else:
            item += 1

    #Start up the live realtime 3D animation
    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(1)
        self.start()


def main():
    #Instantiate a Visualizer object for the input video file
    v = Visualizer()

    #Start up realtime 3D animation for Visualizer
    v.animation()

    #Close all open windows after animation ends
    cv2.destroyAllWindows()

#Main entrance point
if __name__ == '__main__':
    main()