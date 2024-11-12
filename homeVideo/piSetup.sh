#!/bin/bash


# copy key with ssh-copy-id
# ssh in

# sudo apt update
# if needed: sudo rm -r /var/lib/apt/lists/*
# sudo apt upgrade -y

# first manually clone repo
# sudo apt install git
# git clone https://github.com/AbhikChowdhury6/videoProcessing.git ~/Documents/videoProcessing
# run 

#in this script

echo "enter the device name"
read DEVICE_NAME
echo "enter the local username"
read LOCAL_USERNAME
echo "enter the remote username"


sudo apt install -y  rpicam-apps


#install miniconda
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3-Linux-aarch64.sh
rm Miniforge3-Linux-aarch64.sh
source ~/.bashrc


conda create --name vision
conda activate vision
conda install -y ultralytics pytorch torchvision pyarrow fastparquet tzlocal

# I am here
# test vidcap and figure out how to get to the camera in v4l2

export DEVICE_NAME=cam1Test
sudo modprobe bcm2835-v4l2

mkdir -p ~/Documents/collectedData


# things left to do
# add exporting the envrionment variables to the .bashrc
echo "export DEVICE_NAME=${DEVICE_NAME}" >> /home/$LOCAL_USERNAME/.bashrc

# add activating the vision environment to the .bashrc
echo "source /home/$LOCAL_USERNAME/vision/bin/activate" >> /home/$LOCAL_USERNAME/.bashrc

# add chron jobs for sending data and restarting processes

# update etc/rc.local to start vidcap on boot up






# for framing
# on pi
# libcamera-vid -t 0 --inline --listen -o tcp://0.0.0.0:8888
# on installing machine
# got to tcp/h264://XXX.XXX.XXX.XXX:8888/ in VLC > Media > open network stream


sudo apt install -y libcap-dev libcamera-dev
pip install picamera2
pip install rpi-libcamera
# pip install opencv-contrib-python


# update the .bashrc

# add the chron job to send the files
chrontab -e 0 3 * * * /home/$LOCAL_USERNAME/Documents/videoProcessing/send.sh
#TODO also add a chron job to restart the vidcap proces since there appear to be some memory leaks still

# last manually restart

# then add running the vidCap.py script to /etc/rc.local once ready
# before exit 0
# source /home/pi/vision/bin/activate
# "export LOCAL_USERNAME=${LOCAL_USERNAME}"
# sudo -u pi python /home/$LOCAL_USERNAME/Documents/videoProcessing/homeVideo/vidCap.py


