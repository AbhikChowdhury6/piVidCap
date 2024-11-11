import os
import subprocess
import sys
from datetime import datetime
import tzlocal

deviceName = sys.argv[1] if len(sys.argv) > 0 else "notSet"


pathToCollectedData = "/home/" + os.getlogin() + "/Documents/collectedData/"
remotePathBase = "/home/uploadingGuest/recentCaptures/"

foldersInCollectedData = os.listdir(pathToCollectedData)
nameOfTodaysFolder = deviceName + "-" + datetime.now(tzlocal.get_localzone()).strftime("%Y-%m-%d%z")
for folderName in foldersInCollectedData:
    if folderName == nameOfTodaysFolder:
        continue
    source = pathToCollectedData + folderName
    remoteFolder = remotePathBase + folderName
    
    o = subprocess.run(["ssh uploadingGuest@192.168.1.242 mkdir -p", remoteFolder], capture_output=True)
    print(f"the returncode for making the direcotry was {o.returncode}")
    o = subprocess.run(["scp -r ", source, " uploadingGuest@192.168.1.242:", remoteFolder], capture_output=True)
    print(f"the returncode for uploading the direcotry was {o.returncode}")
    
    if o.returncode == 0:
        print(f"successfuly sent now deleting {source}")
        o = subprocess.run(["rm -r ", source], capture_output=True)
        print("deleted") if o.returncode == 0 else print(o)
    else:
        print(f"there was a problem sending {source} not deleting")
        print(o)
