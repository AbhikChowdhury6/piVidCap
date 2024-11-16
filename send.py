#process for setting up remote user
# as root
# useradd -m uploadingGuest
# passwd <strong password here>

#process for setting up local
# ssh-keygen -t rsa
# ssh-copy-id uploadingGuest@<remote ip>

import os
import subprocess
import sys
from datetime import datetime
import tzlocal

if len(sys.argv) > 1:
    deviceName = sys.argv[1]
else: 
    deviceName = "notSet"

serverip = "192.168.1.113"

pathToCollectedData = "/home/" + os.getlogin() + "/Documents/collectedData/"

foldersInCollectedData = os.listdir(pathToCollectedData)
nameOfTodaysFolder = deviceName + "-" + datetime.now(tzlocal.get_localzone()).strftime("%Y-%m-%d%z")
startTime = datetime.now()
for folderName in foldersInCollectedData:
    if folderName == nameOfTodaysFolder:
        continue
    source = pathToCollectedData + folderName
    
    # send the folder over
    print("starting send")
    o = subprocess.run(["scp", "-r", source, "uploadingGuest@" + serverip +
                         ":/home/uploadingGuest/recentCaptures/"],
                         capture_output=True)
    print(f"the returncode for uploading the direcotry was {o.returncode}")
    
    # make it writeable by other users since the umask in the .bashrc isn't working for some reason
    o2 = subprocess.run(["ssh", "uploadingGuest@"  + serveri, "chmod", "-R", "777", 
                        "/home/uploadingGuest/recentCaptures/" + folderName + "/"], 
                        capture_output=True)
    print(f"the returncode for upating the permissions was {o2.returncode}")

    #delete the folder locally if the send was successful
    if o.returncode == 0:
        print(f"successfuly sent now deleting {source}")
        o = subprocess.run(["rm", "-r", source], capture_output=True)
        print("deleted") if o.returncode == 0 else print(o)
    else:
        print(f"there was a problem sending {source} not deleting")
        print(o)

print(f"done sending in {datetime.now() - startTime}!")
print(f"the time is {datetime.now()}")