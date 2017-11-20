# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

from clairmeta.info import __license__, __author__, __version__
from clairmeta.dcp import DCP
from clairmeta.dsm import DSM
from clairmeta.dcdm import DCDM
from clairmeta.logger import get_log
from clairmeta.utils.probe import check_command
from clairmeta.dcp_parse import (volindex_parse, assetmap_parse, pkl_parse,
                                 cpl_parse, kdm_parse)


__all__ = ['DCP', 'DCDM', 'DSM']
__license__ = __license__
__author__ = __author__
__version__ = __version__
__deps__ = ['asdcp-info', 'asdcp-unwrap', 'sox']

for d in __deps__:
    if not check_command(d):
        get_log().warning("Missing dependency : {}".format(d))
