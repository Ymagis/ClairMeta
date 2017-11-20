# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

from datetime import datetime

from clairmeta.dcp_utils import list_cpl_assets
from clairmeta.check_isdcf import parse_isdcf_string
from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.settings import DCP_SETTINGS


class Checker(CheckerBase):
    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

    def run_checks(self):
        for source in self.dcp._list_cpl:
            valid, fields = self.run_check(self.check_dcnc_compliance, source)
            if valid:
                checks = self.find_check('dcnc_field')
                [self.run_check(check, source, fields) for check in checks]

        return self.check_executions

    def check_dcnc_compliance(self, playlist):
        """ Strict ISDCF DCNC check """
        cpl_node = playlist['Info']['CompositionPlaylist']
        ct = cpl_node['ContentTitleText']
        fields, errors = parse_isdcf_string(ct)
        if errors:
            raise CheckException('\n'.join(errors))

        return fields

    def check_dcnc_field_redband(self, playlist, fields):
        """ See Appendix 3. """
        is_trailer = fields['content_type']['Type'] == 'TLR'
        redband = fields['content_type']['RedBand']
        if not is_trailer and redband is not None:
            raise CheckException(
                "RedBand qualifier is only for trailer content")

    def check_dcnc_field_dimension(self, playlist, fields):
        is_3D = fields['standard'].get('Dimension') is not None
        dimension_content = fields['content_type'].get('Dimension')
        if is_3D and dimension_content is None:
            raise CheckException("Content Type should specifiy 2D version or "
                                 "3D version for 3D Movie")

    def check_dcnc_field_aspect_ratio(self, playlist, fields):
        """ See Appendix 7. """
        is_trailer = fields['content_type']['Type'] == 'TLR'
        iar_qualifier = fields['projector_aspect_ratio']['ImageAspectRatio']
        if is_trailer and iar_qualifier is not None:
            raise CheckException("Trailer content should not contain "
                                 "ImageAspectRatio qualifier")

    def check_dcnc_field_date(self, playlist, fields):
        """ Basic date check """
        date_str = fields['date']['Value']
        date = datetime.strptime(date_str, '%Y%m%d')
        now = datetime.now()
        if date > now:
            raise CheckException("Date suggest a composition from the future")

    def check_dcnc_field_package_type(self, playlist, fields):
        """ Basic date check """
        pkg_type = fields['package_type']['Type']
        pkg_version = fields['package_type']['Version']
        if pkg_type == 'OV' and pkg_version is not None:
            raise CheckException("OV Package can't include a version number "
                                 "in the package type field")

    def check_dcnc_field_claim_framerate(self, playlist, fields):
        cpl_node = playlist['Info']['CompositionPlaylist']

        content_type = fields['content_type']
        content_rate = content_type['FrameRate']
        cpl_rate = str(cpl_node['EditRate'])
        if content_rate and cpl_rate != "Mixed" and content_rate != cpl_rate:
            raise CheckException(
                "ContentTitle / CPL Framerate mismatch : {} / {}".format(
                    content_rate, cpl_rate))

    def check_dcnc_field_claim_dimension(self, playlist, fields):
        cpl_node = playlist['Info']['CompositionPlaylist']

        content_type = fields['content_type']
        dimension = content_type['Dimension']
        cpl_stereo = cpl_node['Stereoscopic']
        is_stereo_map = {
            '2D': False,
            '3D': True
        }
        if (dimension and cpl_stereo != "Mixed" and
                is_stereo_map[dimension] != cpl_stereo):
            raise CheckException(
                "ContentTitle suggest {} but CPL is not".format(dimension))

    def check_dcnc_field_claim_aspectratio(self, playlist, fields):
        cpl_node = playlist['Info']['CompositionPlaylist']

        ar_str = fields['projector_aspect_ratio']['AspectRatio']
        ar = DCP_SETTINGS['picture']['aspect_ratio'].get(ar_str)
        cpl_ar = cpl_node['ScreenAspectRatio']
        if ar and cpl_ar != "Mixed" and ar['ratio'] != cpl_ar:
            raise CheckException(
                "ContentTitle / CPL AspectRatio mismatch : {} / {}".format(
                    ar['ratio'], cpl_ar))

    def check_dcnc_field_claim_subtitle(self, playlist, fields):
        cpl_node = playlist['Info']['CompositionPlaylist']

        subtitle = fields['language']['Subtitle']
        if subtitle != cpl_node['Subtitle']:
            raise CheckException(
                "ContentTitle suggest Subtitle but CPL have none")

    def check_dcnc_field_claim_audio(self, playlist, fields):
        # Note : MXF track count don't seems to be related to the actual
        # number of audio channels (there could be metadata and/or reserved
        # tracks).
        # TODO : SMPTE 428-12 add SoundField UL structure that could be used
        # to have a more meanigful check
        audio_format = fields['audio_type']['Channels']
        audio_map = DCP_SETTINGS['sound']['format_channels']
        sounds = list(list_cpl_assets(
            playlist,
            filters=['Sound'],
            required_keys=['Probe']))

        if sounds and audio_format:
            _, asset = sounds[0]
            asset_cc = asset['Probe']['ChannelCount']
            cpl_cc = audio_map.get(audio_format)

            if cpl_cc and asset_cc < cpl_cc:
                raise CheckException(
                    "ContentTitle claims {} audio but CPL contains only "
                    " {} channels".format(audio_format, asset_cc))

    def check_dcnc_field_claim_immersive_sound(self, playlist, fields):
        immersive = fields['audio_type']['ImmersiveSound']
        auxdatas = list(list_cpl_assets(
            playlist,
            filters=['AuxData'],
            required_keys=['Probe']))

        if immersive and not auxdatas:
            raise CheckException("ContentTitle claims immersive audio ({}) "
                                 "but CPL have no Auxiliary tracks".format(
                                    immersive))

        if immersive and auxdatas:
            assets = [
                asset for _, asset in auxdatas
                if asset['Schema'].lower() == immersive.lower()]

            if not assets:
                raise CheckException("ContentTitle claims immersive audio ({})"
                                     " but CPL is not".format(immersive))

    def check_dcnc_field_claim_resolution(self, playlist, fields):
        resolution_map = DCP_SETTINGS['picture']['resolutions']
        resolution = fields['resolution']['Value']

        mxf_res = playlist['Info']['CompositionPlaylist']['Resolution']
        detect_res = mxf_res != 'Unknown' and mxf_res != 'Mixed'

        if resolution and detect_res:
            if mxf_res not in resolution_map[resolution]:
                raise CheckException(
                    "ContentTitle claims {} but CPL Picture track resolution "
                    "is {}".format(resolution, mxf_res))

    def check_dcnc_field_claim_standard(self, playlist, fields):
        standard = fields['standard']['Schema']
        if standard and standard != self.dcp.schema:
            raise CheckException("ContentTitle claims {} but DCP is not")

    def check_dcnc_field_claim_packagetype(self, playlist, fields):
        # TODO : this check don't work for multi-CPL packages
        pass

        package = fields['package_type']['Type']
        dcp_package = self.dcp.package_type
        if package and dcp_package != package:
            raise CheckException(
                "ContentTitle claims {} but DCP is not".format(package))
