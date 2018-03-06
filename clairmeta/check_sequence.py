# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import re
import magic


IMAGENO_REGEX = re.compile(r'[\._](\d+)(?=[\._])')


def check_sequence(path, allowed_extensions, ignore_files=[], ignore_dirs=[]):
    """ Check image file sequence coherence recursively.

        Args:
            path (str): Base directory path.
            allowed_extensions (dict): Dictionary mapping extensions with file
                descriptions as returned by magic.
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
            allowed_extensions (dict): Dictionary mapping extensions with file
                descriptions as returned by magic.

        Raises:
            ValueError: If image file sequence check failed.

    """
    # First file in folder is the reference
    fileref = filenames[0]
    fullpath_ref = os.path.join(dirpath, fileref)
    filename, idx = parse_name(fileref)
    filesize = os.path.getsize(fullpath_ref)
    extension = os.path.splitext(fileref)[-1]
    description = magic.from_file(fullpath_ref).split(',')[0]
    sequence_idx = [idx]

    # Check that this reference is conform
    if extension not in allowed_extensions:
        raise ValueError('extension {} not authorized'.format(extension))
    if description != allowed_extensions[extension]:
        raise ValueError('wrong file format : {} should not be {}'
                         .format(fileref, description))

    # Then check that all subsequent files are identical
    for f in filenames[1:]:
        fullpath = os.path.join(dirpath, f)
        current_ext = os.path.splitext(f)[-1]
        current_filename, current_idx = parse_name(f)
        current_filesize = os.path.getsize(fullpath)
        current_description = magic.from_file(fullpath).split(',')[0]
        sequence_idx.append(current_idx)

        if current_filename != filename:
            raise ValueError('{} : filename difference, expected {}'
                             .format(current_filename, filename))
        if current_ext != extension:
            raise ValueError('{} : file extension difference, expected {}'
                             .format(current_filename, extension))
        if current_description != description:
            raise ValueError(
                '{} : file description difference got {} but expected {}'
                .format(current_filename, current_description, description))
        if current_filesize != filesize:
            raise ValueError(
                '{} : file size difference got {} but expected {}'
                .format(current_filename, current_filesize, filesize))

    # Check for jump in sequence (ie. missing frame(s))
    sequence_idx.sort()
    for idx, fno in enumerate(sequence_idx, sequence_idx[0]):
        if idx != fno:
            raise ValueError(
                'file sequence jump found, file {} not found'.format(idx))


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
        ('myfile.tiff', 1)
        >>> parse_name('myfile_0001.tiff')
        ('myfile.tiff', 1)
        >>> parse_name('myfile.123.0001.tiff')
        ('myfile.123.tiff', 1)
        >>> parse_name('myfile.tiff')
        Traceback (most recent call last):
        ...
        ValueError: myfile.tiff : image index not found

    """
    m = list(regex.finditer(filename))
    if m == []:
        raise ValueError('{} : image index not found'.format(filename))

    lastm = m[::-1][0]
    name = filename[:lastm.start()] + filename[lastm.end():]
    index = filename[lastm.start()+1:lastm.end()]
    return name, int(index)
