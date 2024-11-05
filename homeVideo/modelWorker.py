from ultralytics import YOLO
import sys
import cv2

#model = YOLO("yolo11n-pose.pt")

# Export the model to NCNN format
# model.export(format="ncnn")  # creates 'yolo11n_ncnn_model'


def model_worker(input_queue, output_queue):
    ncnn_model = YOLO("yolo11n-pose.torchscript")
    while True:
        print("waiting for frame!")
        sys.stdout.flush()
        frame = input_queue.get()  # Get frame from the input queue
        if frame is None:  # None is the signal to exit
            break
        
        print("got frame!")
        sys.stdout.flush()
        try:
            result = ncnn_model(frame, device='cpu')
            sys.stdout.flush()
            print("got results!")
            sys.stdout.flush()
            output_queue.put(len(result[0].names) > 0)
        except Exception as e:
            print(f"Error processing frame: {e}")
            sys.stdout.flush()
