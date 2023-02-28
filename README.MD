MPD2CamillaDSPVolume<!-- omit in toc -->
=============================================
bitkeeper @ github 2022

# Introduction

MPD2CamillaDSPVolume makes it possible to control the volume of CamillaDSP with the volume of MPD.

Features:
- Synchronize the volume of [MPD](https://www.musicpd.org/) to [CamillaDSP](https://github.com/HEnquist/camilladsp)
- When [alsa_cdsp](https://github.com/scripple/alsa_cdsp) is sued, support the use of  volume state file

How it works:
* It listens to MPD Mixer changes.
* When the volume changes, send a message to CamillaDSP with the volume.



When using MPD with CamillaDSP the volume of MPD isn't coupled to CamillaDSP.
When using the

# Install
Checkout the repository from github
```
git clone https://github.com/bitkeeper/mpd2cdspvolume.git
cd mpd2cdspvolume
```

`mpd2cdspvolume` is a python script and requires to dependencies:
```bash
pip install -r requirements.txt
```

Copy the scripts to a convient location like:
```bash
sudo cp mpd2cdspvolume.py /usr/local/bin/mpd2cdspvolume
sudo chmod a+x /usr/local/bin/mpd2cdspvolume
sudo cp cdspstorevolume.sh /usr/local/bin/cdspstorevolume
sudo chmod a+x /usr/local/bin/cdspstorevolume
```

When alas_cdsp is used prep the volume state file:
```bash
sudo mkdir -p /var/run/mpd2cdspvol
sudo mkdir -p /var/lib/cdsp

sudo chown -R mpd /var/run/mpd2cdspvol
sudo chown -R mpd /var/lib/cdsp
```


# Commandline use
```
usage: mpd2cdspvolume [-h] [-V] [-v] [--mpd_host MPD_HOST] [--mpd_port MPD_PORT] [--cdsp_host CDSP_HOST] [--cdsp_port CDSP_PORT] [-s VOLUME_STATE_FILE] [-p PID_FILE]

Synchronize MPD volume to CamillaDSP

optional arguments:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
  -v, --verbose         Show debug output.
  --mpd_host MPD_HOST   Host running MPD. (default: 127.0.0.1)
  --mpd_port MPD_PORT   Port user by MPD. (default: 6600)
  --cdsp_host CDSP_HOST
                        Host running CamillaDSP. (default: 127.0.0.1)
  --cdsp_port CDSP_PORT
                        Port used by CamillaDSP. (default: 1234)
  -s VOLUME_STATE_FILE, --volume_state_file VOLUME_STATE_FILE
                        File where to store the volume state. (default: None)
  -p PID_FILE, --pid_file PID_FILE
                        Write PID of process to this file. (default: None)
```




# alsa_cdsp support
When also  [alsa_cdsp](https://github.com/scripple/alsa_cdsp) is used, alsa_cdsp start and stop camilladsp on source change like samplerate. Also when music is pauzed camilladsp is stopped. [moOde](https://www.moode.org) is an example that uses alsa_cdsp

To preserve the volume settings of camilladsp alsa_cdsp a way of using a volume state file:
- Before camilladsp is started, the state file is read and volume is supplied as argument to camilladsp
- Just before shutting down camilladsp an 'exit' command can be executed to store the volume.


When a SIGHUP signal is send to mpd2cdspvolume it read the current volume setting of camilladsp and write it to file.

Md2cdspvolume provides and script `cdspstorevolume` that can be use as 'exit' command, that send the SIGHUP to `mpd2cdspvolume` script.

When MPD volume changes are made, while the music isn't playing or camilladsp isn't active, the volume setting is writen to the state file instead.

To use the state file with alsa_cdsp edit the config and add the `vol_file` and `camilla_exit_cmd` arguments.

For example with moOde add following lines to `/etc/alsa/conf.d/camilladsp.conf`:
```bash
    vol_file "/var/lib/cdsp/camilladsp_volume_state"
    camilla_exit_cmd "/usr/local/bin/cdspstorevolume"
```

To make this work the user of the process who is running should have the rights to send a signal to mpd2cdspvolume.


# mpd2cdspvolume as service
For more convenience mpd2cdspvolume can also be runned as service.
Example service script is provided. Tune it to your own use.

If you use alsa_cdsp run it as the same user as from the process that runs alsa_cdsp/camilladsp. This allows sending signals without additional configuration.



# testing as mpd user
To test if the file rights are correct run the it from the command-line as `mpd` user:

```
sudo -H -u mpd bash -c "python ./mpd2cdspvolume.py --verbose --pid_file /var/run/mpd2cdspvol/mpd2cdspvol.pid --volume_state_file /var/lib/cdsp/camilladsp_volume_state"
```