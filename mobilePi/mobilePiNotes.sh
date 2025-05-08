#on startup run 
    # ups hat monitoring
    # pwm fan control
    # video capture
#set up systemd's for all the services

#pwm fan control
sudo nano /etc/systemd/system/pwmtest.service
# [Unit]
# Description=PWM Test Script
# After=network.target

# [Service]
# ExecStart=/usr/bin/python /home/pi/pwmTest.py
# WorkingDirectory=/home/pi
# User=pi
# Restart=on-failure
# StandardOutput=append:/home/pi/pwm.log
# StandardError=append:/home/pi/pwm.log

# [Install]
# WantedBy=multi-user.target

#vision cap
# sudo nano /etc/systemd/system/visioncap.service
# [Unit]
# Description=Run piVidCap in conda env
# After=network.target

# [Service]
# ExecStart=/home/pi/miniforge3/envs/vision/bin/python /home/pi/Documents/piVidCap/main.py
# WorkingDirectory=/home/pi/Documents/piVidCap
# User=pi
# Restart=on-failure
# StandardOutput=append:/home/pi/visioncap.log
# StandardError=append:/home/pi/visioncap.log

# [Install]
# WantedBy=multi-user.target


#ups hat
sudo nano /etc/systemd/system/ups.service
# [Unit]
# Description=Run UPS HAT script
# After=network.target

# [Service]
# ExecStart=/usr/bin/python /home/pi/UPS_HAT_E/ups.py
# WorkingDirectory=/home/pi/UPS_HAT_E
# User=pi
# Restart=on-failure
# StandardOutput=append:/home/pi/ups.log
# StandardError=append:/home/pi/ups.log

# [Install]
# WantedBy=multi-user.target


sudo systemctl daemon-reload
sudo systemctl enable pwmtest.service
sudo systemctl enable visioncap.service
sudo systemctl enable ups.service

sudo systemctl start pwmtest.service
sudo systemctl start visioncap.service
sudo systemctl start ups.service


#rotate the logs
sudo nano /etc/logrotate.d/pi-services
# /home/pi/pwm.log
# /home/pi/visioncap.log
# /home/pi/ups.log {
#     daily
#     rotate 7
#     compress
#     delaycompress
#     missingok
#     notifempty
#     copytruncate
# }


# remember to set the raspi-config country to US to cut down on kernel logs
# when out of wifi range

sudo apt install python3-tzlocal

#to check the end of the latest text file
tail "$(ls -1 *.txt | sort | tail -n 1)"
