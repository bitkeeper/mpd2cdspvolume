#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Script for updating the CamillaDSP volume on MPD volume changes.
#
#
# The MIT License
#
# Copyright (c) 2023 bitkeeper @ github
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import os
from typing import Callable, Optional
import argparse
import time
import signal
import logging
from pathlib import Path
from math import log10
from mpd import MPDClient, ConnectionError

from camilladsp import CamillaConnection

VERSION = "0.1.0"

class MPDMixerMonitor:
    """ Monitors MPD for mixer changes and callback when so
        callback receives as argument the volume in dbs.
    """
    def __init__(self, host: str= "127.0.0.1", port: int = 6600, callback: Callable= None):
        self._host = host
        self._port = port
        self._callback = callback

        self._client = MPDClient()               # create client object
        self._client.timeout = 10                # network timeout in seconds (floats allowed), default: None
        self._client.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None


        self._kill_now = False
        """ Indicates if signal to close app is received"""

    def exit_gracefully(self, signum, frame):
        logging.info('close the shop')
        global kill_now
        self._kill_now = True
        self._client.close()

    def _handle_mpd_status(self, status: dict):
        if 'volume' in status:
            volume = float(status['volume'])
            volume_db = 20*log10(volume/100.0) if volume > 0 else -51.0
            logging.info('vol update = %d : %.2f dB', volume, volume_db)

            if self._callback:
                self._callback(volume_db)

    def run_monitor(self):
        while self._kill_now is False:
            try:
                changed = self._client.idle()
                if 'mixer' in changed:
                    self._handle_mpd_status(self._client.status())
            except (ConnectionError, ConnectionRefusedError):
                while self._kill_now is False:
                    try:
                        self._client.connect(self._host, self._port)
                        break
                    except ConnectionRefusedError:
                        logging.info('couldn\'t connect to MPD, retrying')
                        time.sleep(1)

        self._client.disconnect()



class CamillaDSPVolumeUpdater:
    """Updates CamillaDSP volume
       When cdsp isn't running and a volume state file for alsa_cdsp is provided that one is updated
    """
    def __init__(self, volume_state_file: Optional[Path] = None, host: str='127.0.0.1', port:int=1234):
        self._volume_state_file: Optional[Path]= volume_state_file
        self._cdsp = CamillaConnection(host, port)
        if volume_state_file:
            logging.info('volume state file: "%s"', volume_state_file )

    def update_alsa_cdsp_volume_file(self, volume_db: float, mute: int=0):
        if self._volume_state_file and self._volume_state_file.exists():
            logging.info('update volume state file : %.2f dB, mute: %d', volume_db,mute)
            self._volume_state_file.write_text('{} {}'.format(volume_db, mute))

    def update_cdsp_volume(self, volume_db: float):
        try:
            if self._cdsp.is_connected() is False:
                self._cdsp.connect()

            self._cdsp.set_volume(volume_db)
        except (ConnectionRefusedError, IOError) as e:
            logging.info('no cdsp')
            self.update_alsa_cdsp_volume_file(volume_db)

    def store_volume(self):
        try:
            if self._cdsp.is_connected() is False:
                self._cdsp.connect()

            volume_db = float(self._cdsp.get_volume())
            mute = 1 if self._cdsp.get_mute() else 0
            self.update_alsa_cdsp_volume_file(volume_db, mute)
        except (ConnectionRefusedError, IOError) as e:
            logging.warning('store volume: no cdsp')

    def sig_hup(self, signum, frame):
        self.store_volume()

def get_cmdline_arguments():
    parser = argparse.ArgumentParser(description = 'Synchronize MPD volume to CamillaDSP')

    parser.add_argument('-V', '--version', action='version', version='%(prog)s {}'.format(VERSION))
    parser.add_argument('-v', '--verbose', action='store_true',
                        help = 'Show debug output.')
    parser.add_argument('--mpd_host', default = '127.0.0.1',
                   help = 'Host running MPD. (default: 127.0.0.1)')
    parser.add_argument('--mpd_port', default = 6600, type=int,
                   help = 'Port user by MPD. (default: 6600)')
    parser.add_argument('--cdsp_host', default = '127.0.0.1',
                   help = 'Host running CamillaDSP. (default: 127.0.0.1)')
    parser.add_argument('--cdsp_port', default = 1234, type=int,
                   help = 'Port used by CamillaDSP. (default: 1234)')

    parser.add_argument('-s', '--volume_state_file', type=Path, default = None,
                   help = 'File where to store the volume state. (default: None)')
    parser.add_argument('-p', '--pid_file', type=Path, default = None,
                   help = 'Write PID of process to this file. (default: None)')

    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = get_cmdline_arguments()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    logging.info('start-up mpd2cdspvolume')
    pid_file=args.pid_file
    if pid_file:
        logging.info('pid file: "%s"', pid_file )
        try:
            pid_file.write_text('{}'.format(os.getppid()))
        except PermissionError as e:
            print(e)

    cdsp = CamillaDSPVolumeUpdater(args.volume_state_file, host = args.cdsp_host, port = args.cdsp_port)
    monitor = MPDMixerMonitor(host = args.mpd_host, port = args.mpd_port, callback = cdsp.update_cdsp_volume)

    signal.signal(signal.SIGINT, monitor.exit_gracefully)
    signal.signal(signal.SIGTERM, monitor.exit_gracefully)
    signal.signal(signal.SIGHUP, cdsp.sig_hup)

    monitor.run_monitor()

    if pid_file and pid_file.exists():
        pid_file.unlink()
