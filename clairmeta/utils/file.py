# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

from __future__ import division
from __future__ import absolute_import
import os
import sys
import contextlib
import shutil
import tempfile
import base64
import hashlib
import time
import re


def folder_size(folder):
    """ Compute total size of a folder.

        Args:
            folder (str): Folder path.

        Returns:
            Total folder size in bytes.

    """
    size = 0

    for dirpath, dirnames, filenames in os.walk(folder):
        for f in filenames:
            filename = os.path.join(dirpath, f)
            size += os.path.getsize(filename)

    return size


def human_size(nbytes):
    """ Convert size in bytes to a human readable representation.

        Args:
            nbytes (int): Size in bytes.

        Returns:
            Human friendly string representation of ``nbytes``, unit is power
            of 1024.

        >>> human_size(65425721)
        '62.39 MiB'
        >>> human_size(0)
        '0.00 B'

    """
    for unit in ['', 'ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(nbytes) < 1024.0:
            return "{:.2f} {}B".format(nbytes, unit)
        nbytes /= 1024.0
    return "{:.2f} {}B".format(nbytes, 'Yi')


@contextlib.contextmanager
def temporary_file(prefix="tmp", suffix=""):
    """ Context managed temporary file.

        Yields:
            str: Absolute path of the temporary file.

    """
    try:
        _, filepath = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        yield filepath
    finally:
        try:
            os.remove(filepath)
        except PermissionError:
            pass


@contextlib.contextmanager
def temporary_dir():
    """ Context managed temporary directory.

        Yields:
            str: Absolute path of the temporary directory.

    """
    try:
        dirpath = tempfile.mkdtemp()
        yield dirpath
    finally:
        shutil.rmtree(dirpath)


class ConsoleProgress(object):

    def __init__(self):
        """ ConsoleProgress constructor. """
        self._total_size = None

        self.total_processed = 0
        self.total_elapsed = 0

    def __call__(self, file_path, file_processed, file_size, file_elapsed):
        """ Callback for shaone_b64.

            Args:
                file_path (str): File absolute path.
                file_processed (int): Bytes processed for the current file
                file_size (int): Size of the current file
                file_elapsed (float): Seconds elapsed for the current file

        """
        col_width = 15
        complete_col_width = 60
        # Avoid division by zero if time resolution is too small
        file_elapsed = max(sys.float_info.epsilon, file_elapsed)

        if file_processed != file_size:
            elapsed = self.total_elapsed + file_elapsed
            processed = self.total_processed + file_processed

            file_progress = min(1, (file_processed / file_size))
            file_progress_size = int(file_progress * col_width)
            file_bar_size = col_width - file_progress_size

            total_progress = min(1, (processed / self._total_size))
            total_progress_size = int(total_progress * col_width)
            total_bar_size = col_width - total_progress_size

            if processed > 0:
                eta_sec = (self._total_size - processed) / (processed / elapsed)
            else:
                eta_sec = 0

            eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_sec))

            sys.stdout.write("ETA {} [{}] {:.2f}% - File [{}] {:.2f}% - {}\r".format(
                eta_str,
                "{}{}".format('=' * total_progress_size, ' ' * total_bar_size),
                total_progress * 100.0,
                "{}{}".format('=' * file_progress_size, ' ' * file_bar_size),
                file_progress * 100.0,
                os.path.basename(file_path)))
            sys.stdout.flush()
        else:
            file_size = os.path.getsize(file_path)

            speed_report = "{} in {:.2f} sec (at {:.2f} MBytes/s)".format(
                human_size(file_size), file_elapsed, (file_size / 1e6) / file_elapsed)

            sys.stdout.write("[  {}] 100.00% - {}\r".format(
                speed_report.ljust(complete_col_width - 2),
                os.path.basename(file_path)))
            sys.stdout.write("\n")

            self.total_processed += file_size
            self.total_elapsed += file_elapsed


def shaone_b64(file_path, callback=None):
    """ Compute file hash using sha1 algorithm.

        Args:
            file_path (str): File absolute path.
            callback (func, optional): Callback function, see
              ``console_progress_bar`` for an example implementation.

        Returns:
            String representation of ``file`` sha1 (encoded in base 64).

        Raises:
            ValueError: If ``file_path`` is not a valid file.

    """
    if not os.path.isfile(file_path):
        raise ValueError("{} file not found".format(file_path))

    BUF_SIZE = 65536
    file_size = os.path.getsize(file_path)
    run_size = 0
    sha1 = hashlib.sha1()
    start = time.time()
    last_cb_time = start

    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break

            run_size += len(data)
            sha1.update(data)

            time_cb = time.time()
            call_cb = time_cb - last_cb_time > 0.2
            complete = run_size == file_size
            if callback and (call_cb or complete):
                last_cb_time = time_cb
                callback(file_path, run_size, file_size, time_cb - start)

    # Encode base64 and remove carriage return
    sha1b64 = base64.b64encode(sha1.digest())
    return sha1b64.decode("utf-8")


IMAGENO_REGEX = re.compile(r'[\._]?(?P<Index>\d+)(?=[\._])')


def parse_name(filename, regex=IMAGENO_REGEX):
    """ Extract image name and index from filename.

        Args:
            filename (str): Image file name.
            regex (RegexObject): Extraction rule.

        Returns:
            Tuple (name, index) extracted from filename.

        Raises:
            ValueError: If image index not found in ``filename``.

        >>> parse_name('myfile.0001.tiff')
        ('myfile', 1)
        >>> parse_name('myfile_0001.tiff')
        ('myfile', 1)
        >>> parse_name('myfile.123.0001.tiff')
        ('myfile.123', 1)
        >>> parse_name('00123060.tiff')
        ('', 123060)
        >>> parse_name('123060.tiff')
        ('', 123060)
        >>> parse_name('myfile.tiff')
        Traceback (most recent call last):
        ...
        ValueError: myfile.tiff : image index not found
        >>> parse_name('myfile.abcdef.tiff')
        Traceback (most recent call last):
        ...
        ValueError: myfile.abcdef.tiff : image index not found

    """
    m = list(regex.finditer(filename))
    if m == []:
        raise ValueError('{} : image index not found'.format(filename))

    lastm = m[-1]
    name = filename[:lastm.start()]
    index = lastm.groupdict()['Index']
    return name, int(index)
