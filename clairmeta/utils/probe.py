# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import six
import subprocess
import xmltodict
import magic
import bisect
import contextlib
from shutilwhich import which

from clairmeta.utils.sys import (transform_keys_dict, try_convert_number,
                                 camelize)
from clairmeta.utils.file import temporary_dir
from clairmeta.utils.time import format_ratio
from clairmeta.settings import DCP_SETTINGS


def check_command(name):
    """ Check command is available on the system.

        Args:
            name (str): Command name.

        Returns:
            True if command ``name`` was found on the system.

    """
    return which(name) is not None


def execute_command(cmd_args):
    """ Execute command and returns the result.

        Args:
            cmd_args (list): Command argument list.

        Returns:
            Tuple (stdout, stderr).

        Raises:
            ValueError: If ``cmd_args`` is empty.
            ValueError: In case of non-zero return code.

    """
    if not cmd_args:
        return ValueError("Invalid arguments")

    p = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    if p.returncode:
        raise ValueError("Error calling process : {}".format(cmd_args[0]))

    return p.communicate()


def probe_mxf(path, stereoscopic=False):
    """ Probe MXF asset using asdcp-info.

        Args:
            path (str): MXF file path.
            stereoscopic (boolean, optional): Must be True for Stereoscopic
                (3D) MXF picture asset.

        Returns:
            Dictionary containing MXF metadata as parsed by asdcp-info.

        Raises:
            ValueError: If ``path`` is not a valid file.
            ValueError: If asdcp-info command is not available.

    """
    if not os.path.isfile(path):
        raise ValueError("File not found : {}".format(path))
    if not check_command('asdcp-info'):
        raise ValueError("asdcp-info not available")

    # We don't want asdcp-info to report error in case of bitrate exceeded
    # We do our own check in Clairmeta.
    bitrate_threshold = 1e6
    # Prepare command line...
    asdcp_args = [
        'asdcp-info',
        '-v',  # Verbose flag
        '-i',  # Show identity info
        '-d',  # Show essence descriptor info
        '-r',  # Show bit-rate (Mb/s)
        '-t', str(bitrate_threshold),
        path]

    if stereoscopic:
        # Force stereoscopic interpretation of a JP2K file
        asdcp_args.append('-3')

    # Execute asdcp-info and parse results
    out, err = execute_command(asdcp_args)
    if err:
        raise ValueError(err)

    metadata = {}
    out = out.decode('UTF-8').split('\n')
    for line in out:
        if ':' not in line:
            continue

        k, v = line.replace(' ', '').split(':', 1)
        metadata[k] = v

    return probe_mxf_clean(metadata)


def probe_mxf_clean(in_meta):
    """ Format asdcp-info probe result.

        Args:
            in_meta (dict): MXF probe metadata returned by asdcp-info.

        Returns:
            Dictionary containing MXF metadata as parsed by asdcp-info.

    """
    out_meta = {}

    # Generic cleanup
    for k, v in six.iteritems(in_meta):
        # Remove BitRate unit suffix
        if v.endswith('Mb/s'):
            v = v[:-4]

        # Try to transform ratios string
        try:
            if '/' in v:
                v = format_ratio(v)
        except ValueError:
            pass

        # Try to convert to number
        v = try_convert_number(v)

        # Use boolean instead of string
        if v == 'Yes':
            v = True
        if v == 'No':
            v = False

        # Remove empty value key
        if v == '':
            continue

        out_meta[k] = v

    # Specific helper keys
    is_picture = 'AspectRatio' in out_meta
    if is_picture:
        out_meta['Resolution'] = "{}x{}".format(
            out_meta['StoredWidth'],
            out_meta['StoredHeight'])

    is_sound = 'AudioSamplingRate' in out_meta
    if is_sound:
        config_map = DCP_SETTINGS['sound']['configuration_channels']
        mxf_format = out_meta['ChannelFormat']
        if mxf_format in config_map:
            label, _, _ = config_map[mxf_format]
            out_meta['ChannelConfiguration'] = label

    return out_meta


@contextlib.contextmanager
def unwrap_mxf(path, prefix=None, args=[]):
    """ Temporarily unwrap MXF asset in a temporary folder using asdcp-unwrap.

        Args:
            path (str): MXF file path.
            prefix (str, optional): Optional prefix for unwraped file names.
            args (list): Optional arguments to asdcp-unwrap.

        Yields:
            str: Path to the temporary folder containg unwraped resources.

        Raises:
            ValueError: If ``path`` is not a valid file.
            ValueError: If asdcp-unwrap command is not available.

    """
    if not os.path.isfile(path):
        raise ValueError("File not found : {}".format(path))
    if not check_command('asdcp-unwrap'):
        raise ValueError("asdcp-unwrap not available")

    with temporary_dir() as tmp:

        if prefix:
            unwrap_prefix = os.path.join(tmp, prefix)
        else:
            folder = os.path.splitext(os.path.basename(path))[0]
            unwrap_prefix = os.path.join(tmp, folder)

        unwrap_args = [
            'asdcp-unwrap',
            path,
            unwrap_prefix
        ]
        unwrap_args += args

        execute_command(unwrap_args)
        yield tmp


def stat_mxf_audio(path, channels, entry_point, duration):
    """ Gather audio statistics from MXF audio file using asdcp-unwrap and sox.

        Args:
            path (str): MXF file path.
            channels (int): Number of audio channel.
            entry_point (int): Starting frame number from audio track.
            duration (int): Number of frames to process from audio track.

        Returns:
            Dictionary containing global statistics for each audio channels.

        Raises:
            ValueError: If ``path`` is not a valid file.
            ValueError: If sox command is not available.

    """
    if not os.path.isfile(path):
        raise ValueError("File not found : {}".format(path))
    if not check_command('sox'):
        raise ValueError("sox not available")

    args = [
        '-1',  # Split Wave essence to mono WAV files during extract
        '-f', str(entry_point),  # Starting frame number
        '-d', str(duration),  # Number of frames to process
    ]

    prefix = 'wav_track'

    with unwrap_mxf(path, prefix=prefix, args=args) as folder:

        wav_list = [
            "{}_{:02d}.wav".format(os.path.join(folder, prefix), c)
            for c in range(1, channels+1)]

        sox_args = [
            'sox',
            '-t', 'wavpcm',  # File type of audio
            '-M'] + wav_list + [  # Merge multiple input files
            '-n', 'stats'  # Use the `null' file handler
        ]

        out, err = execute_command(sox_args)
        err = err.decode('UTF-8')

    statistics = {
        'DC offset': [],
        'Min level': [],
        'Max level': [],
        'Pk lev dB': [],
        'RMS lev dB': [],
        'RMS Pk dB': [],
        'RMS Tr dB': [],
        'Crest factor': [],
        'Flat factor': [],
        'Pk count': [],
        'Bit-depth': [],
        'Num samples': [],
        'Length s': [],
        'Scale max': [],
        'Window s': [],
    }

    for line in err.split('\n'):
        for stat in statistics:
            if line.startswith(stat):
                values = line.replace(stat, '').split()
                values = [v.replace('-inf', '.') for v in values]
                statistics[stat] = values

    return {
        'rms_lvl_db': "|".join(statistics['RMS lev dB'][1:]),
        'pk_lvl_db': "|".join(statistics['Pk lev dB'][1:]),
        'rms_lvl_db_overall': statistics['RMS lev dB'][0],
        'pk_lvl_db_overall': statistics['Pk lev dB'][0]
    }


def probe_mediainfo(path):
    """ Probe video asset using mediainfo.

        Args:
            path (str): Video file path.

        Returns:
            Dictionary containing file metadata as parsed by mediainfo.

        Raises:
            ValueError: If ``path`` is not a valid file.
            ValueError: If mediainfo command is not available.

    """
    if not os.path.isfile(path):
        raise ValueError("File not found : {}".format(path))
    if not check_command('mediainfo'):
        raise ValueError("mediainfo not available")

    mediainfo_args = [
        'mediainfo',
        '--Output=XML',
        path
    ]

    out, err = execute_command(mediainfo_args)

    probe = xmltodict.parse(
        out,
        force_list=('track',),
        process_namespaces=False,
        dict_constructor=dict)

    metadata = {}

    try:
        # Mediainfo < 2.0
        if 'Mediainfo' in probe:
            track_list = probe['Mediainfo']['File']['track']
        else:
            track_list = probe['MediaInfo']['media']['track']

        for track in track_list:
            track_type = track.pop('@type')
            track = transform_keys_dict(track, camelize)

            if track_type == 'General':
                metadata = track
            else:
                metadata['Probe' + track_type] = track
    except:
        raise ValueError('Cannot read file metadata')

    return {
        'Path': path,
        'Type': 'MEDIA',
        'Probe': metadata
    }


def probe_folder(path):
    """ Probe a folder containing image file sequence using mediainfo.

        This will parse all the file in ``path`` (sub folder not considered)
        and construct a dictionary where metadata are grouped by file
        extension.

        Args:
            path (str): Folder path.

        Returns:
            Dictionary containing file sequences metadata.

        Raises:
            ValueError: If ``path`` is not a valid directory.

    """
    if not os.path.isdir(path):
        raise ValueError("Directory not found : {}".format(path))

    metadata = {}

    for dirpath, dirnames, filenames in os.walk(path):
        # Skip folder with no files
        if not filenames:
            continue

        metadata[dirpath] = {}
        metadir = metadata[dirpath]

        for f in filenames:
            fullpath = os.path.join(dirpath, f)
            extension = os.path.splitext(f)[-1][1:]
            description = magic.from_file(fullpath)

            if extension in metadir:
                metadir[extension]['Count'] += 1
                bisect.insort(metadir[extension]['Paths'], f)
            else:
                probe = probe_mediainfo(fullpath)['Probe']
                probe.pop('CompleteName', None)

                metadesc = metadir[extension] = {}
                metadesc['Folder'] = dirpath
                metadesc['Paths'] = [f]
                metadesc['Count'] = 1
                metadesc['Description'] = description
                metadesc['Probe'] = probe

    # Remove base folder path from keys
    rootpath = os.path.dirname(path) + '/'
    clean_metadata = {}
    for key, val in six.iteritems(metadata):
        newkey = key.replace(rootpath, '')
        clean_metadata[newkey] = val

    return clean_metadata
