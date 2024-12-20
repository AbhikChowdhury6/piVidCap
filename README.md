to check folder size
du -s -h videoData/

to recursively make files in a folder permissable
chmod -R 777 piCam_2024-12-14-0700/

moving recent captures:
mv /home/uploadingGuest/recentCaptures/* /home/chowder/Documents/recentCaptures/

so for this file structure:

videoProcessing

videoFiles
|___homeVideo
|   |___bathroomCam
|   |___bedroomCam
|   |___kitchen
|   |___frontDoor
|___otherVideos (egocentric, dashcam, office, etc.)

workingData
|___homeVideo
    |___bathroomCam
    |___bedroomCam
    |___kitchen
    |___frontDoor# videoProcessing
