from collections import OrderedDict

# rename this file to deviceInfo.py after pulling
keys = ["responsiblePartyName", "instanceName", "developingPartyName", "deviceName", "dataType", "dataSource"]
#values = ["abhik", "mobilepi", "abhik", "piCam-raspberryPi5-Camv3120noir", "mp4", "piVidCap"]
#values = ["abhik", "bedroompi", "abhik", "piCam-raspberryPi5-Camv3120", "mp4", "piVidCap"]
#values = ["abhik", "bathroompi", "abhik", "piCam-raspberryPi5-Camv3noir", "mp4", "piVidCap"]
#values = ["abhik", "kitchenpi", "abhik", "piCam-raspberryPi5-Camv3120noir", "mp4", "piVidCap"]
#values = ["abhik", "testpi", "abhik", "piCam-raspberryPi5-Camv3120noir", "mp4", "piVidCap"]
#values = ["abhik", "testpi4b", "abhik", "piCam-raspberryPi4-wideAnglenoir", "mp4", "piVidCap"]

values = ["abhik", "notSet", "abhik", "unknown", "mp4", "piVidCap"]
deviceInfo = OrderedDict(zip(keys, values))

# 1 is for 1920x1080 2MP
# 2 is for 960x540 .5MP
# 3 is for 640x360 .2MP
subSample = 1

# the biggest one: yolo11x.pt
# yolo11l.pt should halve the inference time
# yolo11s.pt is another big jump
# the smallest one: yolo11n.pt
modelName = "yolo11x.pt"


noRecThresh = 8