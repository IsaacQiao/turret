# This is a demo of running face recognition on a Raspberry Pi.
# This program will print out the names of anyone it recognizes to the console.

# To run this, you need a Raspberry Pi 2 (or greater) with face_recognition and
# the picamera[array] module installed.
# You can follow this installation instructions to get your RPi set up:
# https://gist.github.com/ageitgey/1ac8dbe8572f3f533df6269dab35df65

import picamera
import time
from _thread import *
from turret import *
import threading
import numpy as np
import cv2
import subprocess
import logging
import os
from firebase_server import *


FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(filename='log.log',format=FORMAT)
logger = logging.getLogger(__name__)
file_location = "/home/pi/face_recognition/test/"
ref_location = "/home/pi/face_recognition/ref/"
intruder_location = "/home/pi/face_recognition/Intruder/"
fire_location = "/home/pi/LeptonModule/"
def face_detection_sec(img, firebase, faceCascade, logger):
    #face_locations = face_recognition.face_locations(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    number_face = len(faces)
    msg2 = "Found {} faces in image.".format(number_face)
    #print(msg2)
    #checks if there are faces found
    #also checks if its in either in alert mode or not
    #or in calibration mode
    if number_face > 0 and (firebase.get_alert() == 'on' or firebase.get_calibration()):

        for (x, y, w, h) in faces:
            file_name = file_location + "test_{}.jpg".format(x)
            cv2.imwrite(file_name, img[y:(h+y), x:(w+x)])
        return_Val = subprocess.call("/home/pi/face_recognition/facial_rec > facial.log", shell=True)
        print(return_Val)
        #checks if start of calibration mode
        if firebase.get_calibration() and firebase.calibration_pass == 0:
            print('Calibration Start')
            for (x, y, w, h) in faces:
                file_name = ref_location + "owner{}_{}.jpg".format(w,time.time())
                cv2.imwrite(file_name, img[y:(h + y), x:(w + x)])
            firebase.calibration_pass += 1
            return

        if return_Val == 0:
            print('owner')
            #if in calibration mode check if it passed 3x and if so it is done calibration
            if firebase.get_calibration():
                firebase.calibration_pass += 1
                if firebase.calibration_pass >= 4:
                    firebase.calibration_done()
                    print('Calibration Done')
            #creates new picture with owner's face
            for (x, y, w, h) in faces:
                file_name = ref_location + "owner{}_{}.jpg".format(w,time.time())
                cv2.imwrite(file_name, img[y:(h + y), x:(w + x)])
        elif return_Val == 255:
            print("intruder");
            #if in calibration mode then don't need to alert
            if not(firebase.get_calibration()):
                #turn off alarm intruder found
                firebase.alert_off()
                #create image of intruder
                file_name = intruder_location + "{}.jpg".format(time.time())
                cv2.imwrite(file_name, img)
                #send image of intruder
                msg = "Intruder {}".format(time.strftime("%H:%M:%S"))
                result = firebase.send_alarm_picture(msg, file_name)
                print(result)
                #send notification
                firebase.alert_intruder()
        elif return_Val == 254:
            #no ref or test image
            return;
    else:
        folder = file_location
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                # elif os.path.isdir(file_path): shutil.rmtree(file_path)
            except Exception as e:
                print(e)

def fire_check(firebase,temp):
    folder = fire_location
    if(firebase.get_fire() == False):
            for the_file in os.listdir(folder):
                if(the_file=="fire.jpg"):
                    file_path = os.path.join(folder, the_file)
                    os.unlink(file_path)
    else:
        folder = file_location
        file_path = os.path.join(folder, "fire.jpg")
        if os.path.isfile(file_path):
            #new fire img
            msg = "Fire Detected {}".format(time.strftime("%Y/%m/%d at %H:%M:%S"))
            firebase.send_fire_alarm(file_path, msg)
            os.unlink(file_path)

# Get a reference to the Raspberry Pi camera.
# If this fails, make sure you have a camera connected to the RPi and that you
# enabled your camera in raspi-config and rebooted first.
camera = picamera.PiCamera()
camera.resolution = (320, 240)
output = np.empty((240, 320, 3), dtype=np.uint8)
t = Turret(camera)
t.calibrate()

# Load a sample picture and learn how to recognize it.

# Initialize some variables
face_locations = []

firebase = firebase_server()
result = firebase.get_calibration()
print(result)

#face detection
cascPath = "/home/pi/face_recognition/haarcascade_frontalface_default.xml"
# Create the haar cascade
faceCascade = cv2.CascadeClassifier(cascPath)
count_turrent = 0
while True:
    camera.capture(output, format='bgr')
    count_turrent = count_turrent+1


    # Find all the faces and face encodings in the current frame of video
    '''Thread for facial recongition'''
    #face_thread = threading.Thread(target=face_detection_sec, args=(output, firebase, faceCascade, logger))
    fire_thread = threading.Thread(target=fire_check, args=(firebase,"temp string"))

    fire_thread.start()
    #face_thread.start()
    # if count_turrent>1:
    #     count_turrent=0
        #turret_thread = threading.Thread(target=t.motion_detection_rasp, args=(output,))
        #turret_thread.start()

    #face_thread.join()
    #turret_thread.join()
    #start_new_thread(face_detection_sec,(output, firebase, faceCascade, logger,))#not used
    '''thread for moving platform'''
    #turret_thread = threading.Thread(target=t.motion_detection_rasp, args=(output,False))
    #turret_thread.start()