from collections import OrderedDict

# rename this file to deviceInfo.py after pulling
keys = ["responsiblePartyName", "instanceName", "developingPartyName", "deviceName", "dataType", "dataSource"]
#values = ["abhik", "mobilepi", "abhik", "piCam-raspberryPi5-Camv3120noir", "mp4", "piVidCap"]
#values = ["abhik", "bedroompi", "abhik", "piCam-raspberryPi5-Camv3120", "mp4", "piVidCap"]
#values = ["abhik", "bathroompi", "abhik", "piCam-raspberryPi5-Camv3noir", "mp4", "piVidCap"]
#values = ["abhik", "kitchenpi", "abhik", "piCam-raspberryPi5-Camv3120noir", "mp4", "piVidCap"]
values = ["abhik", "notSet", "abhik", "unknown", "mp4", "piVidCap"]
deviceInfo = OrderedDict(zip(keys, values))