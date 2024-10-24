import cv2
import pytesseract
from PIL import Image
import time

testFile = '/media/chowder/abhiksFiles/personalData/wyzeCams/roomCamBy3dp/20201230/10/20.mp4'
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
cap = cv2.VideoCapture(testFile)
shownTsList = []
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    print(frame.shape)
    # Define the region of interest (ROI) to crop
    x1, y1 = 1350, 1000  # Starting coordinates
    x2, y2 = 1900, 1080  # Ending coordinates

    # Crop the frame
    cropped_frame = frame[y1:y2, x1:x2]

    cv2.imshow('cropped image', cropped_frame)


    img_rgb = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
    print(pytesseract.image_to_string(img_rgb, lang='eng'))
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release video and close windows
cap.release()
cv2.destroyAllWindows()
