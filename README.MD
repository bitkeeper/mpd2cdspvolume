MPD2CamillaDSPVolume<!-- omit in toc -->
=============================================
bitkeeper @ github 2022

Starting from mpd2cdspvolume version `1.0.0` support for camilladsp 1.x is dropped. With that also the command `cdspstorevolume` is dropped.

# Introduction

[MPD2CamillaDSPVolume](https://github.com/bitkeeper/mpd2cdspvolume) makes it possible to control the volume of CamillaDSP with the volume of MPD.

Features:
- Synchronize the volume of [MPD](https://www.musicpd.org/) to [CamillaDSP](https://github.com/HEnquist/camilladsp)
- When [alsa_cdsp](https://github.com/scripple/alsa_cdsp) is used, support the use of  volume state file:
  - When alsa_cdsp stop CamillaDSP the state file is writen
  - When the volume is changed, while no music is playing, also the state file is writen.
- Dynamic range of volume curve is configuratable.
- Volume offset is possible to reduce the volume with a constant value.

How it works:
* It listens to MPD Mixer changes.
* When CamillaDSP is running, the changed volume is send to CamillaDSP else to the statefile.

Requires:
* Add in alsa_cdsp config for the `cargs` the argument to the correct statefile ` -s <path_t_your_statefile>` to start camilladsp with the correct statefile.
* Use the same statefile with mpd2cdspvolume.


# Files
## From source

| File    |      Description    | Packed  as |
|----------  |-----------------|---------------|
| mpd2cdspvolume.py       | mpd volume to camilladsp syncer                           | /usr/local/bin/mpd2cdspvolume |
| etc/mpd2cdspvolume.conf | tmpfs files to created                                    | /usr/lib/tmpfiles.d/mpd2cdspvolume.conf |
| etc/mpd2cdspvolume.service | systemd service file                                   | /lib/systemd/system/mpd2cdspvolume.service |
| etc/mpd2cdspvolume.config | mpd2cdspvolume config file*                                  | /etc/mpd2cdspvolume.config
| etc/postinstall.sh      | runned as part of deb install                             | na |

*) contains dynamic_range and volume_offset

## Run-time created/used state files

| File    |      Description    |
|----------  |-----------------|
| /var/run/mpd2cdspvol/mpd2cdspvol.pid | Contains PID of mpd2cdspvolume. Path is in a temp.fs and is created on boot by `usr/lib/tmpfiles.d/mpd2cdspvolume.conf` |
| /var/lib/cdsp/statefile.yml | Contains the volume_state as required by camilladsp. Path is postinstall.sh (typical runned on deb install time)|

# Install


## As source
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
sudo chmod a+x /usr/local/bin/cdspstorevolume
sudo cp etc/mpd2cdspvolume.conf usr/lib/tmpfiles.d/
```

When alas_cdsp is used prep the volume state file:
```bash
sudo mkdir -p /var/lib/cdsp
sudo chown -R mpd /var/lib/cdsp
```

# Commandline use
```bash
usage: mpd2cdspvolume [-h] [-V] [-v] [--mpd_host MPD_HOST] [--mpd_port MPD_PORT] [--cdsp_host CDSP_HOST] [--cdsp_port CDSP_PORT] [-s VOLUME_STATE_FILE] [-p PID_FILE] [-c CONFIG]

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
  -c CONFIG, --config CONFIG
                        Load config from a file (default: None)
```

example:

```bash
sudo -H -u mpd bash -c "/usr/local/bin/mpd2cdspvolume --verbose --pid_file /var/run/mpd2cdspvol/mpd2cdspvol.pid --volume_state_file /var/lib/cdsp/statefile.yml --config /etc/mpd2cdspvolume.config"
```
This will run the program as user `mpd` and with `--verbose` show output of the actions.

## alsa_cdsp support
When also  [alsa_cdsp](https://github.com/scripple/alsa_cdsp) is used, alsa_cdsp start and stop camilladsp on source change like samplerate. Also when music is pauzed camilladsp is stopped. [moOde](https://www.moode.org) is an example that uses alsa_cdsp

To preserve the volume settings of camilladsp alsa_cdsp a way of using a volume state file:
- camilladsp gets and argument at startup with the used statefile


When MPD volume changes are made, while the music isn't playing or camilladsp isn't active, the volume setting is writen to the state file instead.

To use the state file with alsa_cdsp edit the config and add the `vol_file` and `camilla_exit_cmd` arguments.

For example with moOde add following lines to `/etc/alsa/conf.d/camilladsp.conf`:
```bash
   cargs [
        -p "1234"
        -a "0.0.0.0"
        -s "/var/lib/cdsp/statefile.yml"
   ]
```

To make this work the user of the process who is running should have the rights to send a signal to mpd2cdspvolume.


## mpd2cdspvolume as service
For more convenience mpd2cdspvolume can also be runned as service.
Example service script is provided. Tune it to your own use.

If you use alsa_cdsp run it as the same user as from the process that runs alsa_cdsp/camilladsp. This allows sending signals without additional configuration.


# build debian package
With the script `builddep.sh` you can build a debian package for `mpd2cdspvolume`.
This requires that you have `fpm` installed.
And to the system where the package should be installed also the following packages should be present:
* python3-mpd2
* python3-camilladsp



