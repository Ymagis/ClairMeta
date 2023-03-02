# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import six

from clairmeta.dcp_utils import list_cpl_assets, cpl_probe_asset
from clairmeta.dcp_check import CheckerBase
from clairmeta.utils.sys import all_keys_in_dict


class Checker(CheckerBase):
    def __init__(self, dcp):
        super(Checker, self).__init__(dcp)

    def run_checks(self):
        """ Execute all checks. """
        dcp_checks = self.find_check('dcp')
        [self.run_check(c, stack=[self.dcp.path]) for c in dcp_checks]
        self.setup_dcp_link_ov()

        return self.checks

    def check_dcp_empty_dir(self):
        """ Empty directory detection.

            References: N/A
        """
        list_empty_dir = []
        for dirpath, dirnames, filenames in os.walk(self.dcp.path):
            for d in dirnames:
                fullpath = os.path.join(dirpath, d)
                if not os.listdir(fullpath):
                    list_empty_dir.append(
                        os.path.relpath(fullpath, self.dcp.path))

        if list_empty_dir:
            self.error("Empty directories detected : {}".format(list_empty_dir))

    def check_dcp_hidden_files(self):
        """ Hidden files detection.

            References: N/A
        """
        hidden_files = [
            os.path.relpath(f, self.dcp.path)
            for f in self.dcp._list_files
            if os.path.basename(f).startswith('.')]
        if hidden_files:
            self.error("Hidden files detected : {}".format(hidden_files))

    def check_dcp_foreign_files(self):
        """ Foreign files detection (not listed in AssetMap).

            References: N/A
        """
        list_asset_path = [
            os.path.join(self.dcp.path, a)
            for a in self.dcp._list_asset.values()]
        list_asset_path += self.dcp._list_vol_path
        list_asset_path += self.dcp._list_am_path

        allowed_paths = [
            os.path.join(self.dcp.path, a) 
            for a in self.allowed_foreign_files]

        self.dcp.foreign_files = [
            os.path.relpath(a, self.dcp.path)
            for a in self.dcp._list_files
            if a not in list_asset_path and a not in allowed_paths]
        if self.dcp.foreign_files:
            self.error('\n'.join(self.dcp.foreign_files))

    def check_dcp_multiple_am_or_vol(self):
        """ Only one AssetMap and VolIndex shall be present.

            References: N/A
        """
        restricted_lists = {
            'VolIndex': self.dcp._list_vol,
            'Assetmap': self.dcp._list_am,
        }

        for k, v in six.iteritems(restricted_lists):
            if len(v) == 0:
                self.error("Missing {} file".format(k))
            if len(v) > 1:
                self.error("Multiple {} files found".format(k))

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

            References:
                DCI DCSS (v1.3) 5.4.3.7
                DCI DCSS (v1.3) 5.5.2.3
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
                    self.error("Encrypted DCP must be signed")

    def check_link_ov_coherence(self):
        """ Relink OV/VF sanity checks.

            References: N/A
        """
        if self.ov_path and self.dcp.package_type != 'VF':
            self.error("Package checked must be a VF")

        from clairmeta.dcp import DCP
        self.ov_dcp = DCP(self.ov_path)
        self.ov_dcp.parse()
        if self.ov_dcp.package_type != 'OV':
            self.error("Package referenced must be a OV")

    def check_link_ov_asset(self, asset, essence):
        """ VF package shall reference assets present in OV.

            References: N/A
        """
        if not self.ov_dcp:
            return

        ov_dcp_dict = self.ov_dcp.parse()

        if not asset.get('Path'):
            uuid = asset['Id']
            path_ov = ov_dcp_dict['asset_list'].get(uuid)

            if not path_ov:
                self.error(
                    "Asset missing ({}) from OV : {}".format(essence, uuid))

            asset_path = os.path.join(self.ov_dcp.path, path_ov)
            if not os.path.exists(asset_path):
                self.error(
                    "Asset missing ({}) from OV (MXF not found) : {}"
                    "".format(essence, path_ov))

            # Probe asset for later checks
            asset['AbsolutePath'] = asset_path
            cpl_probe_asset(asset, essence, asset_path)
