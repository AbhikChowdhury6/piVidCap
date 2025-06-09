from collections import OrderedDict

# rename this file to deviceInfo.py after pulling
keys = ["responsiblePartyName", "instanceName", "developingPartyName", "deviceName", "dataType", "dataSource"]
values = ["abhik", "notSet", "abhik", "unknown", "mp4", "piVidCap"]

#values = ["abhik", "mobilepi", "abhik", "piCam-raspberryPi5-Camv3120noir", "mp4", "piVidCap"]
#values = ["abhik", "bedroompi", "abhik", "piCam-raspberryPi5-Camv3120", "mp4", "piVidCap"]
#values = ["abhik", "bathroompi", "abhik", "piCam-raspberryPi5-Camv3noir", "mp4", "piVidCap"]
#values = ["abhik", "kitchenpi", "abhik", "piCam-raspberryPi5-Camv3120noir", "mp4", "piVidCap"]
#values = ["abhik", "testpi", "abhik", "piCam-raspberryPi5-Camv3120noir", "mp4", "piVidCap"]
#values = ["abhik", "testpi4b", "abhik", "piCam-raspberryPi4-wideAnglenoir", "mp4", "piVidCap"]

deviceInfo = OrderedDict(zip(keys, values))

#make this a divisor of the number of seconds in a minute
buffSecs = 5

capHz = 8

#maxWidth = 1296
#maxHeight = 972
maxWidth = 1920
maxHeight = 1080

rotate = -1

# 1 is for 1920x1080 2MP
# 2 is for 960x540 .5MP
# 3 is for 640x360 .2MP
subSample = 1

#TODO
#options for buffer saving
# frameSum-sum just frame sum
# diff-thresh motion between 5 seconds
# yolo-yolo11n.pt person detection
capType = "yolo-yolo11x.pt"

# the biggest one: yolo11x.pt
# yolo11l.pt should halve the inference time
# yolo11s.pt is another big jump
# the smallest one: yolo11n.pt
#modelName = "yolo11x.pt"

#1 debug
#2 info
#3 warn
#4 error
#5 critical
debugLvl = 1

noRecThresh = 8