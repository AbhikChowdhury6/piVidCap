import cv2
import pytesseract
import time

testFile = '/media/chowder/abhiksFiles/personalData/wyzeCams/roomCamBy3dp/20201230/10/20.mp4'
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

from concurrent.futures import ProcessPoolExecutor

startTime = time.time()

def ocr_image(image_frame):
    custom_config = '--psm 6 -l eng'
    return (image_frame[0], pytesseract.image_to_string(image_frame[1], config=custom_config))

def getFrames(fileLocation):
    frames = []
    cap = cv2.VideoCapture(fileLocation)
    frameNum = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break   
        x1, y1 = 1350, 1000  # Starting coordinates
        x2, y2 = 1900, 1080  # Ending coordinates
        cropped_frame = frame[y1:y2, x1:x2]
        image_resized = cv2.resize(cropped_frame, (cropped_frame.shape[1] // 2, cropped_frame.shape[0] // 2), interpolation=cv2.INTER_LINEAR)
        img_rgb = cv2.cvtColor(image_resized, cv2.COLOR_BGR2RGB)
        frames.append((frameNum, img_rgb))
        frameNum += 1
    return frames

# List of images to process
image_frames = getFrames(testFile)[:100]

# Use ProcessPoolExecutor for parallel processing
with ProcessPoolExecutor() as executor:
    results = executor.map(ocr_image, image_frames)

for result in results:
    print(result)

print(time.time() - startTime)