# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

from datetime import datetime

from clairmeta.dcp_utils import list_cpl_assets
from clairmeta.utils.isdcf import parse_isdcf_string
from clairmeta.dcp_check import CheckerBase
from clairmeta.settings import DCP_SETTINGS


class Checker(CheckerBase):
    def __init__(self, dcp):
        super(Checker, self).__init__(dcp)
        self.fields = None

    def run_checks(self):
        for source in self.dcp._list_cpl:
            asset_stack = [source['FileName']]
            self.run_check(
                self.check_dcnc_compliance, source, stack=asset_stack)

            checks = self.find_check('dcnc_field')
            [self.run_check(check, source, self.fields, stack=asset_stack)
             for check in checks]

        return self.checks

    def check_dcnc_compliance(self, playlist):
        """ Digital Cinema Naming Convention compliance (9.3). """
        cpl_node = playlist['Info']['CompositionPlaylist']
        ct = cpl_node['ContentTitleText']
        self.fields, errors = parse_isdcf_string(ct)
        if errors:
            self.error('\n'.join(errors))

    def check_dcnc_field_redband(self, playlist, fields):
        """ RedBand qualifier is restricted to Trailer. """
        is_trailer = fields['ContentType'].get('Type') == 'TLR'
        redband = fields['ContentType'].get('RedBand')
        if not is_trailer and redband:
            self.error("RedBand qualifier is only for trailer content")

    def check_dcnc_field_dimension(self, playlist, fields):
        """ 3D content shall specify 2D or 3D version. """
        is_3D = fields['Standard'].get('Dimension') == '3D'
        dimension_content = fields['ContentType'].get('Dimension')
        if is_3D and dimension_content == '':
            self.error("Content Type should specify 2D version or "
                       "3D version for 3D Movie")

    def check_dcnc_field_aspect_ratio(self, playlist, fields):
        """ ImageAspectRatio qualifier forbidden for Trailer. """
        is_trailer = fields['ContentType'].get('Type') == 'TLR'
        iar_qualifier = fields['ProjectorAspectRatio'].get('ImageAspectRatio')
        if is_trailer and iar_qualifier != '':
            self.error("Trailer content should not contain "
                       "ImageAspectRatio qualifier")

    def check_dcnc_field_date(self, playlist, fields):
        """ Composition Date validation. """
        date_str = fields['Date'].get('Value')
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y%m%d')
            except ValueError as e:
                self.fatal_error(
                    "Date can't be parsed, expecting YYYYMMDD : {}"
                    .format(date_str),
                    "format")

            now = datetime.now()
            if date > now:
                self.error(
                    "Date suggest a composition from the future",
                    "future")

    def check_dcnc_field_package_type(self, playlist, fields):
        """ Version qualifier is forbidden for OV package. """
        pkg_type = fields['PackageType'].get('Type')
        pkg_version = fields['PackageType'].get('Version')
        if pkg_type == 'OV' and pkg_version != '':
            self.error("OV Package can't include a version number "
                       "in the package type field")

    def check_dcnc_field_claim_framerate(self, playlist, fields):
        """ FrameRate from CPL and ContentTitleText shall match. """
        cpl_node = playlist['Info']['CompositionPlaylist']

        content_rate = fields['ContentType'].get('FrameRate')
        cpl_rate = str(cpl_node['EditRate'])
        if content_rate and cpl_rate != "Mixed" and content_rate != cpl_rate:
            self.error(
                "ContentTitle / CPL Framerate mismatch : {} / {}".format(
                    content_rate, cpl_rate))

    def check_dcnc_field_claim_dimension(self, playlist, fields):
        """ Dimension from CPL and ContentTitleText shall match. """
        cpl_node = playlist['Info']['CompositionPlaylist']

        dimension = fields['ContentType'].get('Dimension')
        cpl_stereo = cpl_node['Stereoscopic']
        is_stereo_map = {
            '2D': False,
            '3D': True
        }
        if (dimension and cpl_stereo != "Mixed" and
                is_stereo_map[dimension] != cpl_stereo):
            self.error(
                "ContentTitle suggest {} but CPL is {}".format(
                    dimension, '3D' if cpl_stereo else '2D'))

    def check_dcnc_field_claim_aspectratio(self, playlist, fields):
        """ AspectRatio from CPL and ContentTitleText shall match. """
        cpl_node = playlist['Info']['CompositionPlaylist']

        ar_str = fields['ProjectorAspectRatio'].get('AspectRatio')
        ar = DCP_SETTINGS['picture']['aspect_ratio'].get(ar_str)
        cpl_ar = cpl_node['ScreenAspectRatio']
        if ar and cpl_ar != "Mixed" and ar['ratio'] != cpl_ar:
            self.error(
                "ContentTitle / CPL AspectRatio mismatch : {} / {}".format(
                    ar['ratio'], cpl_ar))

    def check_dcnc_field_claim_subtitle(self, playlist, fields):
        """ Subtitle (presence) from CPL and ContentTitleText shall match. """
        cpl_node = playlist['Info']['CompositionPlaylist']

        hasSub = fields['Language'].get('Subtitle', False)
        hasBurnedSub = fields['Language'].get('BurnedSubtitle', False)
        cplHasSub = cpl_node['Subtitle']
        cplHasCaption = cpl_node['OpenCaption'] or cpl_node['ClosedCaption']
        captionLanguage = hasSub and not cplHasSub and cplHasCaption
        if not hasBurnedSub and hasSub != cplHasSub and not captionLanguage:
            msg_map = {
                True: 'Subtitle',
                False: 'No Subtitle'
            }

            self.error(
                "ContentTitle suggest {} but CPL contains {}".format(
                    msg_map[hasSub],
                    msg_map[cplHasSub]))


    def check_dcnc_field_claim_caption(self, playlist, fields):
        """ Captions (presence) from CPL and ContentTitleText shall match. """
        cpl_node = playlist['Info']['CompositionPlaylist']

        titleCaption = fields['Language'].get('Caption', '')
        if titleCaption is False:
            titleCaption = ''

        if 'OCAP' in titleCaption and not cpl_node['OpenCaption']:
            self.error("ContentTitle suggest OCAP but CPL has none")
        if 'CCAP' in titleCaption and not cpl_node['ClosedCaption']:
            self.error("ContentTitle suggest CCAP but CPL has none")
        if titleCaption == '' and cpl_node['OpenCaption']:
            self.error("ContentTitle suggest no caption but CPL has OCAP")
        if titleCaption == '' and cpl_node['ClosedCaption']:
            self.error( "ContentTitle suggest no caption but CPL has CCAP")

    def check_dcnc_field_claim_audio(self, playlist, fields):
        """ Audio format from CPL and ContentTitleText shall match. """
        # NOTE : MXF track count don't seems to be related to the actual
        # number of audio channels (there could be metadata and/or reserved
        # tracks).
        # TODO : SMPTE 428-12 add SoundField UL structure that could be used
        # to have a more meanigful check
        audio_format = fields['AudioType'].get('Channels')
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
                self.error(
                    "ContentTitle claims {} audio but CPL contains only "
                    " {} channels".format(audio_format, asset_cc))

    def check_dcnc_field_claim_immersive_sound(self, playlist, fields):
        """ Immersive audio format imply Auxiliary track in CPL. """
        immersive = fields['AudioType'].get('ImmersiveSound')
        auxdatas = list(list_cpl_assets(
            playlist,
            filters=['AuxData']))

        if immersive and not auxdatas:
            self.error("ContentTitle claims immersive audio ({}) "
                       "but CPL have no Auxiliary tracks".format(immersive))

        if immersive and auxdatas:
            assets = [
                asset for _, asset in auxdatas
                if asset['Schema'].lower() == immersive.lower()]

            if not assets:
                self.error("ContentTitle claims immersive audio ({})"
                           " but CPL is not".format(immersive))

    def check_dcnc_field_claim_resolution(self, playlist, fields):
        """ Picture resolution from CPL and ContentTitleText shall match.  """
        resolution_map = DCP_SETTINGS['picture']['resolutions']
        resolution = fields['Resolution'].get('Value')

        mxf_res = playlist['Info']['CompositionPlaylist']['Resolution']
        detect_res = mxf_res != 'Unknown' and mxf_res != 'Mixed'

        if resolution and detect_res:
            if mxf_res not in resolution_map[resolution]:
                self.error(
                    "ContentTitle claims {} but CPL Picture track resolution "
                    "is {}".format(resolution, mxf_res))

    def check_dcnc_field_claim_standard(self, playlist, fields):
        """ DCP Standard coherence check. """
        standard = fields['Standard'].get('Schema')
        if standard and standard != self.dcp.schema:
            self.error("ContentTitle claims {} but DCP schema is {}".format(
                standard, self.dcp.schema))

    def check_dcnc_field_claim_dolbyvision(self, playlist, fields):
        """ DolbyVision metadata shall be present in CPL. """
        dvi_dcnc = fields['ContentType'].get('DolbyVision')
        dvi_cpl = playlist['Info']['CompositionPlaylist']['DolbyVision']
        if dvi_dcnc and not dvi_cpl:
            self.error("ContentTitle claims DolbyVision but CPL "
                       "miss required metadata")
        elif not dvi_dcnc and dvi_cpl:
            self.error("CPL imply DolbyVision but ContentTitle miss "
                       "DVis ContentType field")

    def check_dcnc_field_claim_eclaircolor(self, playlist, fields):
        """ EclairColor metadata shall be present in CPL. """
        ec_dcnc = fields['ContentType'].get('EclairColor')
        ec_cpl = playlist['Info']['CompositionPlaylist']['EclairColor']
        if ec_dcnc and not ec_cpl:
            self.error("ContentTitle claims EclairColor but CPL "
                                 "miss required metadata")
        elif not ec_dcnc and ec_cpl:
            self.error("CPL imply EclairColor but ContentTitle miss "
                                 "EC ContentType field")

    def check_dcnc_field_claim_packagetype(self, playlist, fields):
        """ DCP type (OV / VF) coherence check. """
        package = fields['PackageType'].get('Type')
        dcp_package = self.dcp.package_type

        if package and package == 'OV' and dcp_package != package:
            self.error( "ContentTitle claims OV but DCP is not complete")

        if package and package == 'VF' and dcp_package != package:
            self.error("ContentTitle claims VF but DCP is complete")
