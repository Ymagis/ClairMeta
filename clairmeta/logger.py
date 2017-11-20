# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import logging
from logging.handlers import RotatingFileHandler

from clairmeta.settings import LOG_SETTINGS


def init_log():
    """ Initialize logging utilities.

        Returns:
            logging.Logger object with appropriate handler initialized.

    """
    log = logging.getLogger('Clairmeta')

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if LOG_SETTINGS['enable_console']:
        init_console(log, formatter)
    if LOG_SETTINGS['enable_file']:
        init_file(log, formatter)

    return log


def init_console(log, formatter):
    """ Initialize console stream handler. """
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)


def init_file(log, formatter):
    """ Initialize file handler. """
    try:
        log_dir = os.path.expanduser(LOG_SETTINGS['file_name'])
        log_file = log_dir
        log_dir = os.path.dirname(log_dir)
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_SETTINGS['file_size'],
            backupCount=LOG_SETTINGS['file_count'])
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)
    except Exception as e:
        log.error("Could not intialize log file : {}".format(str(e)))


def enable_log():
    logging.disable(logging.NOTSET)


def disable_log():
    logging.disable(logging.CRITICAL)


def get_log():
    """ Returns package logging.Logger global object. """
    return cm_log


def set_level(level):
    """ Set logging threshold level.

        Args:
            level (str): Minimum level for a log event to be recorded. List
             include : CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET.

    """
    cm_log.setLevel(level)
    [h.setLevel(level) for h in cm_log.handlers]


cm_log = init_log()
set_level(LOG_SETTINGS['level'])
