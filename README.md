# Clairmeta

Clairmeta is a python package for Digital Cinema Package (DCP) probing and checking.

This project status is *Beta*, the following needs to be done for the release :
- Large scale tests on lots DCP (including D-Box, DVIs, OCAP, CCAP, ...)
- Copyright free test materials for unittest
- Proper packaging (we plan to support Ubuntu 14.04 / 16.04 at first), this include
clairmeta python package, all the dependent python package and asdcplib.

## Features

* DCP Probe : metadata extraction of the whole DCP, including all XML fields
and MXF assets inspection.
* DCP Checker : advanced DCP validation tool, including (non exhaustive) :
  * SMPTE / Interop standard convention (naming, ...)
  * Integrity (mime type, size, hash) of all assets
  * Foreign file identification
  * XSD Schema validation for XML files (VolIndex, AssetMap, CPL, PKL)
  * Digital signature validation (CPL, PKL)
  * Intra / Inter Reels integrity and coherence
  * Metadata match between CPL assets and MXF headers
  * Re-link VF / OV
  * Picture tests : FrameRate, BitRate, ...
  * Sound tests : Channels, Sampling, ...
  * Subtitle : Deep inspection of Interop and SMPTE subtitles
* DSM / DCDM Checker : basic image file sequence validation with some
specifics rules.

## Installation

Requirements :
* Python
  * Should work on python 2.7 and python 3.3+
  * Tested on : python 2.7, python 3.6
* Platform
  * Should work on Windows, macOS, Linux
  * Tested on : macOS 10.12

Install asdcplib (macOS / Linux) :
```
wget http://download.cinecert.com/asdcplib/asdcplib-2.7.19.tar.gz
tar xzf asdcplib-2.7.19.tar.gz
cd asdcplib-2.7.19
./configure
make install
```

Install clairmeta :
```
pip install clairmeta
```

## Usage

### General

As a command line tool :
```
python3 -m clairmeta.cli probe -type dcp path/to/dcp
python3 -m clairmeta.cli probe -type dcp path/to/dcp -format json > dcp.json
python3 -m clairmeta.cli probe -type dcp path/to/dcp -format xml > dcp.xml
python3 -m clairmeta.cli check -type dcp path/to/dcp
```

As a python library :
```
from clairmeta import DCP

dcp = DCP("path/to/dcp")
# Parse DCP
dcp.parse()
# Check DCP
status, report = dcp.check()
# Check DCP VF against OV
status, report = dcp.check(ov_path="/path/to/dcp_ov")
```

### Profiles

Check profile allow custom configuration of the DCP check process such as
bypassing some unwanted tests or criticity specification. To implement a
check profile, simply write a JSON file derived from this template (actual
content listed below is for demonstration purpose only) :
* *criticality* key allow custom criticity level specification, check name can
be incomplete to quickly ignore a bunch of tests, *default* is used if no other
match where found.
* *bypass* key allow specific test bypassing, incomplete name are not allowed.
```
{
    "criticality": {
        "default": "ERROR",
        "check_dcnc_": "WARNING",
        "check_cpl_reel_duration_picture_subtitles": "WARNING",
        "check_picture_cpl_avg_bitrate": "WARNING",
        "check_picture_cpl_resolution": "WARNING"
    },
    "bypass": ["check_assets_pkl_hash"],
    "log_level": "INFO"
}
```

Custom profile check :
```
python3 -m clairmeta.cli check -type dcp path/to/dcp -profile path/to/profile.json
```

```
from clairmeta import DCP
from clairmeta.profile include load_profile

dcp = DCP("path/to/dcp")
profile = load_profile("/path/to/profile.json")
status, report = dcp.check(profile=profile)
```



### Logging

All check results are logged to stdout and a rotating file specified in the
settings file.

```
'filename': '~/Library/Logs/clairmeta.log',
'filesize': 1e6,
'filecount': 10,
'level': 'INFO',
```

## Contributing

* To setup your environment, use pipenv :
    ```
    pip install pipenv

    git clone ...
    cd clairmeta
    pipenv install [--two]
    pipenv check
    pipenv shell
    ...
    exit
    ```

* Open a Pull Request

## Changes

The releases changes are available on Github: https://github.com/Ymagis/ClairMeta/releases

## References

The following sources / software were used :
* dcp_inspect : https://github.com/wolfgangw/backports, including the
DCSubtitles XSD Schema
* packageparser : url packageparser
* asdcp-lib : http://www.cinecert.com/asdcplib/
* sox : http://sox.sourceforge.net/
* mediainfo : https://mediaarea.net/
* SMPTE Digital Cinema standards
* Interop Digital Cinema specifications
* Digital Cinema Initiative specifications
* ISDCF Naming Convention : http://isdcf.com/dcnc/
* Texas Instrument Digital Cinema Subtitles specifications

## About

http://www.ymagis.com/
