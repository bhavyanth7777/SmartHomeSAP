import tornado.web
import tornado.httpserver
import tornado.options
import tornado.ioloop
import tornado.websocket
import tornado.httpclient
from tornado import gen
import os.path
import os
import json
import requests
import time
import datetime
import psycopg2
import uuid
import smtplib
import hashlib
import base64
import random
import string
import pyhdb
from twilio.rest import TwilioRestClient

account_sid = "ACb2e73fe6a36429265bbd587a74ae9bb7" # Your Account SID from www.twilio.com/console
auth_token  = "5ee6ef76aeae2121ee06a3d6a90a330e"  # Your Auth Token from www.twilio.com/console
client = TwilioRestClient(account_sid, auth_token)

# defined constants
count = 1560000001
heartCount = 1570000001
caregiver_count = 1005
lightCount = 1
FLAG = {"status":"ON"}
previousTime = datetime.datetime.now()
thresholdHeartRate = {"thresholdHeartRateMax":100,"thresholdHeartRateMin":30}

connection = pyhdb.connect(host="52.74.212.84",port=30015, user="SYSTEM", password="Welcome1")
cursor = connection.cursor()

from tornado.options import define, options, parse_command_line
define('port',default=8000,type=int)

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Working!")

class LightsOnHandler(tornado.web.RequestHandler):
    def get(self):
        # write the lights.json file to {"light":"on"}
        # global previousTime
        hitTime = datetime.datetime.now()
        tDelta = hitTime - previousTime
        tDelta = divmod(tDelta.days * 86400 + tDelta.seconds, 60)
        tDelta = tDelta[1]
        print("tdelta ",tDelta)

        if tDelta>5:
            global lightCount
            lightCount+=1
            print("lightCount ",lightCount)
        else:
            pass

        if lightCount%2 == 0:
            # global previousTime
            previousTime = datetime.datetime.now()
            with open('light.json', 'w') as outfile:
                json.dump({"light":"on"}, outfile)
                print("light on")
            # global count
            count = count+1
            cursor.execute("INSERT INTO SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA VALUES(%s,'BHAVYANTH','MOTION_ON',7,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'MOTION')"%count)
            connection.commit()

        elif lightCount%2 !=0:
            with open('light.json', 'w') as outfile:
                json.dump({"light":"off"}, outfile)
                print("light off")
            # global count
            count = count+1
            cursor.execute("INSERT INTO SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA VALUES(%s,'BHAVYANTH','MOTION_OFF',7,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'MOTION')"%count)
            connection.commit()



class LightsOffHandler(tornado.web.RequestHandler):
    def get(self):
        global count
        count = count+1

        cursor.execute("INSERT INTO SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA VALUES(%s,'BHAVYANTH','OFF',7,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'MOTION')"%count)
        connection.commit()

class HardOffHandler(tornado.web.RequestHandler):
    def get(self):
        with open('light.json', 'w') as outfile:
            json.dump({"light":"off"}, outfile)

class HardOnHandler(tornado.web.RequestHandler):
    def get(self):
        with open('light.json', 'w') as outfile:
            json.dump({"light":"on"}, outfile)

# class DashBoardHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.render("activeTab.html")
#
# class ThresholdHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.render("alertThreshold.html")
#
# class CaregiverInfoHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.render("homePage.html")
#

class HeartBeatHandler(tornado.web.RequestHandler):
    def get(self,rate):
        print(rate)
        global heartCount
        heartCount+=1
        cursor.execute("INSERT INTO SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA VALUES(%s,'BHAVYANTH',%s,7,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'HEART')"%(heartCount,str(rate)))
        connection.commit()



class WSHandler(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        print("connection opened")

    def on_message(self, message):
        messageReceived = json.loads(message)
        messageLabel = messageReceived['messageLabel']

        if messageLabel == "currentStatus":

            # get the latest record from the table
            cursor.execute("SELECT TOP 1 SENSOR_STATUS FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA ORDER BY SENSOR_RECORD_CREATED DESC")
            sensor_status = cursor.fetchone()[0]

            self.write_message(json.dumps({"messageLabel":"currentStatus","sensor_status":sensor_status}))


        elif messageLabel == "Active":

            # get the last Active record
            try:

                cursor.execute("SELECT TOP 1 SENSOR_RECORD_CREATED FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_STATUS='MOTION_ON'ORDER BY SENSOR_RECORD_CREATED DESC")
                lastActiveTimeStamp = cursor.fetchone()[0]
                lastActiveTimeStampConverted = lastActiveTimeStamp.strftime("%m/%d/%Y %H:%M:%S")

                cursor.execute("SELECT TOP 1 SENSOR_RECORD_CREATED FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_STATUS='MOTION_ON'ORDER BY SENSOR_RECORD_CREATED DESC")
                latestOn = cursor.fetchone()[0]

                cursor.execute("SELECT TOP 1 SENSOR_RECORD_CREATED FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_STATUS='MOTION_OFF'ORDER BY SENSOR_RECORD_CREATED DESC")
                latestOff = cursor.fetchone()[0]

                timeDelta = abs(latestOff - latestOn)
                timeDelta = divmod(timeDelta.days * 86400 + timeDelta.seconds, 60)
                minutes = timeDelta[0]
                seconds = timeDelta[1]


                self.write_message(json.dumps({"messageLabel":"Active","lastActiveTimeStampConverted":lastActiveTimeStampConverted,"minutes":minutes,"seconds":seconds}))
            except Exception as e:
                print("In except handler Active",e)
                self.write_message(json.dumps({"messageLabel":"Active","lastActiveTimeStampConverted":"N/A","minutes":"N/A","seconds":"N/A"}))

        elif messageLabel == "motionGraphData":
            # get time stamp and corresponding on values. {"value":"on","timestamp":"timestampFromServer"}
            # day,week,year
            try:
                cursor.execute("SELECT TOP 100 SENSOR_STATUS FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_TYPE='MOTION' ORDER BY SENSOR_RECORD_CREATED DESC")#TODO: Order by timestamp 8am to 8pm
                listOfData = cursor.fetchall()
                motionDataFromServer = []
                for i in listOfData:
                    if i[0] == "OFF":
                        motionDataFromServer.append(0)
                    elif i[0] == "ON":
                        motionDataFromServer.append(1)
                self.write_message({"messageLabel":"motionGraphData","motionDataFromServer":motionDataFromServer})
            except Exception as e:
                print("In except handler motionGraphData",e)



        elif messageLabel == "thresholdHeartRate":
            # get values of minimum and maximum heart rate from html
            print("thresholdHeartRate")
            global thresholdHeartRate
            thresholdHeartRate['thresholdHeartRateMax'] = messageReceived['thresholdHeartRateMax']
            thresholdHeartRate['thresholdHeartRateMin'] = messageReceived['thresholdHeartRateMin']
            print(thresholdHeartRate)

        elif messageLabel == "Pulse":
            print("In pulse")

            try:
                cursor.execute("SELECT AVG(TO_INT(SENSOR_STATUS)) FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_TYPE='HEART'") #TODO: and date= today's date
                averageHeartRate = cursor.fetchone()[0]
                averageHeartRate = round(float(averageHeartRate))
                print("averageHeartRate",averageHeartRate)
            except Exception as e:
                print("2",e)

            try:
                cursor.execute("SELECT MAX(TO_INT(SENSOR_STATUS)) FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_TYPE='HEART'") #TODO: and date = today's date
                max_HeartRate = cursor.fetchone()[0]
                if max_HeartRate > 140:
                    max_HeartRate = 139

                cursor.execute("SELECT MIN(TO_INT(SENSOR_STATUS)) FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_TYPE='HEART'") #TODO: and date = today's date
                min_HeartRate = cursor.fetchone()[0]
                print("min_HeartRate",min_HeartRate)
            except Exception as e:
                print("3",e)

            self.write_message(json.dumps({"messageLabel":"Pulse","averageHeartRate":averageHeartRate,"max_heart_rate":max_HeartRate,"min_heart_rate":min_HeartRate}))
            # except Exception as e:
            #     print("In except Handler Pulse",e)
            #     self.write_message(json.dumps({"messageLabel":"Pulse","latestHeartRate":"N/A","averageHeartRate":"N/A","max_heart_rate":"N/A","min_heart_rate":"N/A"}))

        elif messageLabel == "currentPulse":
            try:
                cursor.execute("SELECT TOP 1 SENSOR_STATUS,SENSOR_RECORD_CREATED FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_TYPE='HEART' ORDER BY SENSOR_RECORD_CREATED DESC")
                heartData = cursor.fetchone()
                latestHeartRate = int(heartData[0])
                if latestHeartRate > 140:
                    latestHeartRate = 139
                print("latestHeartRate",latestHeartRate)
                self.write_message(json.dumps({"messageLabel":"currentPulse","latestHeartRate":latestHeartRate}))
            except Exception as e:
                print("1",e)

        elif messageLabel == "heartGraphData":
            # {"heartValue":"72","timestamp":"timestampFromServer"}
            # day, week, year
            try:
                cursor.execute("SELECT TOP 100 SENSOR_STATUS FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_TYPE='HEART' ORDER BY SENSOR_RECORD_CREATED DESC")
                listOfHeartData = cursor.fetchall()
                heartDataFromServer = []
                for i in listOfHeartData:
                    heartDataFromServer.append(int(i[0]))
                self.write_message({"messageLabel":"heartGraphData","heartDataFromServer":heartDataFromServer})
            except Exception as e:
                print("In except handler heartGraphData",e)


        elif messageLabel == "heartBeatAlerts":
            print("heartBeatAlerts")
            thresholdHeartRateMin = thresholdHeartRate['thresholdHeartRateMin'] # get it from the dashboard
            thresholdHeartRateMax = thresholdHeartRate['thresholdHeartRateMax']
            print(thresholdHeartRate)
            # message = client.messages.create(body="Heart Beat Spike! Please check the patient",to="+91%s"%caregiverPhoneNumber,from_="+1855-851-3299") # Replace with your Twilio number
            # print(message.sid)

            try:
                cursor.execute("SELECT TOP 1 CAREGIVER_MOBILE FROM SAP_STARTUP_SMARTHOME.SMARTHOME_CAREGIVER_INFO ORDER BY CAREGIVER_ID DESC")
                caregiverPhoneNumber = cursor.fetchone()[0]
                print(caregiverPhoneNumber)
            except Exception as e:
                print("In except handler heartBeatAlerts-2",e)

            try:
                cursor.execute("SELECT TOP 1 SENSOR_RECORD_CREATED,SENSOR_STATUS FROM SAP_STARTUP_SMARTHOME.SMARTHOME_USER_SENSOR_DATA WHERE SENSOR_TYPE='HEART' ORDER BY SENSOR_RECORD_CREATED DESC")
                heartData = cursor.fetchone()
                datetimeNow = datetime.datetime.now()
                latestHeartRateTimeStamp = heartData[0]
                latestHeartRate = heartData[1]
                print("latestHeartRate",latestHeartRate)
                td = datetimeNow - latestHeartRateTimeStamp
                tDelta = divmod(td.days * 86400 + td.seconds, 60)
                tDelta = tDelta[0]

                if tDelta > 10 and FLAG['status'] == "ON": #TODO: add variable
                    print(FLAG)
                    # message = client.messages.create(body="Heart Beat Sensor Might have failed! Please check the sensor",to="+91%s"%caregiverPhoneNumber,from_="+1855-851-3299") # Replace with your Twilio number
                    # print(message.sid)
                else:
                    pass

                if (int(latestHeartRate) > thresholdHeartRateMax) and FLAG['status'] == "ON":
                    # message = client.messages.create(body="Heart Beat Spike! Please check the patient",to="+91%s"%caregiverPhoneNumber,from_="+1855-851-3299") # Replace with your Twilio number
                    # print(message.sid)
                    print("spike")
                elif (int(latestHeartRate) < thresholdHeartRateMin) and FLAG['status'] == "ON":
                    # message = client.messages.create(body="Heart Beat Low! Please check the patient",to="+91%s"%caregiverPhoneNumber,from_="+1855-851-3299") # Replace with your Twilio number
                    # print(message.sid)
                    print("dip")
            except Exception as e:
                print("In except handler heartBeatAlerts-1",e)



        elif messageLabel == "caregiver_details":
            print("caregiver_details")
            caregiver_name_value = messageReceived['caregiver_name']
            caregiver_phone = str(messageReceived['caregiver_phone'])
            caregiver_relation = messageReceived['caregiver_relation']
            global caregiver_count
            caregiver_count = str(caregiver_count+1)
            cursor.execute("INSERT INTO SAP_STARTUP_SMARTHOME.SMARTHOME_CAREGIVER_INFO VALUES("+caregiver_count+",'"+caregiver_name_value+"','"+caregiver_phone+"','"+caregiver_relation+"',1,CURRENT_TIMESTAMP,1)")
            connection.commit()

        elif messageLabel == "currentDatetime":
            current_time = datetime.datetime.now()
            current_time = current_time.strftime("%m/%d/%Y %H:%M:%S")
            self.write_message(json.dumps({"messageLabel":"currentDatetime","current_time":current_time}))


        elif messageLabel == "Sleep":
            #TODO: get the data from 9pm to 8am where there is no motion = total sleep
            #TODO: get the first record time stamp in the above time = Slept at
            #TODO: from 9pm to 8 am get the time from last motion to next motion from which there is no motion = Time taken to Sleep
            #TODO: from 9pm to 8 am get the number of times "MOTION_ON" has been captured = Awakened times
            #TODO: from 9pm to 8 am, total sleep - (Awakened Times * 10 minutes + Time taken to sleep)
            #TODO: from 9pm to 8 am, number of times the sensor_id of bathroom has detected motion
            pass

        elif messageLabel == "FLAG_SET":
            flag_value = messageReceived['flag_value']
            if flag_value == "ON":
                FLAG['status'] = "ON"
            elif flag_value == "OFF":
                FLAG['status'] = "OFF"
            print(FLAG)






            # 2. Total Active: get the time stamps of all the on queries and add up.
    def on_close(self):
        print("Connection closed")



handlers = [
    (r'/',IndexHandler),
    (r'/on',LightsOnHandler),
    (r'/off',LightsOffHandler),
    (r'/hardoff',HardOffHandler),
    (r'/hardon',HardOnHandler),
    (r'/heart/([^/]+)',HeartBeatHandler),
    (r'/ws',WSHandler),
    (r"/(.*)", tornado.web.StaticFileHandler, {"path": os.path.dirname(os.path.realpath("light.json"))}),
]

if __name__ == "__main__":
    parse_command_line()
    # template path should be given here only unlike handlers
    app = tornado.web.Application(handlers, template_path=os.path.join(os.path.dirname(__file__), "templates"),
                                  static_path=os.path.join(os.path.dirname(__file__), "static"),cookie_secret="61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=", debug=True)
    http_server = tornado.httpserver.HTTPServer(app)
    options.port = 8000
    http_server.listen(options.port)
    print("Live at %s"%options.port)
    loop = tornado.ioloop.IOLoop.instance()
    loop.start()
