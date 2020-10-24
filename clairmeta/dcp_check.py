# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import six
import importlib
import inspect

from clairmeta.settings import DCP_CHECK_SETTINGS
from clairmeta.profile import get_default_profile
from clairmeta.dcp_utils import list_cpl_assets, cpl_probe_asset
from clairmeta.dcp_check_base import CheckerBase, CheckException
from clairmeta.utils.file import ConsoleProgress
from clairmeta.utils.sys import all_keys_in_dict


class DCPChecker(CheckerBase):
    """ Digital Cinema Package checker. """

    def __init__(
        self, dcp, profile=get_default_profile(), ov_path=None,
        hash_callback=None
    ):
        """ DCPChecker constructor.

            Args:
                dcp (clairmeta.DCP): DCP object.
                profile (dict): Checker profile.
                ov_path (str, optional): Absolute path of OriginalVersion DCP.

        """
        super(DCPChecker, self).__init__(dcp, profile)
        self.ov_path = ov_path
        self.ov_dcp = None

        self.hash_callback = hash_callback
        if not self.hash_callback:
            pass
        elif isinstance(self.hash_callback, ConsoleProgress):
            self.hash_callback._total_size = self.dcp.size
        elif inspect.isclass(self.hash_callback):
            raise CheckException(
                "Invalid callback, please provide a function"
                " or instance of ConsoleProgress (or derivate).")

        self.check_modules = {}
        self.load_modules()

    def load_modules(self):
        prefix = DCP_CHECK_SETTINGS['module_prefix']
        for k, v in six.iteritems(DCP_CHECK_SETTINGS['modules']):
            try:
                module_path = 'clairmeta.' + prefix + k
                module_vol = importlib.import_module(module_path)
                checker = module_vol.Checker(self.dcp, self.profile)
                checker.hash_callback = self.hash_callback
                self.check_modules[v] = checker
            except (ImportError, Exception) as e:
                self.log.critical("Import error {} : {}".format(
                    module_path, str(e)))

    def check(self):
        """ Execute the complete check process. """
        self.run_checks()
        self.make_report()
        self.dump_report()
        return self.report.valid(), self.report

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
        self.log.info("Checking DCP : {}".format(self.dcp.path))

        # Run own tests
        dcp_checks = self.find_check('dcp')
        [self.run_check(c, stack=[self.dcp.path]) for c in dcp_checks]
        self.setup_dcp_link_ov()

        # Run external modules tests
        for _, checker in six.iteritems(self.check_modules):
            self.checks += checker.run_checks()

    def check_dcp_empty_dir(self):
        """ Empty directory detection.

            Reference : N/A
        """
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
        """ Hidden files detection.

            Reference : N/A
        """
        hidden_files = [
            os.path.relpath(f, self.dcp.path)
            for f in self.dcp._list_files
            if os.path.basename(f).startswith('.')]
        if hidden_files:
            raise CheckException("Hidden files detected : {}".format(
                hidden_files))

    def check_dcp_foreign_files(self):
        """ Foreign files detection (not listed in AssetMap).

            Reference : N/A
        """
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
            raise CheckException('\n'.join(self.dcp.foreign_files))

    def check_dcp_multiple_am_or_vol(self):
        """ Only one AssetMap and VolIndex shall be present.

            Reference : N/A
        """
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
        """ Setup the link VF to OV check and run for each assets. """
        if not self.ov_path:
            return

        self.run_check(self.check_link_ov_coherence, stack=[self.dcp.path])
        for cpl in self.dcp._list_cpl:
            for essence, asset in list_cpl_assets(cpl):
                self.run_check(
                    self.check_link_ov_asset,
                    asset, essence, stack=[self.dcp.path])

    def check_dcp_signed(self):
        """ DCP with encrypted content must be digitally signed.

            Reference :
                DCI Spec 1.3 5.4.3.7.
                DCI Spec 1.3 5.5.2.3.
        """
        for cpl in self.dcp._list_cpl:
            cpl_node = cpl['Info']['CompositionPlaylist']
            xmls = [
                pkl['Info']['PackingList'] for pkl in self.dcp._list_pkl
                if pkl['Info']['PackingList']['Id'] == cpl_node.get('PKLId')]
            xmls.append(cpl_node)

            for xml in xmls:
                signed = all_keys_in_dict(xml, ['Signer', 'Signature'])
                if not signed and cpl_node['Encrypted'] is True:
                    raise CheckException("Encrypted DCP must be signed")

    def check_link_ov_coherence(self):
        """ Relink OV/VF sanity checks.

            Reference : N/A
        """
        if self.ov_path and self.dcp.package_type != 'VF':
            raise CheckException("Package checked must be a VF")

        from clairmeta.dcp import DCP
        self.ov_dcp = DCP(self.ov_path)
        self.ov_dcp.parse()
        if self.ov_dcp.package_type != 'OV':
            raise CheckException("Package referenced must be a OV")

    def check_link_ov_asset(self, asset, essence):
        """ VF package shall reference assets present in OV.

            Reference : N/A
        """
        if not self.ov_dcp:
            return

        ov_dcp_dict = self.ov_dcp.parse()

        if not asset.get('Path'):
            uuid = asset['Id']
            path_ov = ov_dcp_dict['asset_list'].get(uuid)

            if not path_ov:
                raise CheckException(
                    "Asset missing ({}) from OV : {}".format(essence, uuid))

            asset_path = os.path.join(self.ov_dcp.path, path_ov)
            if not os.path.exists(asset_path):
                raise CheckException(
                    "Asset missing ({}) from OV (MXF not found) : {}"
                    "".format(essence, path_ov))

            # Probe asset for later checks
            asset['AbsolutePath'] = asset_path
            cpl_probe_asset(asset, essence, asset_path)
