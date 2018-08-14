'''
Requirements:
In workon cv envirnment write the following
pip3 install pyrebase
pip3 install pyfcm
pip3 install requests
pip3 install python-firebase
'''

from firebase import firebase
import json
from pyfcm import FCMNotification
import pyrebase
import time

class firebase_server():
    def __init__(self):

        config = {
            "apiKey": "AAAAXDKjDeY:APA91bHLONjob43L-tynyMAicqee38C9yuAo6rZFdlc25zmCmmnqyrcyG7NIugNLECKIU2q4QpyNPTzN0NsJHTm8SyiuzJOxzL5JPmHwIoJO7LrYDboUJU0-115EXKWpK8vLVJor1-Pi",
            "authDomain": "homeattender.firebaseapp.com",
            "databaseURL": "https://homeattender.firebaseio.com/",
            "storageBucket": "homeattender.appspot.com"
        }
        #base firebase setup
        self.firebase = firebase.FirebaseApplication('https://homeattender.firebaseio.com/', None)
        self.push_service = FCMNotification(api_key=config["apiKey"])
        self.registration_id = "cp5OKaH4C_Y:APA91bEtcHMcJINecS8SpGYMckeO_Jj9HYwyrQXs4jGBObxgrT8yGCYmdh0JHVE4VP0Q0MmlGxH-OOC6ixT9pFNkqfivOke-nTXanJnhbyVkVBK28bT7KMhSH_Mun3SuWRj14xH58e0V3ZAJLpsFFds8BwFjbyXbnQ"
        self.calibration_pass = 0
        #picture pyrebase setup to send from rasp to phone
        self.pyrebase = pyrebase.initialize_app(config)
        self.storage = self.pyrebase.storage()

    '''
    ----------------------------------------GENERAL FUNCTIONS-------------------------------------------------------------
    '''
    def patch(self, grouping, state):
        '''
        :param grouping: String of the name the grouping you want to patch
        :param state:
        :return:
        '''
        self.firebase.patch('/', {grouping: state})

    def get(self, grouping):
        '''
        :param grouping: String of the name the grouping you want to patch
        :return: state of grouping
        '''
        self.firebase.get('/{}'.format(grouping), None)

    def send_notification(self, title, msg):
        self.push_service.notify_single_device(registration_id=self.registration_id, message_title=title,
                                               message_body=msg)

    def upload_picture(self, src, name):
        '''
        :param src: source path + name of picture
        :param name: name of picture to appear in database
        :return:
        '''
        self.storage.child(name).put(src)

    def download_picture(self, name, dst):
        '''
        :param name: picture in database
        :param dst: full destination of picture including name
        :return:
        '''
        self.storage.child(name).download(dst)

    '''
    -------------------------------------------------------------END----------------------------------------------------
    '''
    def send_alarm_picture(self, msg, src):
        '''
        :param msg: message for the app to view ex: is it a fire or is it an intruder time stamped
        :param src: full name of picture to send
        :return: returns the name of the alarm picture
        '''
        picture_name = "{}.png".format(time.strftime("%Y%m%d-%H%M%S"))
        self.upload_picture(src, picture_name)
        self.firebase.patch('/LastAlarm', {'Info': msg, 'PicName': picture_name})
        return picture_name

    def get_intruder(self):
        return self.firebase.get('/Alert', None)

    def alert_intruder(self):
        message_title = "INTRUDER"
        message_body = "INTRUDER HAS BEEN DETECTED"
        self.firebase.patch('/', {'Alert': 'off'})

        self.push_service.notify_single_device(registration_id=self.registration_id, message_title=message_title,
                                                   message_body=message_body)

    def get_alert(self):
        return self.firebase.get('/Alert', None)

    def alert_off(self):
        self.firebase.patch('/', {'Alert': 'off'})

    def get_calibration(self):
        return not(self.firebase.get('/Calibration', None))

    def calibration_done(self):
        self.firebase.patch('/', {'Calibration': True})
        self.send_notification('Calibration Done', 'Owner has been inputted into system')
        self.calibration_pass = 0

    def get_owner(self):
        return self.firebase.get('/Owner', None)

    def owner_off(self):
        self.firebase.patch('/', {'Owner': False})


    def send_fire_alarm(self, src, msg):
        #PUSH
        picture_name = "fire{}.png".format(time.strftime("%Y%m%d-%H%M%S"))
        self.upload_picture(src, picture_name)
        self.firebase.patch('/FireAlarm', {'Info': msg, 'PicName': picture_name})
        #NOTIFICATION
        message_title = "FIRE"
        message_body = "FIRE HAS BEEN DETECTED"
        self.firebase.patch('/', {'Fire': 'off'})
        self.push_service.notify_single_device(registration_id=self.registration_id, message_title=message_title,
                                                       message_body=message_body)

    def get_fire(self):
        return self.firebase.get('/Fire', None)
