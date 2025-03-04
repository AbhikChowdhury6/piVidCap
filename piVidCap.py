import cv2
import torch
import gc
from datetime import datetime, timedelta

BUFFER_SIZE = 450
HEIGHT = 1080
WIDTH = 1920
CHANNELS = 3
DTYPE = torch.uint8

def pi_vid_cap(frame_buffer, time_buffer, frame_index):
    """ Captures frames and writes to the shared buffer in a circular fashion. """
    st = datetime.now() 
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (1920, 1080), "format": "RGB888"})
    picam2.configure(video_config)
    picam2.start()
    print(f"The cap took {datetime.now()  - st} to initialize")

    st = datetime.now()
    frame = picam2.capture_array()
    print(f"The first Frame took {datetime.now() - st} to capture")
    del frame
    gc.collect()
    
    def delayTill100ms(): # a bit offset to compensate for read lag
        msToDelay = 100 - ((datetime.now().microsecond / 1000) % 100)
        time.sleep(msToDelay/1000)

    st = datetime.now()
    secondsToWait = (14 - (st.second % 15)) + (1 - st.microsecond/1_000_000)
    print(f"waiting {secondsToWait} till {timedelta(seconds=urrTime + secondsToWait)}")
    time.sleep(secondsToWait)

    frame_index[0] = -1

    while True:
        idx = frame_index[0].item()
        
        frameTime = datetime.now().astimezone()
        frame_buffer[frame_index] = picam2.capture_array()
        cv2.putText(frame_buffer[frame_index], frameTS, (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, 
                (0, 255, 0), 2, cv2.LINE_AA)

        time_buffer[frame_index] = frameTime.astimezone(ZoneInfo("UTC"))
        frameTS = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")

        delayTill100ms()
        # Update frame index
        frame_index[0] = (idx + 1) % BUFFER_SIZE

    cap.release()
