from multimon import Multimon
import json
import signal
import sys
from time import sleep
import argparse
from frame import APRSFrame, InvalidFrame

parser = argparse.ArgumentParser(description='Stardust Ground Station.')
parser.add_argument('-c', dest='config', default='config.json', help='Use this config file')
parser.add_argument('--syslog', action='store_true', help='Log to syslog')
parser.add_argument('--logfile', dest='logfile', help='Log to file')
parser.add_argument('-v', '--verbose', action='store_true', help='Log all traffic - including beacon')
args = parser.parse_args()

config = json.load(open(args.config))

def mmcb(tnc2_frame):
    try:
        frame = APRSFrame()
        frame.import_tnc2(tnc2_frame)
        if config['append_callsign']:
            frame.path.extend([u'qAR', config['callsign']])

        # Filter packets from TCP2RF gateways
        reject_paths = set(["TCPIP", "TCPIP*", "NOGATE", "RFONLY"])
        # '}' is the Third-Party Data Type Identifier (used to encapsulate pkgs)
        # indicating traffic from the internet
        if len(reject_paths.intersection(frame.path)) > 0 or frame.payload.startswith("}"):
            print("rejected: %s" % frame.export(False))
        else:
            print("%s" % frame.export(False))

    except InvalidFrame:
        pass


mm = Multimon(mmcb,config)
def signal_handler(signal, frame):
    print("Stopping pymultimonaprs")
    mm.exit()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

while True:
    sleep(10)