import logging
import sys

logger = logging.getLogger('birdfish')


log_level = 'DEBUG'

# TODO proper tmp file needed
log_file = '/tmp/birdfish.log'

if hasattr(logging, log_level):
    logger.setLevel(getattr(logging, log_level))

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

file_log = logging.FileHandler(log_file)

file_log.setFormatter(formatter)

logger.addHandler(file_log)

# TODO: should we always log to console, doesn't seem worth another setting
logger.addHandler(logging.StreamHandler(sys.stdout))

