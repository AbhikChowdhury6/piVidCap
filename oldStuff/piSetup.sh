#!/bin/bash

# ssh-keygen -t rsa
# copy key with ssh-copy-id uploadingGuest@192.168.1.113
# ssh in

# sudo apt update
# if needed: sudo rm -r /var/lib/apt/lists/*
# sudo apt upgrade -y

# first manually clone repo
# sudo apt install git
# git clone https://github.com/AbhikChowdhury6/videoProcessing.git ~/Documents/videoProcessing
# run 

#in this script

#echo "enter the device name"
#read DEVICE_NAME
#export DEVICE_NAME=cam1Test
#echo "enter the local username"
#read LOCAL_USERNAME
#echo "enter the remote username"

sudo apt install -y  rpicam-apps


#install miniconda
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3-Linux-aarch64.sh
rm Miniforge3-Linux-aarch64.sh
source ~/.bashrc


conda create --name vision
conda activate vision
conda install -y ultralytics pytorch torchvision pyarrow fastparquet tzlocal

sudo apt update && sudo apt upgrade
sudo apt install libcap-dev libatlas-base-dev ffmpeg libopenjp2-7
sudo apt install libcamera-dev
sudo apt install libkms++-dev libfmt-dev libdrm-dev

pip install --upgrade pip
pip install wheel
pip install rpi-libcamera rpi-kms picamera2 av

mkdir -p ~/Documents/collectedData
ssh-copy-id uploadingGuest@192.168.1.113

# add exporting the envrionment variables to the .bashrc
echo "export DEVICE_NAME=piCam" >> /home/pi/.bashrc

# add activating the vision environment to the .bashrc
echo "source /home/pi/miniforge3/bin/activate vision" >> /home/pi/.bashrc

# for framing
# on pi
# libcamera-vid --width 640 --height 480 --rotation 180 -t 0 --inline --listen -o tcp://0.0.0.0:8888
# on installing machine
# mpv --fps=40 --no-correct-pts tcp://192.168.1.17:8888/

# add the chron job to send the files
chrontab -e
#0 3 * * * /home/pi/miniforge3/envs/vision/bin/python3.12 /home/pi/Documents/videoProcessing/send.py


# TODO - install tmux so i can run the vidcap software in a persistent terminal




# we don't do this anymore
# echo "/usr/lib/python3/dist-packages" >> /home/pi/miniforge3/envs/vision/lib/python3.12/site-packages/conda.pth


# test vidcap and figure out how to get to the camera in v4l2

# check gpu mem vcgencmd get_mem gpu

# sudo modprobe bcm2835-v4l2

# bruh I did sudo rpi-update and a reboot and now at least I'm getting frames


#sudo nano /usr/share/libcamera/pipeline/rpi/vc4/rpi_apps.yaml 
# add     "camera_timeout_value_ms":    10000000,

#sudo nano /etc/dphys-swapfile
# update swap to 3000


# then add running the vidCap.py script to /etc/rc.local once ready
# before exit 0
# source /home/pi/vision/bin/activate
# "export LOCAL_USERNAME=${LOCAL_USERNAME}"
# sudo -u pi python /home/$LOCAL_USERNAME/Documents/videoProcessing/homeVideo/vidCap.py