"""
Implement DCP copy and subsequent check.

Require python 3.8 for shutil.copytree() dirs_exist_ok kwargs.
Require python 3.2 for concurrent.futures.ThreadPoolExecutor.
"""

import argparse
import concurrent.futures
import time
import shutil
import sys

import clairmeta
from clairmeta import DCP
from clairmeta.logger import get_log
from clairmeta.utils.file import ConsoleProgress, folder_size


def cli_copy(args):
    dcp = DCP(args.source)
    dcp_size = dcp.size

    try:

        log = get_log()
        log.info("Copy {} to {}".format(args.source, args.dest))

        start = time.time()
        progress = ConsoleProgress()
        progress._total_size = dcp_size

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                shutil.copytree,
                args.source,
                args.dest,
                dirs_exist_ok=args.overwrite
            )

            while future.running():
                copy_size = folder_size(args.dest)
                elapsed = time.time() - start
                progress(args.source, copy_size, dcp_size, elapsed)
                time.sleep(1.0)

            future.result()

        progress(args.source, dcp_size, dcp_size, elapsed)
        log.info("Total time : {:.2f} sec".format(time.time() - start))

        DCP(args.dest)
        status, _ = dcp.check(hash_callback=ConsoleProgress())

        return status

    except Exception as e:
        print(str(e))
        return False


def get_parser():
    parser = argparse.ArgumentParser(
        description='Clairmeta Copy Sample Utility {}'
        .format(clairmeta.__version__))

    parser.add_argument('source', help="absolute source package path")
    parser.add_argument('dest', help="absolute destination copy path")
    parser.add_argument('-progress', action='store_true', help="progress bar")
    parser.add_argument('-overwrite', action='store_true', help="overwrite dst")
    parser.set_defaults(func=cli_copy)

    return parser


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
    else:
        status = args.func(args)
        sys.exit(0 if status else 1)