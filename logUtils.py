import logging
import logging.handlers
import colorlog
from datetime import datetime

# for formatter attributes I went to 
# https://docs.python.org/3/library/logging.html
# and went to the LogRecord attributes section

def listener_configurer(logfile_path="/home/pi/vcap.log", lvl = 10):
    formatter = logging.Formatter('[%(asctime)s] [%(filename)s] [%(funcName)s] [%(module)s] [%(name)s] [%(processName)s] [%(levelname)s] %(message)s')

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

def listener_process(queue, buffSecs, exitSignal):
    listener_configurer()
    while True:
        if exitSignal[0] == 1:
            startExitTime = datetime.now()
            while (datetime.now() - startExitTime).total_seconds < buffSecs + 2:
                record = queue.get()
                logger = logging.getLogger(record.name)
                logger.handle(record)
            break
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
