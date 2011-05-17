import logging
import sys

print __name__

logger = logging.getLogger('birdfish')


log_level = 'DEBUG'

if hasattr(logging, log_level):
    logger.setLevel(getattr(logging, log_level))

# TODO: should we always log to console, doesn't seem worth another setting
logger.addHandler(logging.StreamHandler(sys.stdout))

# TODO proper tmp file needed
log_file = '/tmp/birdfish.log'
try:
    logger.addHandler(logging.FileHandler(log_file))
except (KeyError, AttributeError):
    pass

