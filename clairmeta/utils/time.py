# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six


def compare_ratio(a, b, precision=0.05):
    """ Compare decimal numbers up to a given precision. """
    return abs(a-b) <= precision


def format_ratio(in_str, separator='/'):
    """ Convert a string representing a rational value to a decimal value.

        Args:
            in_str (str): Input string.
            separator (str): Separator character used to extract numerator and
                denominator, if not found in ``in_str`` whitespace is used.

        Returns:
            An integer or float value with 2 digits precision or ``in_str`` if
            formating has failed.

        >>> format_ratio('48000/1')
        48000
        >>> format_ratio('24000 1000')
        24
        >>> format_ratio('24000 1001')
        23.98
        >>> format_ratio('1,77')
        '1,77'
        >>> format_ratio(1.77)
        1.77

    """
    if not isinstance(in_str, six.string_types):
        return in_str

    try:
        sep = separator if separator in in_str else ' '
        ratio = in_str.split(sep)

        if len(ratio) == 2:
            ratio = round(float(ratio[0]) / float(ratio[1]), 2)
        else:
            ratio = float(ratio[0])

        if ratio.is_integer():
            ratio = int(ratio)

        return ratio
    except ValueError:
        return in_str


def frame_to_tc(edit_count, edit_rate):
    """ Convert sample count to timecode.

        Args:
            edit_count(int): number of samples.
            edit_rate (int): number of sample per second.

        Returns:
            Timecode string (format HH:MM:SS:FF).

        >>> frame_to_tc(48, 24)
        '00:00:02:00'

    """
    if edit_rate != 0 and edit_count != 0:
        s, f = divmod(edit_count, edit_rate)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return "%02d:%02d:%02d:%02d" % (h, m, s, f)
    else:
        return "00:00:00:00"


def tc_to_frame(tc, edit_rate):
    """ Convert timecode to sample count.

        Args:
            tc (str): Timecode string (format HH:MM:SS:FF).
            edit_rate (int): number of samples per second.

        Returns:
            Total samples count.

        >>> tc_to_frame('00:00:02:00', 24)
        48

    """
    hours, minutes, seconds, frames = map(int, tc.split(':'))
    framePerHour = edit_rate * 60 * 60
    framePerMinute = edit_rate * 60
    framePerSecond = edit_rate

    return hours * framePerHour + \
        minutes * framePerMinute + \
        seconds * framePerSecond + frames
