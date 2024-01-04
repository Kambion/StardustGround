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

class Frame:
    def __init__(self):
        self.source = None
        self.dest = None
        self.path = None
        self.payload = None

start_frame_re = re.compile(r'^APRS: (.*)')
header_re = re.compile(r'^(?P<source>\w*(-\d{1,2})?)>(?P<dest>\w*(-\d{1,2})?),(?P<path>[^\s]*)')

def decode_frame(raw_frame):
    raw_frame = raw_frame.replace("\r", "")
    header, payload = raw_frame.split(":", 1)
    header = header.strip()
    payload = payload.strip()
    frame = Frame()
    try:
        res = header_re.match(header).groupdict()
        frame.source = res['source']
        frame.dest = res['dest']
        frame.path = res['path'].split(',')
    except:
        raise InvalidFrame()
    frame.payload = payload
    return frame

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
        frame = decode_frame(frame)
        print("Source: " + frame.source)
        print("Destination: " + frame.dest)
        print("Payload: " + frame.payload)
