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


import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
import tzlocal
import logging
import logging.handlers

parser = argparse.ArgumentParser()
parser.add_argument("--include-today", action="store_true", help=(
    "Also send today's folder, safely: only already-completed segments "
    "(the in-progress new.mp4/new.parquet.gzip pair is always skipped), "
    "sent and deleted from the Pi one file at a time as each is confirmed "
    "uploaded. Never touches the folder itself or the currently-open file, "
    "so it's safe to run anytime, including while capture is active."
))
args = parser.parse_args()

logger = logging.getLogger('home-video-uploader')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="/home/" + os.getlogin() + '/home-video-uploader.log')
formatter = logging.Formatter('%(asctime)s - %(name)s: %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

print(f"the time started is {datetime.now()}")
# logger.info(f"the time started is {datetime.now()}")

serverip = "192.168.20.64"

pathToCollectedData = "/home/" + os.getlogin() + "/Documents/collectedData/"

foldersInCollectedData = os.listdir(pathToCollectedData)
if len(foldersInCollectedData) == 0:
    print("no files found, exiting")
    logger.info("no files found, exiting")
    sys.exit()

# get device name
repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import deviceInfo
else:
    from collections import OrderedDict
    keys = ["responsiblePartyName", "instanceName", "developingPartyName", "deviceName", "dataType", "dataSource"]
    values = ["abhik", "notSet", "abhik", "unknown", "mp4", "piVidCap"]
    deviceInfo = OrderedDict(zip(keys, values))

deviceName = "_".join(deviceInfo.values())
if deviceInfo["instanceName"] == "notSet":
    print("no instance name set")
    sys.stdout.flush()


nameOfTodaysFolder = deviceName + "_" + datetime.now(timezone.utc).strftime("%Y-%m-%d%z")


def send_completed_folder(folderName, source):
    """Send a folder that capture has fully finished with, then delete it locally on success."""
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


def send_todays_completed_files(folderName, source):
    """Send only today's already-rotated segments, one file at a time.

    Skips the new.mp4/new.parquet.gzip pair the writer currently has open,
    and only deletes a source file once its own upload is confirmed -- the
    folder itself is never touched, so this is safe to run while capture is
    still active in it (unlike force-sending the whole folder).
    """
    entries = sorted(f for f in os.listdir(source)
                      if not f.startswith("new.") and os.path.isfile(os.path.join(source, f)))
    if not entries:
        print(f"no completed segments in {folderName} yet, nothing to send")
        logger.info(f"no completed segments in {folderName} yet, nothing to send")
        return

    print(f"starting partial send of {folderName} ({len(entries)} completed files)")
    logger.info(f"starting partial send of {folderName} ({len(entries)} completed files)")
    remoteDir = "/home/uploadingGuest/recentCaptures/" + folderName + "/"
    o = subprocess.run(["ssh", "uploadingGuest@" + serverip, "mkdir", "-p", remoteDir],
                        capture_output=True)
    if o.returncode != 0:
        print(f"could not create {remoteDir} on the server, aborting partial send")
        logger.error(f"could not create {remoteDir} on the server: {o}")
        return

    for fileName in entries:
        filePath = os.path.join(source, fileName)
        o = subprocess.run(["scp", filePath, "uploadingGuest@" + serverip + ":" + remoteDir],
                            capture_output=True)
        if o.returncode == 0:
            os.remove(filePath)
            print(f"  sent + removed {fileName}")
            logger.info(f"  sent + removed {fileName}")
        else:
            print(f"  problem sending {fileName}, not deleting")
            logger.error(f"  problem sending {fileName}: {o}")

    o2 = subprocess.run(["ssh", "uploadingGuest@" + serverip, "chmod", "-R", "777", remoteDir],
                        capture_output=True)
    print(f"the returncode for upating the permissions was {o2.returncode}")
    logger.info(f"the returncode for upating the permissions was {o2.returncode}")


startTime = datetime.now()
for folderName in foldersInCollectedData:
    source = pathToCollectedData + folderName
    if folderName == nameOfTodaysFolder:
        if args.include_today:
            send_todays_completed_files(folderName, source)
        continue
    send_completed_folder(folderName, source)

print(f"done sending in {datetime.now() - startTime}!")
logger.info(f"done sending in {datetime.now() - startTime}!")
print(f"the time completed is {datetime.now()}")
# logger.info(f"the time completed is {datetime.now()}")
