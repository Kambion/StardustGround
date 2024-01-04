from multimon import Multimon
import json
import signal
import sys
from time import sleep
import logging
import argparse
import queue
from frame import APRSFrame, InvalidFrame
import re
import aprslib

start_frame_re = re.compile(r'^APRS: (.*)')

parser = argparse.ArgumentParser(description='Stardust Ground Station.')
parser.add_argument('-c', dest='config', default='config.json', help='Use this config file')
parser.add_argument('--syslog', action='store_true', help='Log to syslog')
parser.add_argument('--logfile', dest='logfile', help='Log to file')
parser.add_argument('-v', '--verbose', action='store_true', help='Log all traffic - including beacon')
args = parser.parse_args()

config = json.load(open(args.config))

logger = logging.getLogger('pymultimonaprs')
logger.setLevel(logging.DEBUG)

loghandler = logging.FileHandler(config["logfile"])
formatter = logging.Formatter('[%(asctime)s] %(levelname)+8s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
loghandler.setFormatter(formatter)
logger.addHandler(loghandler)

logger.debug("Starting Ground Station")
logger.debug("Tracking callsign: %s" % config["callsign"])

queue = queue.Queue()

mm = Multimon(queue, config, logger)
def signal_handler(signal, frame):
    logger.debug("Stopping Ground Station")
    mm.exit()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print("Started")
while True:
    frame = queue.get()
    frame = frame.decode('ascii')
    frame = start_frame_re.match(frame)
    if(frame):
        frame = frame.group(1)
        print(frame)
        frame = aprslib.parse(frame)
        print(frame)
