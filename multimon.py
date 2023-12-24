#!/usr/bin/python2

import threading
import subprocess
import re

start_frame_re = re.compile(r'^APRS: (.*)')


class Multimon:
    def __init__(self, frameQueue, config, logger):
        self.config = config
        self.frameQueue = frameQueue
        self.logger = logger
        self.subprocs = {}
        self._start()
        self._running = True
        self._worker = threading.Thread(target=self._mm_worker)
        self._worker.setDaemon(True)
        self._worker.start()

    def exit(self):
        self._running = False
        self._stop()

    def _start(self):
        self.logger.debug("Starting Multimon")
        proc_src = subprocess.Popen(
            ['rtl_fm', '-f', str(int(self.config['rtl']['freq'] * 1e6)), '-s', '22050',
             '-p%s' % str(self.config['rtl']['ppm']), '-g', str(self.config['rtl']['gain']),
             '-E', 'offset' if self.config['rtl'].get('offset_tuning', False) else 'none',
             '-d', str(self.config['rtl'].get('device_index', 0)), '-'],
            stdout=subprocess.PIPE, stderr=open('/dev/null')
        )
        proc_mm = subprocess.Popen(
            ['multimon-ng', '-a', 'AFSK1200', '-A', '-t', 'raw', '-'],
            stdin=proc_src.stdout,
            stdout=subprocess.PIPE, stderr=open('/dev/null')
        )
        self.subprocs['src'] = proc_src
        self.subprocs['mm'] = proc_mm

    def _stop(self):
        for name in ['mm', 'src']:
            try:
                proc = self.subprocs[name]
                proc.terminate()
            except:
                pass

    def _mm_worker(self):
        while self._running:
            line = self.subprocs['mm'].stdout.readline()
            line = str(line.strip())
            self.frameQueue.put(line)
            #m = start_frame_re.match(line)
            #if m:
                #tnc2_frame = m.group(1)
                #self.frame_handler(tnc2_frame)
