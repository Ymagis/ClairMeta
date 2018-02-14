# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import six
import time

from clairmeta.logger import get_log
from clairmeta.dcp_utils import list_cpl_assets
from clairmeta.dcp_parse import (assetmap_parse, volindex_parse, pkl_parse,
                                 cpl_parse)
from clairmeta.dcp_utils import (list_am_assets, list_pkl_assets,
                                 cpl_extract_characteristics, cpl_probe_asset)
from clairmeta.dcp_check import DCPChecker
from clairmeta.utils.xml import parse_xml
from clairmeta.utils.sys import remove_key_dict
from clairmeta.utils.file import folder_size, human_size, console_progress_bar
from clairmeta.settings import DCP_SETTINGS
from clairmeta.profile import DCP_CHECK_PROFILE


class DCP(object):
    """ Digital Cinema Package abstraction. """

    def __init__(self, path):
        """ DCP constructor.

            Args:
                path (str): Absolute path to directory.

            Raises:
                ValueError: ``path`` directory not found.

        """

        if not os.path.isdir(path):
            raise ValueError("{} is not a valid folder".format(path))

        self.path = os.path.normpath(path)
        self.schema = 'Unknown'
        self.package_type = 'Unknown'
        self.foreign_files = []
        self.size = folder_size(path)
        self.log = get_log()

        self._probeb = False
        self._parsed = False

    def init_package_files(self):
        """ List all files present in DCP. """
        self._list_files = []
        for dirpath, dirnames, filenames in os.walk(self.path):
            for f in filenames:
                fullpath = os.path.join(dirpath, f)
                self._list_files.append(fullpath)

    def filter_files(self, filters):
        """ Build a list of package files matching specific names. """
        candidates = [os.path.join(self.path, c) for c in filters]
        return [f for f in self._list_files if f in candidates]

    def filter_xml_by_root(self, root_name):
        """ Build a list of package XML files having a specific root node. """
        xml_list = []
        candidates = [
            f for f in self._list_files
            if f.endswith('.xml') and not f.startswith('.')
            and os.path.dirname(f) == self.path]

        for c in candidates:
            nodes = parse_xml(c, namespaces=DCP_SETTINGS['xmlns'])
            if root_name in nodes:
                xml_list.append(c)

        return xml_list

    def init_assetmap(self):
        """ Find DCP AssetMap and build Asset List. """
        self._list_am_path = self.filter_files(['ASSETMAP', 'ASSETMAP.xml'])
        self._list_am = [assetmap_parse(f) for f in self._list_am_path]

        # In the improbable case of multiple Assetmap found in the folder,
        # flatten asset list.
        self._list_asset = [{
            uuid: path
            for a in self._list_am
            for uuid, path, _ in list_am_assets(a)}]
        self._list_asset = {
            k: v for _list_asset in self._list_asset
            for k, v in six.iteritems(_list_asset)}

        # Schema (IOP or SMPTE) is assumed to be the one found for the Assetmap
        if self._list_am:
            self.schema = self._list_am[0]['Info']['AssetMap']['Schema']

    def init_volindex(self):
        """ Find DCP VolIndex. """
        self._list_vol_path = self.filter_files(['VOLINDEX', 'VOLINDEX.xml'])
        self._list_vol = [volindex_parse(f) for f in self._list_vol_path]

    def init_pkl(self):
        """ Find DCP PackingList. """
        self._list_pkl_path = self.filter_xml_by_root('PackingList')
        self._list_pkl = [pkl_parse(f) for f in self._list_pkl_path]

        self.pkl_find_path()

    def pkl_find_path(self):
        """ Find path for each PKL assets (using UUID and AssetMap). """
        for pkl in self._list_pkl:
            pkl_node = pkl['Info']['PackingList']
            for asset in pkl_node['AssetList']['Asset']:
                asset_id = asset['Id']
                if asset_id in self._list_asset:
                    asset['Path'] = os.path.join(self._list_asset[asset_id])

    def init_cpl(self):
        """ Find DCP CompositionPlayList. """
        self._list_cpl_path = self.filter_xml_by_root('CompositionPlaylist')
        self._list_cpl = [cpl_parse(f) for f in self._list_cpl_path]

        self.cpl_find_pkl()
        self.cpl_link_assets()

    def cpl_find_pkl(self):
        """ Find PKL that reference the CPL. """
        for cpl in self._list_cpl:
            cpl_node = cpl['Info']['CompositionPlaylist']
            cpl_id = cpl_node['Id']

            for pkl in self._list_pkl:
                assets = list(list_pkl_assets(pkl))
                uuids = [asset_id for asset_id, _, _ in assets]

                if cpl_id in uuids:
                    cpl_node['PKLId'] = pkl['Info']['PackingList']['Id']

    def cpl_link_assets(self):
        """ Link assets for each reel with actual files in the package. """
        # TODO : For Multi CPL package, what to choose if there are both
        # OV / VF?
        self.package_type = 'OV'

        for cpl in self._list_cpl:
            for _, asset in list_cpl_assets(cpl):
                asset_id = asset['Id']
                if asset_id in self._list_asset:
                    asset['Path'] = self._list_asset[asset_id]
                else:
                    self.package_type = 'VF'

    def cpl_probe_assets(self):
        """ Probe mxf assets for each reel. """
        for cpl in self._list_cpl:
            for essence, asset in list_cpl_assets(cpl):
                asset_path = os.path.join(self.path, asset.get('Path', ''))
                cpl_probe_asset(asset, essence, asset_path)

    def cpl_parse_metadata(self):
        """ Extract CPL common metadata. """
        for cpl in self._list_cpl:
            cpl_node = cpl['Info']['CompositionPlaylist']
            cpl_extract_characteristics(cpl_node)

    @property
    def list_assetmap(self):
        """ List of DCP AssetMap Dictionary. """
        return self._list_am

    @property
    def list_volindex(self):
        """ List of DCP VolIndex Dictionary. """
        return self._list_vol

    @property
    def list_pkl(self):
        """ List of DCP PackingList Dictionary. """
        return self._list_pkl

    @property
    def list_cpl(self):
        """ List of DCP CompositionPlayList Dictionary. """
        return self._list_cpl

    def parse(self, probe=True):
        """ Parse the DCP and Probe its assets. """
        if self._parsed:
            return self.probe_dict

        start = time.time()
        self.log.info("Probing DCP : {}".format(self.path))

        # Find and parse package components
        self.init_package_files()
        self.init_assetmap()
        self.init_volindex()
        self.init_pkl()
        self.init_cpl()

        if probe:
            self.cpl_probe_assets()
            self._probeb = True

        self.cpl_parse_metadata()

        seconds_elapsed = time.time() - start
        self.log.info("Total time : {:.2f} seconds".format(seconds_elapsed))

        self.probe_dict = {
            'asset_list': self._list_asset,
            'volindex_list': self._list_vol,
            'assetmap_list': self._list_am,
            'cpl_list': self._list_cpl,
            'pkl_list': self._list_pkl,
            'package_type': self.package_type,
            'path': self.path,
            'size': human_size(self.size),
            'count_file': len(self._list_asset),
            'schema': self.schema,
            'type': 'DCP'
        }

        # Remove namespace and attributes key from final result
        self.probe_dict = remove_key_dict(
            self.probe_dict, ['__xmlns__', '@xmlns'])
        self._parsed = True
        return self.probe_dict

    def check(
        self, profile=DCP_CHECK_PROFILE, ov_path=None,
        hash_callback=console_progress_bar
    ):
        """ Check validity.

            Args:
                profile (dict): Checker profile.
                ov_path (str, optional): Absolute path of OriginalVersion DCP.

            Returns:
                Tuple (boolean, dict) of DCP check status and report. Report
                    is a Dictionary where check failure are grouped by
                    criticity.

        """
        if not self._parsed or not self._probeb:
            self.parse()

        self._checker = DCPChecker(
            self, profile=profile, ov_path=ov_path,
            hash_callback=hash_callback)
        return self._checker.check()
