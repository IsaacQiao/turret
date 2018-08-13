#changed 6-11-2018
#V1
try:
    import cv2
except Exception as e:
    print("Warning: OpenCV not installed. To use motion detection, make sure you've properly configured OpenCV.")

import time
import _thread
import threading
import atexit
import sys
import termios
import contextlib
import picamera
import picamera.array
import numpy as np
import io

import imutils
import RPi.GPIO as GPIO
from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor


### User Parameters ###

MOTOR_X_REVERSED = True

MAX_STEPS_X = 30

RELAY_PIN = 22


output = np.empty((240, 320, 3), dtype = np.uint8)

#######################


@contextlib.contextmanager
def raw_mode(file):
    """
    Magic function that allows key presses.
    :param file:
    :return:
    """
    old_attrs = termios.tcgetattr(file.fileno())
    new_attrs = old_attrs[:]
    new_attrs[3] = new_attrs[3] & ~(termios.ECHO | termios.ICANON)
    try:
        termios.tcsetattr(file.fileno(), termios.TCSADRAIN, new_attrs)
        yield
    finally:
        termios.tcsetattr(file.fileno(), termios.TCSADRAIN, old_attrs)


class VideoUtils(object):
    """
    Helper functions for video utilities.
    """
    def __init__(self, camera):
        self.camera = camera
        self.prev_frame = ''
        self.tempFrame = ''

    def rasp_find_motion(self, stream, callback=0):

        frame = stream

        # resize the frame, convert it to grayscale, and blur it
        frame = imutils.resize(frame, width=500)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # if the first frame is None, initialize it
        if self.prev_frame == '':
            self.prev_frame = gray
            self.tempFrame = gray
            return
        else:
            delta = cv2.absdiff(self.tempFrame, gray)
            self.tempFrame = gray
            tst = cv2.threshold(delta, 5, 255, cv2.THRESH_BINARY)[1]
            tst = cv2.dilate(tst, None, iterations=2)
            print ("Done.\n Waiting for motion.")
            if not cv2.countNonZero(tst) > 0:
                self.prev_frame = gray
            else:
                print ('not done')

        # compute the absolute difference between the current frame and
        # first frame
        frameDelta = cv2.absdiff(self.prev_frame, gray)
        print(frameDelta)
        thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        thresh = cv2.dilate(thresh, None, iterations=2)
        c = self.get_best_contour(thresh.copy(), 5000)

        if c is not None:
            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            callback(c, frame)



    def get_best_contour(self, imgmask, threshold):
        im, contours, hierarchy = cv2.findContours(imgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_area = threshold
        best_cnt = None
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > best_area:
                best_area = area
                best_cnt = cnt
        return best_cnt


class Turret(object):
    """
    Class used for turret control.
    """

    def __init__(self, camera):
        self.camera = camera
        self.VideoUtils = VideoUtils(camera)

        # create a default object, no changes to I2C address or frequency
        self.mh = Adafruit_MotorHAT()
        atexit.register(self.__turn_off_motors)

        # Stepper motor 1
        self.sm_x = self.mh.getStepper(200, 1)      # 200 steps/rev, motor port #1
        self.sm_x.setSpeed(5)                       # 5 RPM
        self.current_x_steps = 0


        # Relay
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RELAY_PIN, GPIO.OUT)
        GPIO.output(RELAY_PIN, GPIO.LOW)


    def calibrate(self):
        """
        Waits for input to calibrate the turret's axis
        :return:
        """
        '''print( "Please calibrate the tilt of the gun so that it is level. Commands: (w) moves up, " \
              "(s) moves down. Press (enter) to finish.\n")
        #uncomment for y
        #self.__calibrate_y_axis()

        print( "Please calibrate the yaw of the gun so that it aligns with the camera. Commands: (a) moves left, " \
              "(d) moves right. Press (enter) to finish.\n")'''
        Turret.move_backward(self.sm_x, 5)

        '''print ("Calibration finished.")'''


    def motion_detection_rasp(self, frame):
        """
        Uses the camera to move the turret. OpenCV ust be configured to use this.
        :return:
        """
        self.VideoUtils.rasp_find_motion(frame, self.__move_axis)

    def __move_axis(self, contour, frame):
        (v_h, v_w) = frame.shape[:2]
        (x, y, w, h) = cv2.boundingRect(contour)

        # find height
        target_steps_x = (2*MAX_STEPS_X * (x + w / 2) / v_w) - MAX_STEPS_X

        print ("x: %s" % (str(target_steps_x)))
        print ("current x: %s" % (str(self.current_x_steps)))

        t_x = threading.Thread()

        # move x

        stprs_diff = int(target_steps_x - self.current_x_steps)
        print(stprs_diff)

        if (target_steps_x - self.current_x_steps) > 1:
            self.current_x_steps += stprs_diff
            t_x = threading.Thread(target=Turret.move_forward, args=(self.sm_x, stprs_diff+1,))
        elif (target_steps_x - self.current_x_steps) < -1:
            self.current_x_steps += stprs_diff
            t_x = threading.Thread(target=Turret.move_backward, args=(self.sm_x, -stprs_diff-1,))

        t_x.start()

        t_x.join()

    def interactive(self):
        """
        Starts an interactive session. Key presses determine movement.
        :return:
        """

        Turret.move_forward(self.sm_x, 1)

        print ('Commands: Pivot with (a) and (d). Tilt with (w) and (s). Exit with (q)\n')
        with raw_mode(sys.stdin):
            try:
                while True:
                    ch = sys.stdin.read(1)
                    if not ch or ch == "q":
                        break

                    if ch == "a":
                        if MOTOR_X_REVERSED:
                            Turret.move_backward(self.sm_x, 5)
                        else:
                            Turret.move_forward(self.sm_x, 5)
                    elif ch == "d":
                        if MOTOR_X_REVERSED:
                            Turret.move_forward(self.sm_x, 5)
                        else:
                            Turret.move_backward(self.sm_x, 5)
                    elif ch == "\n":
                        Turret.fire()

            except (KeyboardInterrupt, EOFError):
                pass


    @staticmethod
    def move_forward(motor, steps):
        """
        Moves the stepper motor forward the specified number of steps.
        :param motor:
        :param steps:
        :return:
        """
        motor.step(steps, Adafruit_MotorHAT.FORWARD,  Adafruit_MotorHAT.INTERLEAVE)
        return

    @staticmethod
    def move_backward(motor, steps):
        """
        Moves the stepper motor backward the specified number of steps
        :param motor:
        :param steps:
        :return:
        """
        motor.step(steps, Adafruit_MotorHAT.BACKWARD, Adafruit_MotorHAT.INTERLEAVE)
        return

    def __turn_off_motors(self):
        """
        Recommended for auto-disabling motors on shutdown!
        :return:
        """
        self.mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)
        return

#if __name__ == "__main__":
'''an example nopw'''

'''camera = picamera.PiCamera()
camera.resolution = (320, 240)
t = Turret(camera)
t.calibrate()
while(True):
    camera.capture(output,format='bgr')
    t.motion_detection_rasp(output)
'''

'''user_input = raw_input("Choose an input mode: (1) Motion Detection, (2) Interactive\n")

if user_input == "1":
    t.calibrate()
    if raw_input("Live video? (y, n)\n").lower() == "y":
        t.motion_detection(show_video=False)#change to true later mayb
    else:
        t.motion_detection()
elif user_input == "2":
    if raw_input("Live video? (y, n)\n").lower() == "y":
        _thread.start_new__thread(self.VideoUtils.live_video, ())
    t.interactive()
else:
    print ("Unknown input mode. Please choose a number (1) or (2)")
'''