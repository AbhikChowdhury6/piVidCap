#!/bin/bash

# first manually clone repo

#in this script

echo "enter the device name"
read DEVICE_NAME
echo "enter the remote username"
read REMOTE_USERNAME
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
echo "export DEVICE_NAME=${DEVICE_NAME}" >> ~/.bashrc
echo "export REMOTE_USERNAME=${REMOTE_USERNAME}" >> ~/.bashrc
echo "export REMOTE_PASSWORD=${REMOTE_PASSWORD}" >> ~/.bashrc
echo "source ~/vision/bin/activate" >> ~/.bashrc

# add the chron job
chrontab -e 0 3 * * * /home/$USER/Documents/videoProcessing/send.sh

source ~/.bashrc
# last manually restart

# then add running the vidCap.py script to /etc/rc.local once ready
# before exit 0
# source /home/pi/vision/bin/activate
# sudo -u pi python /home/pi/Documents/videoProcessing/homeVideo/vidCap.py


