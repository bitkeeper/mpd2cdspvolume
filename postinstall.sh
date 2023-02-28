#!/bin/bash
# MPD 2 camilladsp volume sync state file

mkdir -p /var/run/mpd2cdspvol
mkdir -p /var/lib/cdsp

chown -R mpd /var/run/mpd2cdspvol
chown -R mpd /var/lib/cdsp