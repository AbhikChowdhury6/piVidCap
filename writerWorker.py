import cv2
import torch
from datetime import datetime, timedelta
import bisect

#frame_index is the latest frame
def writer(frame_buffer, time_buffer, person_buffer, frame_index):
    """ Reads the latest frame from the shared buffer and displays it. """
    while True:
        # wait till a round 15 seconds and then
        st = datetime.now()
        secondsToWait = (14 - (st.second % 15)) + (1 - st.microsecond/1_000_000)
        print(f"waiting {secondsToWait} till {timedelta(seconds=urrTime + secondsToWait)}")
        time.sleep(secondsToWait)
        # check if we should save the last 299, 149 or 1 frames
        pbi = frame_index // 150
        prevPbi = (pbi + 2) % 3

        # find the indexes in the circular buffer for the -15 block and the -15 to -30
        tsMinus15 = datetime.now().replace(microsecond=0) - timedelta(seconds=15)
        tsMinus30 = datetime.now().replace(microsecond=0) - timedelta(seconds=30)
        frame_index15 = -1
        search_index = frame_index
        while time_buffer[search_index] > tsMinus30:
            if search_index == frame_index:
                frame_index30 = (search_index + 449) % 450
                break
            
            if frame_index15 == -1 and time_buffer[search_index] < tsMinus15:
                frame_index15 = (search_index + 449) % 450

            frame_index30 = search_index
            search_index = (search_index + 449) % 450
        

        # save it
        latest_idx = (frame_index[0].item() - 1) % frame_buffer.shape[0]  # Get latest frame index
        frame = frame_buffer[latest_idx].numpy()  # Convert back to NumPy

        cv2.imshow("Torch Shared Memory Frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()