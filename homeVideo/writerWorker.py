import sys
import cv2



# Define the codec and create a VideoWriter object
def writer_worker(input_queue, output_queue):
    first = True
    while True:
        frames = input_queue.get()  # Get frame from the input queue
        if frame is None:  # None is the signal to exit
            output.release()
            break
        
        if first:
            first = False
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            output = cv2.VideoWriter('output.mp4', 
                                    fourcc, 
                                    30.0, 
                                    (int(frame.shape[1]), int(frame.shape[0])))

        for frame in frames:
            output.write(frame)
        
        output_queue.put(True)
        
