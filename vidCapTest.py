import cv2
import sys

# Create a VideoCapture object to access the webcam (usually 0)
cap = cv2.VideoCapture(int(sys.argv[1]))

# Check if the camera opened successfully
if not cap.isOpened():
    print("Error opening video stream or file")
    exit()

# Define the codec and create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use 'mp4v' for MP4 format
out = cv2.VideoWriter('output.mp4', fourcc, 20.0, (640, 480))  # Adjust resolution as needed

frameCount = 0

while frameCount < 300:
    # Capture frame-by-frame
    ret, frame = cap.read()

    if not ret:
        break

    # Write the frame to the output video
    out.write(frame)
    print(f"read frame {frameCount}")
    frameCount += 1


# Release everything when done
cap.release()
out.release()
cv2.destroyAllWindows()