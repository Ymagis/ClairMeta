#!/usr/bin/env python3
# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

from __future__ import print_function
import os
import argparse
import sys
import json
import dicttoxml
import pprint

from clairmeta import DCP, DSM, DCDM
from clairmeta.logger import disable_log
from clairmeta.info import __version__
from clairmeta.profile import load_profile, DCP_CHECK_PROFILE
from clairmeta.utils.xml import prettyprint_xml


package_type_map = {
    'dcp': DCP,
    'dcdm': DCDM,
    'dsm': DSM,
}


def cli_check(args):
    try:
        if args.type == 'dcp':
            check_profile = DCP_CHECK_PROFILE

            if args.profile:
                path = os.path.abspath(args.profile)
                check_profile = load_profile(path)
            if args.log:
                check_profile['log_level'] = args.log

            status, _ = DCP(args.path).check(
                profile=check_profile, ov_path=args.ov)

        else:
            obj_type = package_type_map[args.type]
            status = obj_type(args.path).check()

        return status
    except Exception as e:
        print('Error : ' + str(e), file=sys.stderr)


def cli_probe(args):
    try:
        disable_log()
        obj_type = package_type_map[args.type]
        res = obj_type(args.path).parse()

        if args.format == "dict":
            return pprint.pformat(res)
        elif args.format == "json":
            return json.dumps(
                res, sort_keys=True, indent=2, separators=(',', ': '))
        elif args.format == "xml":
            xml_str = dicttoxml.dicttoxml(
                res, custom_root='ClairmetaProbe', ids=False, attr_type=False)
            return prettyprint_xml(xml_str)
    except Exception as e:
        print('Error : ' + str(e), file=sys.stderr)


def get_parser():
    global_parser = argparse.ArgumentParser(
        description='Clairmeta Command Line Interface {}'
        .format(__version__))
    subparsers = global_parser.add_subparsers()

    # DCP
    parser = subparsers.add_parser(
        'check', help="Package validation")
    parser.add_argument('path', help="absolute package path")
    parser.add_argument('-log', default=None, help="logging level [dcp]")
    parser.add_argument('-profile', default=None, help="json profile [dcp]")
    parser.add_argument('-ov', default=None, help="ov package path [dcp]")
    parser.add_argument(
        '-type', choices=package_type_map.keys(),
        required=True, help="package type")
    parser.set_defaults(func=cli_check)

    parser = subparsers.add_parser('probe', help="Package metadata extraction")
    parser.add_argument('path', help="absolute package path")
    parser.add_argument(
        '-format', default="dict", choices=['dict', 'xml', 'json'],
        help="output format")
    parser.add_argument(
        '-type', choices=package_type_map.keys(),
        required=True, help="package type")
    parser.set_defaults(func=cli_probe)

    return global_parser


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
    else:
        print(args.func(args))
