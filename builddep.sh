#!/bin/bash
#########################################################################
#
# Build script mpd2cdspvolume debian package
#
# (C) bitkeeper 2023 https://github.com/bitkeeper/mpd2cdspvolume
# License: MIT
#
#########################################################################


if [ -z "$PKGNAME" ]
then
PKGNAME="mpd2cdspvolume"
fi

if [ -z "$PKGVERSION" ]
then
PKGVERSION="0.2.2"
fi

if [ -z "$DEBVER" ]
then
DEBVER="1"
fi

if [ -z "$DEBLOC" ]
then
DEBLOC=""
fi

#------------------------------------------------------------
# Prep root to pack
mkdir -p root/usr/local/bin
cp mpd2cdspvolume.py root/usr/local/bin/mpd2cdspvolume
cp cdspstorevolume.sh root/usr/local/bin/cdspstorevolume
mkdir -p root/usr/lib/tmpfiles.d
cp etc/mpd2cdspvolume.conf root/usr/lib/tmpfiles.d/

chmod a+x root/usr/local/bin/mpd2cdspvolume
chmod a+x root/usr/local/bin/cdspstorevolume

# build the package
fpm -s dir -t deb -n $PKGNAME -v $PKGVERSION \
--license MIT \
--category misc \
-S moode \
--iteration $DEBVER$DEBLOC \
-a all \
--deb-priority optional \
--url https://github.com/bitkeeper/mpd2cdspvolume \
-m $DEBEMAIL \
--license LICENSE \
--description "Service for synchronizing MPD volume to CamillaDSP." \
--deb-systemd etc/mpd2cdspvolume.service \
--depends python3-mpd2 \
--depends python3-camilladsp \
--after-install etc/postinstall.sh \
root/usr/=/usr/.

