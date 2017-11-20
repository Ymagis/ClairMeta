# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import six
import importlib

from clairmeta.settings import DCP_CHECK_SETTINGS
from clairmeta.logger import set_level
from clairmeta.dcp_utils import list_cpl_assets, cpl_probe_asset
from clairmeta.dcp_check_base import CheckerBase, CheckException


class DCPChecker(CheckerBase):
    """ Digital Cinema Package checker. """

    def __init__(self, dcp, profile, ov_path=None):
        """ DCPChecker constructor.

            Args:
                dcp (clairmeta.DCP): DCP object.
                profile (dict): Checker profile.
                ov_path (str, optional): Absolute path of OriginalVersion DCP.

        """
        super(DCPChecker, self).__init__(dcp, profile)

        set_level(profile['log_level'])
        self.ov_path = ov_path
        self.run_checks()
        self.make_report()
        self.dump_report()

    def run_checks(self):
        """ Execute all checks. """
        self.check_log.info("Checking DCP : {}".format(self.dcp.path))

        # Run own tests
        dcp_checks = self.find_check('dcp')
        [self.run_check(c) for c in dcp_checks]

        # Run external modules tests
        prefix = DCP_CHECK_SETTINGS['module_prefix']
        for module in DCP_CHECK_SETTINGS['modules']:
            try:
                module_path = 'clairmeta.' + prefix + module
                module_vol = importlib.import_module(module_path)
                checker = module_vol.Checker(self.dcp, self.check_profile)
                self.check_executions += checker.run_checks()
            except (ImportError, Exception) as e:
                self.check_log.critical("Import error {} : {}".format(
                    module_path, str(e)))

    def check_dcp_empty_dir(self):
        list_empty_dir = []
        for dirpath, dirnames, filenames in os.walk(self.dcp.path):
            for d in dirnames:
                fullpath = os.path.join(dirpath, d)
                if not os.listdir(fullpath):
                    list_empty_dir.append(fullpath)

        if list_empty_dir:
            raise CheckException("Empty directories detected : {}".format(
                list_empty_dir))

    def check_dcp_hidden_files(self):
        hidden_files = [f for f in self.dcp._list_files if f.startswith('.')]
        if hidden_files:
            raise CheckException("Hidden files detected : {}".format(
                hidden_files))

    def check_dcp_foreign_files(self):
        list_asset_path = [
            os.path.join(self.dcp.path, a)
            for a in self.dcp._list_asset.values()]
        list_asset_path += self.dcp._list_vol_path
        list_asset_path += self.dcp._list_am_path

        foreign_files = [
            a for a in self.dcp._list_files
            if a not in list_asset_path]
        if foreign_files:
            raise CheckException("Foreign files detected : {}".format(
                foreign_files))

    def check_dcp_multiple_am_or_vol(self):
        restricted_lists = {
            'VolIndex': self.dcp._list_vol,
            'Assetmap': self.dcp._list_am,
        }

        for k, v in six.iteritems(restricted_lists):
            if len(v) == 0:
                raise CheckException("Missing {} file".format(k))
            if len(v) > 1:
                raise CheckException("Multiple {} files found".format(k))

    def check_dcp_link_ov(self):
        """ Relink VF with OV """
        if not self.ov_path:
            return

        if self.ov_path and self.dcp.package_type != 'VF':
            raise CheckException("Package checked must be a VF")

        # Probe OV package
        from clairmeta.dcp import DCP
        ov_dcp = DCP(self.ov_path)
        ov_dcp_dict = ov_dcp.parse()
        if ov_dcp.package_type != 'OV':
            raise CheckException("Package referenced must be a OV")

        # Check that OV contains all referenced asset from VF
        # Probe those assets for later checks
        for cpl in self.dcp._list_cpl:
            for essence, asset in list_cpl_assets(cpl):
                if 'Path' not in asset:
                    uuid = asset['Id']
                    path_ov = ov_dcp_dict['asset_list'].get(uuid)

                    if not path_ov:
                        raise CheckException(
                            "Missing asset from OV : {}".format(uuid))

                    asset_path = os.path.join(ov_dcp.path, path_ov)
                    if not os.path.exists(asset_path):
                        raise CheckException(
                            "Missing asset from OV (MXF not found) : {}"
                            "".format(path_ov))

                    asset['Path'] = asset_path
                    cpl_probe_asset(asset, essence, asset_path)
