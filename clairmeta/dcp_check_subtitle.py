# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import re
import magic
import pycountry

from clairmeta.utils.time import tc_to_frame, frame_to_tc
from clairmeta.utils.file import human_size
from clairmeta.utils.sys import keys_by_name_dict, keys_by_pattern_dict
from clairmeta.utils.xml import parse_xml
from clairmeta.utils.probe import unwrap_mxf
from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_check_utils import check_xml
from clairmeta.dcp_utils import list_cpl_assets, get_reel_for_asset
from clairmeta.settings import DCP_SETTINGS


class Checker(CheckerBase):

    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

    def run_checks(self):
        for cpl in self.dcp._list_cpl:
            checks = self.find_check('subtitle_cpl')
            assets = list_cpl_assets(
                cpl, filters='Subtitle', required_keys=['Path'])

            [self.run_checks_prepare(checks, cpl, asset) for asset in assets]

        return self.check_executions

    def run_checks_prepare(self, checks, cpl, asset):
        _, asset_node = asset
        path = os.path.join(self.dcp.path, asset_node['Path'])
        do_unwrap = path.endswith('.mxf') and os.path.isfile(path)

        if asset_node['Encrypted']:
            return
        elif do_unwrap:
            with unwrap_mxf(path) as folder:
                [self.run_check(
                    check, cpl, asset, folder, message="{} (Asset {})".format(
                        cpl['FileName'], asset[1].get('Path', asset[1]['Id'])))
                    for check in checks]
        else:
            folder = os.path.dirname(path)
            [self.run_check(
                check, cpl, asset, folder, message="{} (Asset {})".format(
                    cpl['FileName'], asset[1].get('Path', asset[1]['Id'])))
             for check in checks]

    def get_subtitle_xml(self, asset, folder):
        _, asset = asset

        if asset['Path'].endswith('.xml'):
            xml_path = os.path.join(self.dcp.path, asset['Path'])
        else:
            xml_path = os.path.join(folder, os.path.splitext(asset['Path'])[0])

        if not os.path.exists(xml_path):
            return

        return parse_xml(
            xml_path,
            namespaces=DCP_SETTINGS['xmlns'],
            force_list=('Subtitle',))

    def get_subtitle_elem(self, xml_dict, name):
        subtitle_root = {
            'Interop': 'DCSubtitle',
            'SMPTE': 'SubtitleReel'
        }

        root = xml_dict.get(subtitle_root[self.dcp.schema])
        if root:
            return root.get(name)

    def get_subtitle_editrate(self, asset, xml_dict):
        _, asset = asset

        if self.dcp.schema == 'SMPTE':
            tc_rate = xml_dict['SubtitleReel']['TimeCodeRate']
        else:
            tc_rate = asset['EditRate']

        return tc_rate

    def ticks_to_frame(self, tick, edit_rate):
        tick = int(tick)
        time_base = 1.0 / edit_rate
        return int((tick * 0.004) // time_base)

    def st_tc_frames(self, tc, edit_rate):
        """ Convert TimeCode to frame count.

            Interop DCSubtitle :
            Format is either hh:mm:ss:ttt or hh:mm:ss.sss or ttt
            (for fade up / down).

            The time is specified in the format, HH:MM:SS:TTT where HH = hours,
            MM = minutes, SS = seconds, and TTT = ticks. A "tick" is defined as
            4 msec and has a range of 0 to 249. This definition of tick was
            chosen because it will allow frame accurate timing at multiple
            frame rates, without specifying the display frame rate in the
            subtitle file.

            Alternatively, time may be specified in the format
            HH:MM:SS.sss where HH = hours, MM = minutes, SS =
            seconds, and sss = decimal fractions of a second. In
            this format, 01:12:42.5 would indicate 1 hour, 12
            minutes, 42 and 1/2 seconds. This definition of time was
            chosen because it will allow frame accurate timing at
            multiple frame rates, without specifying the display
            frame rate in the subtitle file.

            SMPTE :
            Format is always HH:MM:SS:E+, where E+ is the edit unit ie. an
            integer between 0 and TimeCodeRate - 1, typically 2 or 3 digits.

        """
        tc = str(tc)
        tick_simple_pattern = r'^\d{1,3}$'
        tick_pattern = r'^\d{2}:\d{2}:\d{2}:(?P<Tick>\d{2,3})$'
        fract_pattern = r'^\d{2}:\d{2}:\d{2}\.(?P<Fract>\d{1,3})$'

        if self.dcp.schema == 'Interop':
            if re.match(tick_simple_pattern, tc):
                frame = self.ticks_to_frame(tc, edit_rate)
                tc = '00:00:00:{:02d}'.format(frame)
            elif re.match(tick_pattern, tc):
                ticks = int(re.match(tick_pattern, tc).groupdict()['Tick'])
                frame = self.ticks_to_frame(ticks, edit_rate)
                tc = re.sub(r':\d{3}$', ':{:02d}'.format(frame), tc)
            elif re.match(fract_pattern, tc):
                fract = int(re.match(fract_pattern, tc).groupdict()['Fract'])
                frame = int(float("0.{}".format(fract)) * edit_rate)
                tc = re.sub(r'\.\d{1,3}$', ':{:02d}'.format(frame), tc)

        return tc_to_frame(tc, edit_rate)

    def get_subtitle_uuid(self, xml_dict):
        if self.dcp.schema == 'SMPTE':
            uuid = xml_dict['SubtitleReel']['Id']
        else:
            uuid = xml_dict['DCSubtitle']['SubtitleID']

        return uuid

    def get_subtitle_fade_io(self, st, editrate):
        f_s = st.get('Subtitle@FadeUpTime')
        f_d = st.get('Subtitle@FadeDownTime')

        if all([f_s, f_d]):
            f_s = self.st_tc_frames(f_s, editrate)
            f_d = self.st_tc_frames(f_d, editrate)

        return f_s, f_d

    def get_font_path(self, xml_dict, folder):
        uri, path = None, None

        if self.dcp.schema == 'SMPTE':
            font_uri = self.get_subtitle_elem(xml_dict, 'LoadFont')
        else:
            font_uri = self.get_subtitle_elem(xml_dict, 'LoadFont@URI')

        if font_uri:
            path = os.path.join(folder, font_uri)

        return path, uri

    def check_subtitle_cpl_format(self, playlist, asset, folder):
        """ Subtitle format (related to DCP Standard) check. """
        _, asset = asset
        extension_by_schema = {
            'Interop': '.xml',
            'SMPTE': '.mxf'
        }
        ext = os.path.splitext(asset['Path'])[-1]

        if ext != extension_by_schema[self.dcp.schema]:
            raise CheckException("Wrong subtitle format for {} DCP".format(
                self.dcp.schema))

    def check_subtitle_cpl_xml(self, playlist, asset, folder):
        """ Subtitle XML file syntax and structure validation. """
        _, asset = asset
        asset_path = asset['Path']

        if asset_path.endswith('.xml'):
            path = os.path.join(self.dcp.path, asset_path)
            namespace = 'interop_subtitle'
            label = 'Interop'
        else:
            path = os.path.join(folder, os.path.splitext(asset['Path'])[0])
            namespace = asset['Probe']['NamespaceName']
            label = asset['Probe']['LabelSetType']

        if not os.path.exists(path):
            raise CheckException("Subtitle not found : {}".format(path))
        if not os.path.isfile(path):
            raise CheckException("Subtitle must be a file : {}".format(path))

        check_xml(path, namespace, label, self.dcp.schema)

    def check_subtitle_cpl_reel_number(self, playlist, asset, folder):
        """ Subtitle reel number coherence with CPL. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        _, asset = asset

        reel_no = self.get_subtitle_elem(st_dict, 'ReelNumber')
        reel_cpl = get_reel_for_asset(playlist, asset['Id'])['Position']

        if reel_no and reel_no != reel_cpl:
            raise CheckException("Subtitle file indicate Reel {} but actually "
                                 "used in Reel {}".format(reel_no, reel_cpl))

    def check_subtitle_cpl_language(self, playlist, asset, folder):
        """ Subtitle language coherence with CPL. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        _, asset = asset

        st_lang = self.get_subtitle_elem(st_dict, 'Language')
        st_lang_obj = pycountry.languages.lookup(st_lang)
        if not st_lang_obj:
            raise CheckException("Subtitle language from XML could not  "
                                 "be detected : {}".format(st_lang))

        cpl_lang = asset.get('Language')
        if not cpl_lang:
            return

        cpl_lang_obj = pycountry.languages.lookup(cpl_lang)
        if not cpl_lang_obj:
            raise CheckException("Subtitle language from CPL could not  "
                                 "be detected : {}".format(cpl_lang))

        if st_lang_obj != cpl_lang_obj:
            raise CheckException(
                "Subtitle language mismatch, CPL claims {} but XML {}".format(
                    cpl_lang_obj.name, st_lang_obj.name))

    def check_subtitle_cpl_font_ref(self, playlist, asset, folder):
        """ Subtitle font references check. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        if self.dcp.schema == 'SMPTE':
            font_id = self.get_subtitle_elem(st_dict, 'LoadFont@ID')
            font_ref = keys_by_name_dict(st_dict, 'Font@ID')
        else:
            font_id = self.get_subtitle_elem(st_dict, 'LoadFont@Id')
            font_ref = keys_by_name_dict(st_dict, 'Font@Id')

        for ref in font_ref:
            if ref != font_id:
                raise CheckException(
                    "Subtitle reference unknown font {} (loaded {})".format(
                        ref, font_id))

    def check_subtitle_cpl_font(self, playlist, asset, folder):
        """ Subtitle font file exists. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        path, uri = self.get_font_path(st_dict, folder)
        if not path:
            return

        if not os.path.exists(path):
            raise CheckException("Subtitle missing font file : {}".format(uri))

    def check_subtitle_cpl_font_size(self, playlist, asset, folder):
        """ Subtitle maximum font size. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        path, uri = self.get_font_path(st_dict, folder)
        if not path:
            return

        font_size = os.path.getsize(path)
        font_max_size = DCP_SETTINGS['subtitle']['font_max_size']

        if font_size > font_max_size:
            raise CheckException(
                "Subtitle font maximum size is {}, got {}".format(
                    human_size(font_max_size), human_size(font_size)))

    def check_subtitle_cpl_font_format(self, playlist, asset, folder):
        """ Subtitle font format validation. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        path, uri = self.get_font_path(st_dict, folder)
        if not path:
            return

        font_format = magic.from_file(path)
        allowed_formats = DCP_SETTINGS['subtitle']['font_formats']

        for f in allowed_formats:
            if font_format in f:
                return

        raise CheckException("Subtitle font format not valid : {}".format(
            font_format))

    # def check_subtitle_cpl_font_glyph(self, playlist, asset, folder):
    #     """ Check if font can render all glyphs (parsing the text used
    #         in subtitles to have the list of glyphs).
    #
    #         Note : To be implemented.
    #     """

    def check_subtitle_cpl_st_timing(self, playlist, asset, folder):
        """ Subtitle individual duration / fade time check. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        subtitles = keys_by_name_dict(st_dict, 'Subtitle')
        editrate = self.get_subtitle_editrate(asset, st_dict)

        for st in subtitles[0]:
            st_idx = st['Subtitle@SpotNumber']
            st_in, st_out = st['Subtitle@TimeIn'], st['Subtitle@TimeOut']
            dur = (
                self.st_tc_frames(st_out, editrate)
                - self.st_tc_frames(st_in, editrate))

            if dur <= 0:
                raise CheckException(
                    "Subtitle {} null or negative duration".format(st_idx))

            f_s, f_d = self.get_subtitle_fade_io(st, editrate)
            if f_s and f_s > dur:
                raise CheckException(
                    "Subtitle {} FadeUpTime longer than duration".format(
                        st_idx))
            if f_d and f_d > dur:
                raise CheckException(
                    "Subtitle {} FadeDownTime longer than duration".format(
                        st_idx))

    def check_subtitle_cpl_duration(self, playlist, asset, folder):
        """ Subtitle duration coherence with CPL. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        st_rate = self.get_subtitle_editrate(asset, st_dict)
        subtitles = keys_by_name_dict(st_dict, 'Subtitle')
        _, asset = asset

        last_tc = 0
        for st in subtitles[0]:
            st_out = self.st_tc_frames(st['Subtitle@TimeOut'], st_rate)
            if st_out > last_tc:
                last_tc = st_out

        cpl_rate = asset['EditRate']
        cpl_dur = asset['Duration']
        ratio_editrate = st_rate / cpl_rate
        last_tc_st = last_tc / ratio_editrate

        if last_tc_st > cpl_dur:
            reel_cpl = get_reel_for_asset(playlist, asset['Id'])['Position']
            raise CheckException(
                "Subtitle exceed track duration. Subtitle {} - Track {} "
                "- Reel {}".format(
                    frame_to_tc(last_tc_st, cpl_rate),
                    frame_to_tc(cpl_dur, cpl_rate),
                    reel_cpl))

    def check_subtitle_cpl_editrate(self, playlist, asset, folder):
        """ Subtitle editrate coherence with CPL. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        st_rate = self.get_subtitle_editrate(asset, st_dict)
        _, asset = asset
        cpl_rate = asset['EditRate']

        if self.dcp.schema == 'SMPTE':
            if st_rate != cpl_rate:
                raise CheckException(
                    "Subtitle EditRate mismatch, Subtitle claims {} but CPL "
                    "{}".format(st_rate, cpl_rate))

    def check_subtitle_cpl_uuid(self, playlist, asset, folder):
        """ Subtitle UUID coherence with CPL. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        st_uuid = self.get_subtitle_uuid(st_dict)
        _, asset = asset
        cpl_uuid = asset['Id']

        if self.dcp.schema == 'SMPTE':
            if st_uuid != cpl_uuid:
                raise CheckException(
                    "Subtitle UUID mismatch, Subtitle claims {} but CPL "
                    "{}".format(st_uuid, cpl_uuid))

    def check_subtitle_cpl_content(self, playlist, asset, folder):
        """ Subtitle individual structure check. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        subtitles = keys_by_name_dict(st_dict, 'Subtitle')
        for st in subtitles[0]:
            has_image = keys_by_name_dict(st, 'Image')
            has_text = keys_by_name_dict(st, 'Text')
            if not has_image and not has_text:
                raise CheckException(
                    "Subtitle {} element must define one Text or Image"
                    "".format(st['Subtitle@SpotNumber']))

    def check_subtitle_cpl_position(self, playlist, asset, folder):
        """ Subtitles vertical position (out of screen) check.

            VAlign="top", VPosition="0" : out of the top of the screen
            VAlign="bottom", VPosition="0" : some char like 'g' will be cut
        """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        subs = keys_by_name_dict(st_dict, 'Subtitle')
        flat_subs = [item for sublist in subs for item in sublist]

        for st in flat_subs:
            st_idx = st['Subtitle@SpotNumber']
            valign = keys_by_pattern_dict(st, ['@VAlign'])
            vpos = keys_by_pattern_dict(st, ['@VPosition'])

            for a, p in zip(valign, vpos):
                if a == 'top' and p == 0:
                    raise CheckException(
                        "Subtitle {} is out of screen (top)".format(st_idx))
                if a == 'bottom' and p == 0:
                    raise CheckException(
                        "Subtitle {} is nearly out of screen (bottom), some "
                        "characters will be cut".format(st_idx))

    def check_subtitle_cpl_image(self, playlist, asset, folder):
        """ Subtitle image element must reference a valid PNG file. """
        st_dict = self.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        # TODO : Implement the test for SMPTE
        if self.dcp.schema != 'Interop':
            return

        imgs = keys_by_name_dict(st_dict, 'Image')
        for img in imgs:
            if not os.path.exists(os.path.join(folder, img)):
                raise CheckException(
                    "Subtitle image reference {} not found in folder {}"
                    "".format(img, os.path.relpath(folder, self.dcp.path)))
