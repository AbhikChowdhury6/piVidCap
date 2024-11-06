#!/bin/bash

# first manually clone repo

#in this script

echo "enter the device name"
read DEVICE_NAME
echo "enter the local username"
read LOCAL_USERNAME
echo "enter the remote username"
read REMOTE_USERNAME
echo "enter the remote host name"
read REMOTE_HOSTNAME
echo "enter enter the remote password"
read REMOTE_PASSWORD

#install video capture dependencies
# make and activate a virtual enviroment
python -m venv ~/vision
source ~/vision/bin/activate

pip install ultralytics[export]
# installs torch
# installs opencv-python # maybe not proprietry codecs?
# also intalls most things under the sun and takes for ever to resolve an enviroment on the pi
pip install tzlocal
pip install pandas
pip install pyarrow
pip install fastparquet
# pip install opencv-contrib-python


# update the .bashrc
echo "export DEVICE_NAME=${DEVICE_NAME}" >> /home/$LOCAL_USERNAME/.bashrc
echo "export REMOTE_USERNAME=${REMOTE_USERNAME}" >> /home/$LOCAL_USERNAME/.bashrc
echo "export REMOTE_HOSTNAME=${REMOTE_HOSTNAME}" >> /home/$LOCAL_USERNAME/.bashrc
echo "export REMOTE_PASSWORD=${REMOTE_PASSWORD}" >> /home/$LOCAL_USERNAME/.bashrc
echo "source /home/$LOCAL_USERNAME/vision/bin/activate" >> /home/$LOCAL_USERNAME/.bashrc

# add the chron job
chrontab -e 0 3 * * * /home/$LOCAL_USERNAME/Documents/videoProcessing/send.sh


# last manually restart

# then add running the vidCap.py script to /etc/rc.local once ready
# before exit 0
# source /home/pi/vision/bin/activate
# "export LOCAL_USERNAME=${LOCAL_USERNAME}"
# sudo -u pi python /home/$LOCAL_USERNAME/Documents/videoProcessing/homeVideo/vidCap.py


