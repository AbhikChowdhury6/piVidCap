import cv2
import subprocess

cap = cv2.VideoCapture(0)
ffmpeg_cmd = [
    "ffmpeg", "-y", "-f", "rawvideo", "-pixel_format", "bgr24",
    "-video_size", "640x480", "-framerate", "30", "-i", "-",
    "-c:v", "libaom-av1", "-crf", "30", "-b:v", "0", "output_av1.mkv"
]
process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    process.stdin.write(frame.tobytes())  # Send raw frame data

cap.release()
process.stdin.close()
process.wait()