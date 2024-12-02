from ultralytics import YOLO
import sys
import os
# import cv2



def model_worker(input_queue, output_queue):
    print("in model worker")
    sys.stdout.flush()
    model = YOLO("yolo11x.pt")

    while True:
        # print("waiting for frame!")
        # sys.stdout.flush()
        frame = input_queue.get()  # Get frame from the input queue
        if frame is None:  # None is the signal to exit
            print("exiting model worker")
            sys.stdout.flush()
            break
        
        # print("got frame!")
        # sys.stdout.flush()
        try:
            # cv2.imshow("frame",frame)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()

            r = model(frame)
            # sys.stdout.flush()
            # print("got results!")
            # sys.stdout.flush()
            # sys.stdout.flush()
            # print(result[0].boxes.data)
            # sys.stdout.flush()
            indexesOfPeople = [i for i, x in enumerate(r[0].boxes.cls) if x == 0]
            ret = False
            if len(indexesOfPeople) > 0:
                print(f"saw {len(indexesOfPeople)} people")
                sys.stdout.flush()
                maxPersonConf = max([r[0].boxes.conf[i] for i in indexesOfPeople])
                print(f"the most confident recognition was {maxPersonConf}")
                sys.stdout.flush()
                if maxPersonConf > .25:
                    ret = True
            else:
                print("didn't see anyone")
                sys.stdout.flush()
            
            print(f"sending {ret}")
            sys.stdout.flush()
            output_queue.put(ret)
            del r
            del frame
        except Exception as e:
            print(f"Error processing frame: {e}")
            sys.stdout.flush()
