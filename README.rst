|Build Status| |PyPI version| |Code coverage|

ClairMeta
=========

ClairMeta is a python package for Digital Cinema Package (DCP) probing
and checking.

Features
--------

-  DCP Probe:
    - Metadata extraction of the whole DCP, including all XML fields and MXF
      assets inspection.
-  DCP Checker:
    -  SMPTE / Interop standard convention
    -  Integrity (MIME type, size, hash) of all assets
    -  Foreign file identification
    -  XSD Schema validation for XML files (VOLINDEX, ASSETMAP, CPL, PKL)
    -  Digital signature validation (CPL, PKL)
    -  Intra / Inter Reels integrity and coherence
    -  Metadata match between CPL assets and MXF headers
    -  Re-link VF / OV
    -  Picture tests : FrameRate, BitRate
    -  Sound tests : Channels, Sampling
    -  Subtitle : Deep inspection of Interop and SMPTE subtitles
-  DSM / DCDM Checker:
    - Basic image file sequence validation with some specific rules.

Installation
------------

Requirements:

-  Python: 3.6 or later
-  Platform: Windows (with limitations), macOS, Linux
-  External (non-python) dependencies:
    -  asdcplib
    -  mediainfo (opt)
    -  sox (opt)

Install from PyPI package (this does not install external dependencies):

.. code-block:: bash

    pip install clairmeta

If you need help installing the external dependencies, you can have a look at
our continuous integration system, specifically the **.github** folder.


Usage
-----

General
~~~~~~~

As a command line tool:

.. code-block:: python

    # Probing
    python3 -m clairmeta.cli probe -type dcp path/to/dcp
    python3 -m clairmeta.cli probe -type dcp path/to/dcp -format json > dcp.json
    python3 -m clairmeta.cli probe -type dcp path/to/dcp -format xml > dcp.xml

    # Checking
    python3 -m clairmeta.cli check -type dcp path/to/dcp
    python3 -m clairmeta.cli check -type dcp path/to/dcp -format json > check.json
    python3 -m clairmeta.cli check -type dcp path/to/dcp -format xml > check.xml
    python3 -m clairmeta.cli check -type dcp path/to/dcp -kdm /path/to/kdm -key /path/to/privatekey
    python3 -m clairmeta.cli check -type dcp path/to/dcp -progress

As a python library:

.. code-block:: python

    from clairmeta import DCP

    dcp = DCP("path/to/dcp")
    dcp.parse()
    status, report = dcp.check()

.. code-block:: python

    # Check DCP VF against OV
    status, report = dcp.check(ov_path="/path/to/dcp_ov")

.. code-block:: python

    # DCP check with console progression report
    from clairmeta.utils.file import ConsoleProgress

    status, report = dcp.check(hash_callback=ConsoleProgress())
    # Alternatives
    # - function matching utils.file.ConsoleProgress.__call__ signature
    # - derived class from utils.file.ConsoleProgress


Profiles
~~~~~~~~

Check profile allow custom configuration of the DCP check process such
as bypassing some unwanted tests or error level specification. To
implement a check profile, simply write a JSON file derived from this
template (actual content listed below is for demonstration purposes only):

-  *criticality* key allow custom criteria level specification, check
   name can be incomplete to quickly ignore a bunch of tests, *default* is
   used if no other match where found.
-  *bypass* key allow specific test bypass, incomplete names are not allowed.
-  *allowed_foreign_files* key specify files that are allowed in the DCP
   folder and should not trigger the foreign file check.

.. code-block:: python

    {
        "criticality": {
            "default": "ERROR",
            "check_dcnc_": "WARNING",
            "check_cpl_reel_duration_picture_subtitles": "WARNING",
            "check_picture_cpl_avg_bitrate": "WARNING",
            "check_picture_cpl_resolution": "WARNING"
        },
        "bypass": ["check_assets_pkl_hash"],
        "allowed_foreign_files": ["md5.md5"]
    }

Custom profile check:

.. code-block:: python

    python3 -m clairmeta.cli check -type dcp path/to/dcp -profile path/to/profile.json

.. code-block:: python

    from clairmeta import DCP
    from clairmeta.profile import load_profile

    dcp = DCP("path/to/dcp")
    profile = load_profile("/path/to/profile.json")
    status, report = dcp.check(profile=profile)

Logging
~~~~~~~

Logging is customizable, see the *settings.py* file or below. By default 
ClairMeta logs to stdout and a rotated log file.

.. code-block:: python

    'level': 'INFO'  # Minimum log level
    'enable_console': True  # Enable / Disable stdout logging
    'enable_file': True  # Enable / Disable file logging
    'file_name': '/log/path/clairmeta.log'  # Log file absolute path
    'file_size': 1e6  # Individual log file maximum size
    'file_count': 10  # Number of files to rotate on

Contributing
------------

-  To setup your environment follow these steps:

.. code-block:: bash

   git clone https://github.com/Ymagis/ClairMeta.git
   cd clairmeta
   git clone https://github.com/Ymagis/ClairMeta_Data tests/resources

   pip install pipenv
   pipenv install --dev
   pipenv shell

   # Code... and tests
   pytest --doctest-modules

-  Open a Pull Request
-  Open an Issue

Changes
-------

The release changes are available on Github:
https://github.com/Ymagis/ClairMeta/releases

References
----------

The following sources / software were used:

-  asdcp-lib: http://www.cinecert.com/asdcplib/
-  sox: http://sox.sourceforge.net/
-  mediainfo: https://mediaarea.net/
-  SMPTE Digital Cinema standards: https://www.smpte.org/
-  Interop Digital Cinema specifications: https://cinepedia.com/interop/
-  Digital Cinema Initiative specifications: http://www.dcimovies.com/specification/index.html
-  ISDCF Naming Convention: http://isdcf.com/dcnc/
-  Texas Instrument Digital Cinema Subtitles specifications

About
-----

http://www.ymagis.com/

.. |Build Status| image:: https://travis-ci.org/Ymagis/ClairMeta.svg?branch=1.0.0b1
   :target: https://travis-ci.org/Ymagis/ClairMeta
.. |PyPI version| image:: https://badge.fury.io/py/clairmeta.svg
   :target: https://badge.fury.io/py/clairmeta
.. |Code coverage| image:: https://codecov.io/gh/Ymagis/ClairMeta/branch/develop/graph/badge.svg
  :target: https://codecov.io/gh/Ymagis/ClairMeta