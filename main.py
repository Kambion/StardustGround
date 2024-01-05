from multimon import Multimon
import json
import signal
import sys
from time import sleep
import logging
import argparse
from queue import Queue
from frame import APRSFrame, InvalidFrame
import re
import aprslib
import dash
import dash_daq as daq
from dash import html, dcc
import dash_leaflet as dl
from dash_extensions.javascript import assign
from dash.dependencies import Input, Output
import threading

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

queue = Queue()

mm = Multimon(queue, config, logger)
def signal_handler(signal, frame):
    logger.debug("Stopping Ground Station")
    mm.exit()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

positions = []
current_height = 0
semaphore = threading.Semaphore(1)

app = dash.Dash(prevent_initial_callbacks=True, title="SimLE Tracking App")

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script src=\"https://kit.fontawesome.com/68ce9fd520.js\" crossorigin=\"anonymous\"></script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

balloon_icon={"iconUrl": app.get_asset_url('balloon.png'), "iconSize": (40,40), 'iconAnchor':(20,20)}
layerGroup = dl.LayerGroup(id="container", children=[])
map = dl.Map([dl.TileLayer(), dl.LocateControl( locateOptions={'enableHighAccuracy': True},
                                                        keepCurrentZoomLevel=True, icon='fa-solid fa-arrows-to-dot'), layerGroup],
           center=(53.59641833454492, 19.551308688981702), zoom=8, style={'width': '100%', 'height': '99vh',
                                                                          'margin': "auto", "display": "block",
                                                                          'z-index': '0'},  id="map")



logo = html.Img(src='assets/logo.png', style={'width': '150px', 'height': '150px', 'position': 'fixed',
                                              'z-index': '2', 'top': '30px', 'right': '30px'})

heightBar = daq.Tank(
    id='heightbar',
    value=0,
    label={'label': 'Altitude: 0 m','style':{'fontSize':20}},
    labelPosition='bottom',
    height = 600,
    width = 40,
    min=0,
    max=35000,
    scale={'interval': 2000, 'labelInterval': 2},
    style={'position': 'fixed','z-index': '2', 'top': '200px', 'right': '50px'},
    color='red'
)

app.layout = html.Div(
    children=[map,
              logo,
              heightBar,
            dcc.Interval(
                id='interval-component',
                interval=5000,  # Update every 5 seconds
                n_intervals=0
        )
    ]
)
@app.callback([Output('heightbar', 'value'), Output('heightbar', 'label')],[Input('interval-component', 'n_intervals')])
def update_output(n):
    semaphore.acquire()
    value = current_height
    semaphore.release()
    label = {'label': f'Altitude: {value} m','style':{'fontSize':20}}
    return value,label
@app.callback(Output('container', 'children'), [Input('interval-component', 'n_intervals')])
def update_map(n):
    semaphore.acquire()
    path = dl.Polyline(
        positions=positions,
        color='green',
        weight=2,
        opacity=1
    )
    children = [path]
    if len(positions) > 0:
        point = positions[-1]
        marker = dl.Marker(position=point, children=[
            dl.Tooltip(f"Lat: {point[0]}, Lon: {point[1]}")
        ], icon=balloon_icon)
        children.append(marker)
    semaphore.release()
    # Return the marker as the new children of the LayerGroup
    return children

def start_dash_app():
    app.run(host= '0.0.0.0',debug=False)

dash_thread = threading.Thread(target=start_dash_app)
dash_thread.start()

print("Started")
while True:
    frame = queue.get()
    frame = frame.decode('ascii')
    frame = start_frame_re.match(frame)
    if(frame):
        frame = frame.group(1)
        logger.debug(frame)
        try:
            frame = aprslib.parse(frame)
            if 'from' in frame and 'latitude' in frame and 'longitude' in frame:
                if(frame['from'] == config["callsign"]):
                    point = [frame['latitude'], frame['longitude']]
                    semaphore.acquire()
                    positions.append(point)
                    if 'altitude' in frame:
                        current_height = frame['altitude']
                    semaphore.release()

                print(frame['from'] + ": " + str(frame['latitude']) + " " + str(frame['longitude']))
        except:
            pass

