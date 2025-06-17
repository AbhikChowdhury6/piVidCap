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
buffSecs = 10

capHz = 8


maxWidth = 1920
maxHeight = 1080

#can flip the image if set to 1
rotate = -1

# 1 is for 1920x1080 2MP
# 2 is for 960x540 .5MP
# 3 is for 640x360 .2MP
subSample = 2


#options for buffer saving
# frameMean-meanThresh just frame sum
# sqDiff-sqDiffMeanThresh squared pixel difference in buffSecs
# yolo-yolo11n.pt person detection
#capType = "frameMean-10"
capType = "sqDiff-15"
#capType = "yolo-yolo11x.pt"


#10 debug
#20 info
#30 warn
#40 error
#50 critical
# set this number and only messages with values above it will display
debugLvl = 20

allowed_loggers=["model_worker", "ctsb", "pi_vid_cap_worker", "writer_worker", "main"]
#allowed_loggers=[]
allowed_funcs=["getSqDiffresult", "append", "model_worker", "writeCtsbBufferNum", "writer_worker"]
#allowed_funcs = []

# values to make the old code work

# the biggest one: yolo11x.pt
# yolo11l.pt should halve the inference time
# yolo11s.pt is another big jump
# the smallest one: yolo11n.pt
modelName = "yolo11x.pt"

noRecThresh = 8