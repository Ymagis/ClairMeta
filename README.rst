|Build Status| |PyPI version|

Clairmeta
=========

Clairmeta is a python package for Digital Cinema Package (DCP) probing
and checking.

This project status is **Beta**, the following needs to be done for the
release :

-  Large scale tests on lots of DCPs (including D-Box, DVIs, OCAP, CCAP, ...)

Features
--------

-  DCP Probe : metadata extraction of the whole DCP, including all XML
   fields and MXF assets inspection.
-  DCP Checker : advanced DCP validation tool, including (non
   exhaustive) :

   -  SMPTE / Interop standard convention (naming, …)
   -  Integrity (MIME type, size, hash) of all assets
   -  Foreign file identification
   -  XSD Schema validation for XML files (VOLINDEX, ASSETMAP, CPL, PKL)
   -  Digital signature validation (CPL, PKL)
   -  Intra / Inter Reels integrity and coherence
   -  Metadata match between CPL assets and MXF headers
   -  Re-link VF / OV
   -  Picture tests : FrameRate, BitRate, …
   -  Sound tests : Channels, Sampling, …
   -  Subtitle : Deep inspection of Interop and SMPTE subtitles

-  DSM / DCDM Checker : basic image file sequence validation with some
   specific rules.

Installation
------------

Requirements :

-  Python :

   -  Should work on python 2.7 and python 3.3+
   -  Tested on : python 2.7, python 3.6

-  Platform :

   -  Should work on Windows, macOS, Linux
   -  Tested on : macOS 10.12

-  External (non-python) dependencies :

   -  libmagic
   -  asdcplib
   -  mediainfo (opt)
   -  sox (opt)

Install from PyPI package (reminder : this does not install external dependencies):

::

    pip install clairmeta

Install from Debian package (all requirements will be automatically installed):

::

    # Optional : add Bintray public key
    apt-get install dirmngr
    gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv 379CE192D401AB61
    gpg --export --armor 379CE192D401AB61 | apt-key add -

    # Add Clairmeta repository to apt sources
    # Replace <distro> appropriately
    # Ubuntu 14.04 : use trusty
    # Ubuntu 16.04 : use xenial
    # Ubuntu 17.04 : use artful
    echo "deb https://dl.bintray.com/ymagis/Clairmeta <distro> main" | sudo tee /etc/apt/sources.list.d/clairmeta.list

    sudo apt-get update
    sudo apt-get install python3-clairmeta

Usage
-----

General
~~~~~~~

As a command line tool :

::

    python3 -m clairmeta.cli probe -type dcp path/to/dcp
    python3 -m clairmeta.cli probe -type dcp path/to/dcp -format json > dcp.json
    python3 -m clairmeta.cli probe -type dcp path/to/dcp -format xml > dcp.xml
    python3 -m clairmeta.cli check -type dcp path/to/dcp

As a python library :

::

    from clairmeta import DCP

    dcp = DCP("path/to/dcp")
    # Parse DCP
    dcp.parse()
    # Check DCP
    status, report = dcp.check()
    # Check DCP VF against OV
    status, report = dcp.check(ov_path="/path/to/dcp_ov")

Profiles
~~~~~~~~

Check profile allow custom configuration of the DCP check process such
as bypassing some unwanted tests or criteria specification. To
implement a check profile, simply write a JSON file derived from this
template (actual content listed below is for demonstration purposes only) :

-  *criticality* key allow custom criteria level specification, check
   name can be incomplete to quickly ignore a bunch of tests, *default* is
   used if no other match where found.
-  *bypass* key allow specific test
   bypassing, incomplete names are not allowed.

::

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

Custom profile check :

::

    python3 -m clairmeta.cli check -type dcp path/to/dcp -profile path/to/profile.json

::

    from clairmeta import DCP
    from clairmeta.profile include load_profile

    dcp = DCP("path/to/dcp")
    profile = load_profile("/path/to/profile.json")
    status, report = dcp.check(profile=profile)

Logging
~~~~~~~

Logging is customizable, see settings.py file or below. By default Clairmeta
logs to stdout and a rotated log file.

::

    'level': 'INFO'  # Minimum log level
    'enable_console': True  # Enable / Disable stdout logging
    'enable_file': True  # Enable / Disable file logging
    'file_name': '/log/path/clairmeta.log'  # Log file absolute path
    'file_size': 1e6  # Individual log file maximum size
    'file_count': 10  # Number of files to rotate on

Contributing
------------

-  To setup your environment, use pipenv :

::

   pip install pipenv
   git clone https://github.com/Ymagis/ClairMeta.git
   cd clairmeta
   pipenv install --dev [–two]
   pipenv check
   # Enter virtual environment
   pipenv shell
   # Code...
   # Run tests
   nosetests --nocapture --with-doctest --doctest-options=+ELLIPSIS --with-coverage --cover-package=clairmeta
   # Leave virtual environment
   exit

-  Open a Pull Request
-  Open an Issue

Changes
-------

The release changes are available on Github:
https://github.com/Ymagis/ClairMeta/releases

References
----------

The following sources / software were used :

-  asdcp-lib : http://www.cinecert.com/asdcplib/
-  sox : http://sox.sourceforge.net/
-  mediainfo : https://mediaarea.net/
-  SMPTE Digital Cinema standards
-  Interop Digital Cinema specifications
-  Digital Cinema Initiative specifications
-  ISDCF Naming Convention : http://isdcf.com/dcnc/
-  Texas Instrument Digital Cinema Subtitles specifications

About
-----

http://www.ymagis.com/

.. |Build Status| image:: https://travis-ci.org/Ymagis/ClairMeta.svg?branch=1.0.0b1
   :target: https://travis-ci.org/Ymagis/ClairMeta
.. |PyPI version| image:: https://badge.fury.io/py/clairmeta.svg
   :target: https://badge.fury.io/py/clairmeta
