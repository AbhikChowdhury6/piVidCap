import logging
import logging.handlers
import colorlog


# for formatter attributes I went to 
# https://docs.python.org/3/library/logging.html
# and went to the LogRecord attributes section

def listener_configurer(logfile_path="/home/pi/vcap.log", lvl = 10):
    formatter = logging.Formatter('[%(asctime)s] [%(processName)s] [%(levelname)s] %(message)s')

    # File handler
    file_handler = logging.FileHandler(logfile_path)
    file_handler.setFormatter(formatter)

    # Stream handler (stdout)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s[%(asctime)s] [%(processName)s] [%(levelname)s] %(message)s',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
        }
    ))

    # Root logger
    root = logging.getLogger()
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
    root.setLevel(lvl)

def worker_configurer(queue, lvl = 10):
    handler = logging.handlers.QueueHandler(queue)
    root = logging.getLogger()
    root.handlers = []  # Remove default handlers
    root.addHandler(handler)
    root.setLevel(lvl)

def listener_process(queue):
    listener_configurer()
    while True:
        try:
            record = queue.get()
            if record is None:
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)
        except Exception:
            import traceback
            print("Error in logger listener:")
            traceback.print_exc()
