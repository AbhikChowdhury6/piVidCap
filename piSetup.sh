#!/bin/bash

# 
# copy key with ssh-copy-id pi@192.168.1.XX
# ssh in

# sudo apt update
# if needed: sudo rm -r /var/lib/apt/lists/*
# sudo apt upgrade -y

# first manually clone repo
# sudo apt install git
# git clone https://github.com/AbhikChowdhury6/piVidCap.git ~/Documents/piVidCap
# run 

#in this script

#edit the exdeviceInfo.py
#rename it to deviceInfo.py

#sudo rm -r /var/lib/apt/lists/*
#sudo apt update && sudo apt upgrade -y
sudo apt install -y  rpicam-apps tmux


#install miniconda
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3-Linux-aarch64.sh
rm Miniforge3-Linux-aarch64.sh
source ~/.bashrc

source ~/miniforge3/etc/profile.d/conda.sh
conda create --name vision311 python=3.11
source activate vision311
conda install -y ultralytics pytorch torchvision pyarrow fastparquet tzlocal colorlog

sudo apt update && sudo apt upgrade -y
sudo apt install -y libcap-dev libatlas-base-dev ffmpeg libopenjp2-7
sudo apt install -y libcamera-dev
sudo apt install -y libkms++-dev libfmt-dev libdrm-dev

pip install --upgrade pip
# libcamera was a bit ahead of rpi-libcamera so i got this form pypi
pip install rpi-libcamera -C setup-args="-Dversion=unknown"
pip install rpi-kms picamera2 av


mkdir -p ~/Documents/collectedData
ssh-keygen -t rsa
ssh-copy-id uploadingGuest@192.168.1.20


# add activating the vision environment to the .bashrc
echo "source /home/pi/miniforge3/bin/activate vision311" >> /home/pi/.bashrc

# there's been a bug where the model inferece stops working ## <- written on 12/26/24
# with no detections or a bunch of random detections
# here are the comands to downgrade torch for cpu inference that may fix it
# pip uninstall torch torchvision torchaudio -y
# pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu


# for framing
# on pi
# libcamera-vid --width 1920 --height 1080 -t 0 --inline --listen -o tcp://0.0.0.0:8888
# on installing machine
# mpv --fps=40 --demuxer-lavf-probesize=32 tcp://192.168.1.20:8888/


# add the chron job to send the files
crontab -e
#0 8 * * * /home/pi/miniforge3/envs/vision311/bin/python3.11 /home/pi/Documents/piVidCap/send.py

sudo reboot

#code to run capture
# python /home/pi/Documents/piVidCap/main.py

# try adding to rc.local
# sudo nano /etc/rc.local
# su - pi -c "tmux new-session -d -s 0 '/home/pi/miniforge3/envs/vision/bin/python3.12 /home/pi/Documents/piVidCap/piVidCap.py -1'"


# we don't do this anymore
# echo "/usr/lib/python3/dist-packages" >> /home/pi/miniforge3/envs/vision/lib/python3.12/site-packages/conda.pth


# test vidcap and figure out how to get to the camera in v4l2

# check gpu mem vcgencmd get_mem gpu

# sudo modprobe bcm2835-v4l2

# bruh I did sudo rpi-update and a reboot and now at least I'm getting frames


#sudo nano /usr/share/libcamera/pipeline/rpi/vc4/rpi_apps.yaml 
# add     "camera_timeout_value_ms":    10000000,

#sudo nano /etc/dphys-swapfile
# update swap to 5000


# then add running the vidCap.py script to /etc/rc.local once ready
# before exit 0
# source /home/pi/vision/bin/activate
# "export LOCAL_USERNAME=${LOCAL_USERNAME}"
# sudo -u pi python /home/$LOCAL_USERNAME/Documents/videoProcessing/homeVideo/vidCap.py