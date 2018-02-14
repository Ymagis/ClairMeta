# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import six
import importlib

from clairmeta.settings import DCP_CHECK_SETTINGS
from clairmeta.logger import set_level
from clairmeta.profile import get_default_profile
from clairmeta.dcp_utils import list_cpl_assets, cpl_probe_asset
from clairmeta.dcp_check_base import CheckerBase, CheckException
from clairmeta.utils.file import console_progress_bar


class DCPChecker(CheckerBase):
    """ Digital Cinema Package checker. """

    def __init__(
        self, dcp, profile=get_default_profile(), ov_path=None,
        hash_callback=console_progress_bar
    ):
        """ DCPChecker constructor.

            Args:
                dcp (clairmeta.DCP): DCP object.
                profile (dict): Checker profile.
                ov_path (str, optional): Absolute path of OriginalVersion DCP.

        """
        super(DCPChecker, self).__init__(dcp, profile)
        set_level(profile['log_level'])
        self.ov_path = ov_path
        self.hash_callback = hash_callback

        self.check_modules = {}
        self.load_modules()

    def load_modules(self):
        prefix = DCP_CHECK_SETTINGS['module_prefix']
        for k, v in six.iteritems(DCP_CHECK_SETTINGS['modules']):
            try:
                module_path = 'clairmeta.' + prefix + k
                module_vol = importlib.import_module(module_path)
                checker = module_vol.Checker(self.dcp, self.check_profile)
                checker.hash_callback = self.hash_callback
                self.check_modules[v] = checker
            except (ImportError, Exception) as e:
                self.check_log.critical("Import error {} : {}".format(
                    module_path, str(e)))

    def check(self):
        """ Execute the complete check process. """
        self.run_checks()
        self.make_report()
        self.dump_report()
        return self.get_valid(), self.check_report

    def list_checks(self):
        """ List all available checks. """
        all_checks = {}
        all_checks['General'] = self.find_check('dcp')
        all_checks['General'] += self.find_check('link_ov')

        for desc, checker in six.iteritems(self.check_modules):
            all_checks[desc] = checker.find_check('')

        res = {}
        for k, v in six.iteritems(all_checks):
            checks = []
            for check in v:
                docstring = check.__doc__
                if docstring:
                    desc = docstring.splitlines()[0].strip()
                else:
                    desc = ""

                checks.append((check.__name__, desc))
            res[k] = checks

        return res

    def run_checks(self):
        """ Execute all checks. """
        self.check_log.info("Checking DCP : {}".format(self.dcp.path))

        # Run own tests
        dcp_checks = self.find_check('dcp')
        [self.run_check(c) for c in dcp_checks]
        self.setup_dcp_link_ov()

        # Run external modules tests
        for _, checker in six.iteritems(self.check_modules):
            self.check_executions += checker.run_checks()

    def check_dcp_empty_dir(self):
        """ Empty directory detection. """
        list_empty_dir = []
        for dirpath, dirnames, filenames in os.walk(self.dcp.path):
            for d in dirnames:
                fullpath = os.path.join(dirpath, d)
                if not os.listdir(fullpath):
                    list_empty_dir.append(
                        os.path.relpath(fullpath, self.dcp.path))

        if list_empty_dir:
            raise CheckException("Empty directories detected : {}".format(
                list_empty_dir))

    def check_dcp_hidden_files(self):
        """ Hidden files detection. """
        hidden_files = [
            os.path.relpath(f, self.dcp.path)
            for f in self.dcp._list_files
            if os.path.basename(f).startswith('.')]
        if hidden_files:
            raise CheckException("Hidden files detected : {}".format(
                hidden_files))

    def check_dcp_foreign_files(self):
        """ Foreign files detection (not listed in AssetMap). """
        list_asset_path = [
            os.path.join(self.dcp.path, a)
            for a in self.dcp._list_asset.values()]
        list_asset_path += self.dcp._list_vol_path
        list_asset_path += self.dcp._list_am_path

        self.dcp.foreign_files = [
            os.path.relpath(a, self.dcp.path)
            for a in self.dcp._list_files
            if a not in list_asset_path]
        if self.dcp.foreign_files:
            raise CheckException("Foreign files detected : {}".format(
                self.dcp.foreign_files))

    def check_dcp_multiple_am_or_vol(self):
        """ Only one AssetMap and VolIndex shall be present. """
        restricted_lists = {
            'VolIndex': self.dcp._list_vol,
            'Assetmap': self.dcp._list_am,
        }

        for k, v in six.iteritems(restricted_lists):
            if len(v) == 0:
                raise CheckException("Missing {} file".format(k))
            if len(v) > 1:
                raise CheckException("Multiple {} files found".format(k))

    def setup_dcp_link_ov(self):
        """ Setup the link VF to OV check and run for each assets . """
        if not self.ov_path:
            return

        self.run_check(self.check_link_ov_coherence)
        for cpl in self.dcp._list_cpl:
            for essence, asset in list_cpl_assets(cpl):
                self.run_check(self.check_link_ov_asset, asset, essence)

    def check_link_ov_coherence(self):
        """ Relink OV/VF sanity checks. """
        if self.ov_path and self.dcp.package_type != 'VF':
            raise CheckException("Package checked must be a VF")

        from clairmeta.dcp import DCP
        self.ov_dcp = DCP(self.ov_path)
        self.ov_dcp.parse()
        if self.ov_dcp.package_type != 'OV':
            raise CheckException("Package referenced must be a OV")

    def check_link_ov_asset(self, asset, essence):
        """ VF package shall reference assets present in OV. """
        ov_dcp_dict = self.ov_dcp.parse()

        if 'Path' not in asset:
            uuid = asset['Id']
            path_ov = ov_dcp_dict['asset_list'].get(uuid)

            if not path_ov:
                raise CheckException(
                    "Missing asset from OV : {}".format(uuid))

            asset_path = os.path.join(self.ov_dcp.path, path_ov)
            if not os.path.exists(asset_path):
                raise CheckException(
                    "Missing asset from OV (MXF not found) : {}"
                    "".format(path_ov))

            # Probe asset for later checks
            asset['Path'] = asset_path
            cpl_probe_asset(asset, essence, asset_path)
