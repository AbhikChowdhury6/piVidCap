sudo apt install -y git net-tools openssh-server curl htop

#check ip and then ssh-copy-id

ANACONDA_NAME="Anaconda3-2024.10-1-Linux-x86_64.sh"

#install anaconda
curl -O https://repo.anaconda.com/archive/$ANACONDA_NAME
chmod +x 

conda create --name vision
conda activate vision
conda install -y -c conda-forge ultralytics
conda install -y pyarrow fastparquet tzlocal pytorch torchvision

python Documents/videoProcessing/homeVideo/vidCap.py 0
 

export DEVICE_NAME=""

#chrontab -e 0 3 * * * /home/stg/anaconda3/envs/vision/bin/python3.12 /home/stg/Documents/videoProcessing/send.py