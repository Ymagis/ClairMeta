# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os

from clairmeta.settings import SEQUENCE_SETTINGS
from clairmeta.utils.sys import number_is_close
from clairmeta.utils.file import parse_name


def check_sequence(path, allowed_extensions, ignore_files=None, ignore_dirs=None):
    """ Check image file sequence coherence recursively.

        Args:
            path (str): Base directory path.
            allowed_extensions (dict): Dictionary mapping extensions.
            ignore_files (list): List of files name to ignore.
            ignore_dirs (list): List of directory name to ignore.

        Raises:
            ValueError: If ``path`` is not a valid directory.
            ValueError: If ``path`` is an empty directory.
            ValueError: If ``allowed_extensions`` is not a dictionary.

    """
    if not os.path.isdir(path):
        raise ValueError("Folder not found : {}".format(path))
    if not os.listdir(path):
        raise ValueError("Empty folder")
    if not isinstance(allowed_extensions, dict):
        raise ValueError("Wrong arguments, allowed_extensions must be a dict")

    for dirpath, dirnames, filenames in os.walk(path, topdown=True):
        # Filter out explicitly ignored files
        if ignore_files:
            filenames = [f for f in filenames if f not in ignore_files]
        if ignore_dirs:
            # Why dirnames[:] ? Quote from the documentation :
            #   When topdown is True, the caller can modify the dirnames list
            #   in-place (perhaps using del or slice assignment).
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        # No files in folder, nothing to check..
        if not filenames:
            continue

        # First file in folder is the reference
        check_sequence_folder(dirpath, filenames, allowed_extensions)


def check_sequence_folder(dirpath, filenames, allowed_extensions):
    """ Check image file sequence coherence.

        This function checks :
         - Image extension and Mime type is authorized
         - No jump (missing frame) are found in the whole sequence
         - All images must have the same file name (excluding index)
         - All images must have the same extension and Mime type
         - All images must have the same size (we work on uncompressed files
           only)

        Args:
            dirpath (str): Directory path.
            filenames (list): List of files to check in ``dirpath``.
            allowed_extensions (dict): Dictionary mapping extensions.

        Raises:
            ValueError: If image file sequence check failed.

    """
    settings = SEQUENCE_SETTINGS['ALL']
    size_rtol = settings['size_diff_tol'] / 1e2

    # First file in folder is the reference
    fileref = filenames[0]
    fullpath_ref = os.path.join(dirpath, fileref)
    filename, idx = parse_name(fileref)
    filesize = os.path.getsize(fullpath_ref)
    extension = os.path.splitext(fileref)[-1]
    sequence_idx = [idx]

    # Check that this reference is conform
    if extension not in allowed_extensions:
        raise ValueError('extension {} not authorized'.format(extension))

    # Then check that all subsequent files are identical
    for f in filenames[1:]:
        fullpath = os.path.join(dirpath, f)
        current_ext = os.path.splitext(f)[-1]
        current_filename, current_idx = parse_name(f)
        current_filesize = os.path.getsize(fullpath)
        sequence_idx.append(current_idx)

        if current_filename != filename:
            raise ValueError('Filename difference, {} but expected {}'
                             .format(current_filename, filename))
        if current_ext != extension:
            raise ValueError('File extension difference, {} but expected {}'
                             .format(current_filename, extension))
        if not number_is_close(current_filesize, filesize,  rtol=size_rtol):
            raise ValueError(
                '{} : file size difference got {} but expected {}'
                ' - tolerance of {}%'.format(
                    current_filename, current_filesize,
                    filesize, settings['size_diff_tol']))

    # Check for jump in sequence (ie. missing frame(s))
    sequence_idx.sort()
    for idx, fno in enumerate(sequence_idx, sequence_idx[0]):
        if idx != fno:
            raise ValueError(
                'File sequence jump found, file {} not found'.format(idx))
