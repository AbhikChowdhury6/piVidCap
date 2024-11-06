import cv2
import pytesseract
import time

testFile = '/media/chowder/abhiksFiles/personalData/wyzeCams/roomCamBy3dp/20201230/10/20.mp4'
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
cap = cv2.VideoCapture(testFile)
shownTsList = []
while cap.isOpened():
    start_time = time.time()
    ret, frame = cap.read()
    if not ret:
        break

    print(frame.shape)
    # Define the region of interest (ROI) to crop the whole timestamp # 130ms
    x1, y1 = 1350, 1000  # Starting coordinates
    x2, y2 = 1900, 1080  # Ending coordinates

    # Region to crop just the seconds # 100ms
    # x1, y1 = 1810, 1000  # Starting coordinates
    # x2, y2 = 1880, 1080  # Ending coordinates

    # Crop the frame
    cropped_frame = frame[y1:y2, x1:x2]

    #full timestamp downsampled is 115ms and allowing all charecters
    #also actually works, going to see how multiprocessing might speed this up
    image_resized = cv2.resize(cropped_frame, (cropped_frame.shape[1] // 2, cropped_frame.shape[0] // 2), interpolation=cv2.INTER_LINEAR)
    cv2.imshow('resized image', image_resized)



    img_rgb = cv2.cvtColor(image_resized, cv2.COLOR_BGR2RGB)
    custom_config = '--psm 6 -l eng'
    print(pytesseract.image_to_string(img_rgb, config=custom_config))
    end_time = time.time()
    print((end_time - start_time) * 1000)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release video and close windows
cap.release()
cv2.destroyAllWindows()
