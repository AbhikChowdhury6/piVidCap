import cv2
import multiprocessing as mp
from modelWorker import model_worker

if __name__ == "__main__":
    cap = cv2.VideoCapture(1)

    ret, frame = cap.read()
    
    mp.set_start_method('spawn', force=True)
    mp.freeze_support()

    model_input_queue = mp.Queue()
    model_output_queue = mp.Queue()

    # Start the worker process
    model_process = mp.Process(target=model_worker, args=(model_input_queue, model_output_queue))
    model_process.start()

    # time.sleep(1)
    print(model_process.is_alive())
    model_input_queue.put(frame)
    result = model_output_queue.get()
    print("Model output:", result)