#!/bin/bash

# to use set up enviroment variables with
# remote username
# remote host
# remote password
# local device name

# this script will
# at 3am
# send yesterdays folder to 

#TODO
#transfer all folders except for the one for the current day

DEVICE_NAME=${DEVICE_NAME:-"notSet"}

# Set up environment variables for SCP
REMOTE_USER=${REMOTE_USER:-""}
REMOTE_PASS=${REMOTE_PASS:-""}
REMOTE_HOST=${REMOTE_HOST:-""}

YESTERDAY=$(date -d "yesterday" +"%Y-%m-%d")
LOCAL_FOLDER=${LOCAL_FOLDER:-"/home/${USER}/Documents/collectedData/${DEVICE_NAME}_${YESTERDAY}"}

YEAR_MONTH=$(date +"%Y-%m")
REMOTE_FOLDER=${REMOTE_FOLDER:-"/home/${REMOTE_USER}/Documents/videoData/${YEAR_MONTH}/"}

# Ensure environment variables are set
if [[ -z "$REMOTE_USER" || -z "$REMOTE_PASS" || -z "$REMOTE_HOST" ]]; then
    echo "Error: REMOTE_USER, REMOTE_PASS, and REMOTE_HOST must be set as environment variables."
    exit 1
fi

# Install sshpass if not already installed (required for password automation)
if ! command -v sshpass &> /dev/null; then
    echo "Installing sshpass for automated password entry..."
    sudo apt update && sudo apt install sshpass -y
fi

# Create remote directory if it doesn't exist
sshpass -p "$REMOTE_PASS" ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_FOLDER"

# Use sshpass with scp to copy the local folder to the remote server
sshpass -p "$REMOTE_PASS" scp -r "$LOCAL_FOLDER" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_FOLDER"

# Check if the transfer was successful and delete yesterdays files locally
if [[ $? -eq 0 ]]; then
    echo "Folder successfully transferred to $REMOTE_USER@$REMOTE_HOST:$REMOTE_FOLDER"
    rm -rf $LOCAL_FOLDER
else
    echo "Failed to transfer the folder."
fi