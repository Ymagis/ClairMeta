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
        handle, filepath = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        yield filepath
    finally:
        os.remove(filepath)


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


def console_progress_bar(file_path, progress, elapsed, done):
    """ Console Progress Bar callback for shaone_b64.

        Args:
            file_path (str): File absolute path.
            progress (float): Progression, interval 0..1.
            elapsed (float): Seconds elapsed.
            done (boolean): Completion status.

    """
    col_width = 50

    if not done:
        progress_size = int(progress * col_width)
        eta_size = col_width - progress_size

        sys.stdout.write("[{}] {:.2f}% - {}\r".format(
            "{}{}".format('=' * progress_size, ' ' * eta_size),
            progress * 100.,
            os.path.basename(file_path)))
        sys.stdout.flush()
    else:
        file_size = os.path.getsize(file_path)
        speed_report = "{} in {:.2f} sec (at {:.2f} MBytes/s)".format(
            human_size(file_size), elapsed, (file_size / 1e6) / elapsed)

        sys.stdout.write("[  {}] 100.00% - {}\r".format(
            speed_report.ljust(col_width - 2),
            os.path.basename(file_path)))
        sys.stdout.write("\n")


def shaone_b64(file_path, callback=None):
    """ Compute file hash using sha1 algorithm.

        Args:
            file_path (str): File absolute path.
            callback (func): Callback function, see ``console_progress_bar``
            for an example implementation.

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

    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break

            run_size += BUF_SIZE
            sha1.update(data)
            progress = min(1, (run_size / file_size))

            if callback:
                callback(file_path, progress, time.time() - start, False)

    if callback:
        callback(file_path, progress, time.time() - start, True)

    # Encode base64 and remove carriage return
    sha1b64 = base64.b64encode(sha1.digest())
    return sha1b64.decode("utf-8")
