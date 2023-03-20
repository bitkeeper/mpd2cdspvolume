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
import time
import configparser
from pathlib import Path
from math import log10, exp, log
from mpd import MPDClient, ConnectionError

from camilladsp import CamillaConnection

VERSION = "0.3.0"

def lin_vol_curve(perc: int, dynamic_range: float= 60.0) -> float:
    '''
    Generates from a percentage a dBA, based on a curve with a dynamic_range.
    Curve calculations coming from: https://www.dr-lex.be/info-stuff/volumecontrols.html

    @perc (int) : linair value between 0-100
    @dynamic_range (float) : dynamic range of the curve
    return (float): Value in dBA
    '''
    x = perc/100.0
    y = pow(10, dynamic_range/20)
    a = 1/y
    b = log(y)
    y=a*exp(b*(x))
    if x < .1:
        y = x*10*a*exp(0.1*b)
    if y == 0:
        y = 0.000001
    return 20* log10(y)
class MPDMixerMonitor:
    """ Monitors MPD for mixer changes and callback when so
        callback receives as argument the volume in dbs.
    """
    def __init__(self, host: str= "127.0.0.1", port: int = 6600, callback: Callable= None, dynamic_range: Optional[int] = None, volume_offset : Optional[float]= None):
        self._host = host
        self._port = port
        self._callback = callback

        self._client = MPDClient()               # create client object
        self._client.timeout = 10                # network timeout in seconds (floats allowed), default: None
        self._client.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None


        self._kill_now = False

        self._volume = None                     # last synced volume
        """ Indicates if signal to close app is received"""

        self._dynamic_range: int = dynamic_range if dynamic_range else 30
        self._volume_offset: float = volume_offset if volume_offset else 0

        logging.info('dynamic_range = %d dB', self._dynamic_range)
        logging.info('volume_offset = -%d dB', abs(self._volume_offset))

    def exit_gracefully(self, signum, frame):
        logging.info('close the shop')
        global kill_now
        self._kill_now = True
        self._client.close()

    def _handle_mpd_status(self, status: dict):
        """

        @return False when the volume was the same as the previous one, else True
        """

        if 'volume' in status:
            volume = float(status['volume'])
            if volume != self._volume:
                # volume_db = 20*log10(volume/100.0) if volume > 0 else -51.0
                volume_db = lin_vol_curve(volume, self._dynamic_range) - abs(self._volume_offset)

                logging.info('vol update = %d : %.2f dB', volume, volume_db)

                if self._callback:
                    if self._callback(volume_db) == False and (self._volume == 0 or volume == 0):
                        # when unmute fails, give cdsp a little more time to start
                        time.sleep(0.4)
                        self._callback(volume_db)
                self._volume = volume
            else:
                return True

        return True

    def run_monitor(self):
        while self._kill_now is False:
            try:
                changed = self._client.idle()
                if 'mixer' in changed:
                    status= self._client.status()
                    # make sure that it is in sync with the latest state of the volume, by repeating untill we get the same volume
                    while self._handle_mpd_status(status):
                        status= self._client.status()

            except (ConnectionError, ConnectionRefusedError):
                while self._kill_now is False:
                    try:
                        self._client.connect(self._host, self._port)
                        self._handle_mpd_status(self._client.status())
                        self._volume = None
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
            try:
                self._volume_state_file.write_text('{} {}'.format(volume_db, mute))
            except FileNotFoundError as e:
                logging.error('Couldn\'t create state file "%s", prob basedir doesn\'t exists.', self._volume_state_file)
            except PermissionError as e:
                logging.error('Couldn\'t write state to "%s", prob incorrect owner rights of dir.', self._volume_state_file)
    def update_cdsp_volume(self, volume_db: float):
        try:
            if self._cdsp.is_connected() is False:
                self._cdsp.connect()

            self._cdsp.set_volume(volume_db)
            return True
        except (ConnectionRefusedError, IOError) as e:
            logging.info('no cdsp')
            self.update_alsa_cdsp_volume_file(volume_db)
            return False

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
    parser.add_argument('-c', '--config', type=Path,
                   help = 'Load config from a file (default: None)')


    args = parser.parse_args()
    return args

def get_config(config_file: Path):
    dynamic_range = None
    volume_offset = None

    if config_file and config_file.is_file():
        config = configparser.ConfigParser()
        config.read(config_file)


        if 'default' in config and 'dynamic_range' in config['default']:
            dynamic_range = int(config['default']['dynamic_range'])
        if 'default' in config and 'volume_offset' in config['default']:
            volume_offset = float(config['default']['volume_offset'])
    return dynamic_range, volume_offset

if __name__ == "__main__":
    args = get_cmdline_arguments()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    logging.info('start-up mpd2cdspvolume')

    dynamic_range : Optional[int]= None
    volume_offset : Optional[float]= None

    config_file = args.config
    if config_file and config_file.is_file() is False:
        logging.error('Supplied config file "%s" can\'t be read.', config_file)
        exit(1)
    elif config_file:
        logging.info('config file: "%s"', config_file )
        dynamic_range, volume_offset = get_config(config_file)


    pid_file=args.pid_file
    if pid_file:
        logging.info('pid file: "%s"', pid_file )
        try:
            pid_file.write_text('{}'.format(os.getpid()))
        except FileNotFoundError as e:
            logging.error('Couldn\'t write PID file "%s", prob basedir doesn\'t exists.', pid_file)
            exit(1)
        except PermissionError as e:
            logging.error('Couldn\'t write PID file to "%s", prob incorrect owner rights of dir.', pid_file)
            exit(1)


    state_file = args.volume_state_file
    if state_file and state_file.is_file() is False:
        logging.info('Create statefile %s',state_file)
        try:
            state_file.write_text('0 0')
        except FileNotFoundError as e:
            logging.error('Couldn\'t create state file "%s", prob basedir doesn\'t exists.', state_file)
            exit(1)
        except PermissionError as e:
            logging.error('Couldn\'t write state to "%s", prob incorrect owner rights of dir.', state_file)
            exit(1)


    cdsp = CamillaDSPVolumeUpdater(state_file, host = args.cdsp_host, port = args.cdsp_port)
    monitor = MPDMixerMonitor(host = args.mpd_host, port = args.mpd_port, callback = cdsp.update_cdsp_volume, dynamic_range=dynamic_range, volume_offset=volume_offset)

    signal.signal(signal.SIGINT, monitor.exit_gracefully)
    signal.signal(signal.SIGTERM, monitor.exit_gracefully)
    signal.signal(signal.SIGHUP, cdsp.sig_hup)

    monitor.run_monitor()

    if pid_file and pid_file.exists():
        pid_file.unlink()
