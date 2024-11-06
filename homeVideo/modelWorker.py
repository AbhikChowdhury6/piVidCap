from ultralytics import YOLO
import sys
import os
# import cv2

# model = YOLO("yolo11n-pose.pt")

# Export the model to NCNN format
# model.export(format="ncnn")  # creates 'yolo11n_ncnn_model'

# print("just before ncnn def")
# sys.stdout.flush()
# ncnn_model = YOLO("yolo11n-pose.torchscript")

# result = ncnn_model("test.jpg")

def model_worker(input_queue, output_queue):
    print("in model worker")
    sys.stdout.flush()

    if not os.path.isfile("yolo11n-pose.torchscript"):
        print("no file found making the torchscript")
        model = YOLO("yolo11n-pose.pt")
        model.export(format="ncnn") 

    ncnn_model = YOLO("yolo11n-pose.torchscript")
    # result = ncnn_model("test.jpg", device='cpu')

    while True:
        # print("waiting for frame!")
        # sys.stdout.flush()
        frame = input_queue.get()  # Get frame from the input queue
        if frame is None:  # None is the signal to exit
            break
        
        # print("got frame!")
        # sys.stdout.flush()
        try:
            # cv2.imshow("frame",frame)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()

            result = ncnn_model(frame)
            # sys.stdout.flush()
            # print("got results!")
            # sys.stdout.flush()
            output_queue.put(len(result[0].names) > 0)
        except Exception as e:
            print(f"Error processing frame: {e}")
            sys.stdout.flush()
