#process for setting up remote user
# as root
# useradd -m uploadingGuest
# passwd <strong password here>
# as uploadingGuest
# mkdir recentCaptures
# chmod 777 recentCaptures

#process for setting up local
# ssh-keygen -t rsa
# ssh-copy-id uploadingGuest@<remote ip>
# chrontab -e 
# add the line 0 3 * * * /home/$USER/Documents/videoProcessing/send.sh
# for logs check /var/log/syslog or /var/log/cron


import os
import subprocess
import sys
from datetime import datetime
import tzlocal
import logging
import logging.handlers

logger = logging.getLogger('home-video-uploader')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="/home/" + os.getlogin() + '/home-video-uploader.log')
formatter = logging.Formatter('%(asctime)s - %(name)s: %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

print(f"the time started is {datetime.now()}")
# logger.info(f"the time started is {datetime.now()}")

serverip = "192.168.1.113"

pathToCollectedData = "/home/" + os.getlogin() + "/Documents/collectedData/"

foldersInCollectedData = os.listdir(pathToCollectedData)
if len(foldersInCollectedData) == 0:
    print("no files found, exiting")
    logger.info("no files found, exiting")
    sys.exit()

# get device name
def getRepoPath():
    cwd = os.getcwd()
    delimiter = "\\" if "\\" in cwd else "/"
    repoPath = delimiter.join(cwd.split(delimiter)[:cwd.split(delimiter).index("piVidCap")]) + delimiter
    return repoPath
repoPath = getRepoPath()
sys.path.append(repoPath + "/piVidCap/")
if os.path.exists(repoPath + "/piVidCap/deviceInfo.py"):
    from deviceInfo import deviceInfo
else:
    from collections import OrderedDict
    keys = ["responsiblePartyName", "instanceName", "developingPartyName", "deviceName", "dataType", "dataSource"]
    values = ["abhik", "notSet", "abhik", "unknown", "mp4", "piVidCap"]
    deviceInfo = OrderedDict(zip(keys, values))

deviceName = "_".join(deviceInfo.keys())
if deviceInfo["instanceName"] == "notSet":
    print("no instance name set")
    sys.stdout.flush()


nameOfTodaysFolder = deviceName + "_" + datetime.now(tzlocal.get_localzone()).strftime("%Y-%m-%d%z")

startTime = datetime.now()
for folderName in foldersInCollectedData:
    #if you also want to send todays folder then add any argument when calling send
    if folderName == nameOfTodaysFolder and len(sys.argv) == 1:
        continue
    source = pathToCollectedData + folderName
    
    # send the folder over
    print(f"starting send of {folderName}")
    logger.info(f"starting send of {folderName}")
    o = subprocess.run(["scp", "-r", source, "uploadingGuest@" + serverip +
                         ":/home/uploadingGuest/recentCaptures/"],
                         capture_output=True)
    print(f"the returncode for uploading the direcotry was {o.returncode}")
    logger.info(f"the returncode for uploading the direcotry was {o.returncode}")
    
    # make it writeable by other users since the umask in the .bashrc isn't working for some reason
    o2 = subprocess.run(["ssh", "uploadingGuest@"  + serverip, "chmod", "-R", "777", 
                        "/home/uploadingGuest/recentCaptures/" + folderName + "/"], 
                        capture_output=True)
    print(f"the returncode for upating the permissions was {o2.returncode}")
    logger.info(f"the returncode for upating the permissions was {o2.returncode}")

    #delete the folder locally if the send was successful
    if o.returncode == 0:
        print(f"successfuly sent now deleting {source}")
        logger.info(f"successfuly sent now deleting {source}")
        o = subprocess.run(["rm", "-r", source], capture_output=True)
        print("deleted") if o.returncode == 0 else print(o)
        logger.info("deleted") if o.returncode == 0 else logger.info(o)
    else:
        print(f"there was a problem sending {source} not deleting")
        logger.error(f"there was a problem sending {source} not deleting")
        print(o)
        logger.error(o)

print(f"done sending in {datetime.now() - startTime}!")
logger.info(f"done sending in {datetime.now() - startTime}!")
print(f"the time completed is {datetime.now()}")
# logger.info(f"the time completed is {datetime.now()}")
