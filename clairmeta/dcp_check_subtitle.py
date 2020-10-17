# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import re
import six
import freetype
import pycountry

from clairmeta.utils.time import tc_to_frame, frame_to_tc
from clairmeta.utils.file import human_size
from clairmeta.utils.sys import keys_by_name_dict, keys_by_pattern_dict
from clairmeta.utils.xml import parse_xml
from clairmeta.utils.probe import unwrap_mxf
from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_check_utils import check_xml
from clairmeta.dcp_utils import (list_cpl_assets, get_reel_for_asset,
                                 get_contentkey_for_asset)
from clairmeta.settings import DCP_SETTINGS
from clairmeta.logger import get_log


class SubtitleUtils(object):

    def __init__(self, dcp):
        self.dcp = dcp

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
            return root.get(name, '')
        return ''

    def get_subtitle_editrate(self, asset, xml_dict):
        _, asset = asset

        if self.dcp.schema == 'SMPTE':
            tc_rate = xml_dict.get('SubtitleReel', {}).get('TimeCodeRate')
        else:
            tc_rate = asset['EditRate']

        return tc_rate

    def ticks_to_frame(self, tick, edit_rate):
        tick = int(tick)
        time_base = 1.0 / edit_rate

        # Ceiling division. Ugly, but avoids importing math.ceil
        # https://stackoverflow.com/questions/14822184/is-there-a-ceiling-equivalent-of-operator-in-python#17511341
        return int(-(-(tick * 0.004) // time_base))

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
            uuid = xml_dict.get('SubtitleReel', {}).get('Id')
        else:
            uuid = xml_dict.get('DCSubtitle', {}).get('SubtitleID')

        return uuid

    def get_subtitle_fade_io(self, st, editrate):
        f_s = st.get('Subtitle@FadeUpTime')
        f_d = st.get('Subtitle@FadeDownTime')

        f_s = self.st_tc_frames(f_s, editrate) if f_s else None
        f_d = self.st_tc_frames(f_d, editrate) if f_d else None

        return f_s, f_d

    def get_font_path(self, xml_dict, folder):
        uri, path = None, None

        if self.dcp.schema == 'SMPTE':
            uri = self.get_subtitle_elem(xml_dict, 'LoadFont').lower()
        else:
            uri = self.get_subtitle_elem(xml_dict, 'LoadFont@URI')

        if uri:
            path = os.path.join(folder, uri)

        return path, uri

    def extract_subtitle_text(self, node):
        text = []

        if isinstance(node, list):
            for elem in node:
                text += self.extract_subtitle_text(elem)
        elif isinstance(node, dict):
            if 'Font' in node:
                text = self.extract_subtitle_text(node['Font'])
            if 'Text' in node:
                text = self.extract_subtitle_text(node['Text'])
        else:
            text = [str(node)]

        return text


class Checker(CheckerBase):

    def __init__(self, dcp, profile):
        self.st_util = SubtitleUtils(dcp)
        super(Checker, self).__init__(dcp, profile)

    def run_checks(self):
        for cpl in self.dcp._list_cpl:
            assets = list_cpl_assets(
                cpl, filters=['Subtitle', 'ClosedCaption'],
                required_keys=['Path'])

            for asset in assets:
                stack = [cpl['FileName'], asset[1].get('Path', asset[1]['Id'])]

                checks = self.find_check('subtitle_dcp')
                [self.run_check(check, cpl, asset, stack=stack) for check in checks]

                checks = self.find_check('subtitle_cpl')
                self.run_checks_prepare(checks, cpl, asset)

        return self.checks

    def run_checks_prepare(self, checks, cpl, asset):
        _, asset_node = asset
        path = os.path.join(self.dcp.path, asset_node['Path'])
        can_unwrap = path.endswith('.mxf') and os.path.isfile(path)

        asset_stack = [cpl['FileName'], asset[1].get('Path', asset[1]['Id'])]

        if self.dcp.schema == 'SMPTE' and can_unwrap:
            unwrap_args = []
            try:
                if asset_node['Encrypted']:
                    k = get_contentkey_for_asset(self.dcp, asset_node)
                    unwrap_args = ['-k', k]
            except Exception as e:
                get_log().info('Subtitle inspection skipped : {}'.format(
                    str(e)))
                return

            with unwrap_mxf(path, args=unwrap_args) as folder:
                [self.run_check(check, cpl, asset, folder, stack=asset_stack)
                 for check in checks]

        elif self.dcp.schema == 'Interop':
            folder = os.path.dirname(path)
            [self.run_check(check, cpl, asset, folder, stack=asset_stack)
             for check in checks]

    def check_subtitle_dcp_format(self, playlist, asset):
        """ Subtitle format (related to DCP Standard) check.

            Reference :
                SMPTE ST 429-5
                Interop Closed Captions Packaging 1.9
        """
        _, asset = asset
        asset_path = asset['Path']
        extension_by_schema = {
            'Interop': '.xml',
            'SMPTE': '.mxf'
        }
        ext = os.path.splitext(asset['Path'])[-1].lower()

        if ext != extension_by_schema[self.dcp.schema]:
            raise CheckException("Wrong subtitle format for asset {}".format(
                asset_path))

    def check_subtitle_cpl_xml(self, playlist, asset, folder):
        """ Subtitle XML file syntax and structure validation.

            Reference :
                SMPTE ST 428-7
                Interop TI Subtitle Spec 1.1
        """
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
        """ Subtitle reel number coherence with CPL.

            Reference :
                SMPTE 428-7-2014 5.6
                Interop TI Subtitle Spec 1.1 2.5
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        _, asset = asset

        reel_no = self.st_util.get_subtitle_elem(st_dict, 'ReelNumber')
        reel_cpl = get_reel_for_asset(playlist, asset['Id'])['Position']

        if reel_no and reel_no != reel_cpl:
            raise CheckException("Subtitle file indicate Reel {} but actually "
                                 "used in Reel {}".format(reel_no, reel_cpl))

    def check_subtitle_cpl_language(self, playlist, asset, folder):
        """ Subtitle language coherence with CPL.

            Reference : N/A
        """
        def lookup_language(lang):
            """ Detect language from `lang` name. """
            if re.match(r"^[A-Za-z]{2}$", lang):
                return pycountry.languages.get(alpha_2=lang)
            else:
                return pycountry.languages.lookup(lang)

        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        _, asset = asset

        st_lang = self.st_util.get_subtitle_elem(st_dict, 'Language')
        if not st_lang:
            return

        try:
            st_lang_obj = lookup_language(st_lang)
        except LookupError:
            raise CheckException("Subtitle language from XML could not "
                                 "be detected : {}".format(st_lang))

        cpl_lang = asset.get('Language')
        if not cpl_lang:
            return

        cpl_lang_obj = lookup_language(cpl_lang)
        if not cpl_lang_obj:
            raise CheckException("Subtitle language from CPL could not "
                                 "be detected : {}".format(cpl_lang))

        if st_lang_obj != cpl_lang_obj:
            raise CheckException(
                "Subtitle language mismatch, CPL claims {} but XML {}".format(
                    cpl_lang_obj.name, st_lang_obj.name))

    def check_subtitle_cpl_loadfont(self, playlist, asset, folder):
        """ Text subtitle must contains one and only one LoadFont element.

            As specified in SMPTE 429-2 8.4.1, only exception is PNG based
            subtitles. SMPTE 428-7-2014 5.11.1 also specify that the LoadFont ID
            attribute shall be a string of one or more character. This is
            not enforced at the XSD schema level so we explicitly check it
            here.

            Reference :
                SMPTE ST 428-7-2014 5.11.1
                SMPTE ST 429-2-2013 8.4.1

        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        if self.dcp.schema == 'SMPTE':
            loadfont_attribute = "LoadFont@ID"
        else:
            loadfont_attribute = "LoadFont@Id"  # Interop

        text_elems = keys_by_name_dict(st_dict, 'Text')
        loadfont_elems = keys_by_name_dict(st_dict, loadfont_attribute)
        if text_elems and len(loadfont_elems) != 1:
            raise CheckException(
                "Text based subtitle shall contain one and only one "
                "LoadFont element, found {}".format(len(loadfont_elems)))
        if text_elems and not loadfont_elems[0]:
            raise CheckException("LoadFont element with an empty ID attribute")

    def check_subtitle_cpl_font_ref(self, playlist, asset, folder):
        """ Subtitle font references check.

            Reference :
                SMPTE ST 428-7-2014 5.11.1
                Interop TI Subtitle Spec 1.1 2.7
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        if self.dcp.schema == 'SMPTE':
            font_id = self.st_util.get_subtitle_elem(st_dict, 'LoadFont@ID')
            font_ref = keys_by_name_dict(st_dict, 'Font@ID')
        else:
            font_id = self.st_util.get_subtitle_elem(st_dict, 'LoadFont@Id')
            font_ref = keys_by_name_dict(st_dict, 'Font@Id')

        for ref in font_ref:
            if ref != font_id:
                raise CheckException(
                    "Subtitle reference unknown font {} (loaded {})".format(
                        ref, font_id))

    def check_subtitle_cpl_font(self, playlist, asset, folder):
        """ Subtitle font file exists.

            Reference : N/A
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        path, uri = self.st_util.get_font_path(st_dict, folder)
        if not path:
            return

        if not os.path.exists(path):
            raise CheckException("Subtitle missing font file : {}".format(uri))

    def check_subtitle_cpl_font_size(self, playlist, asset, folder):
        """ Subtitle maximum font size.

            Reference :
                Interop TI Subtitle Spec 1.1 2.7
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return
        path, uri = self.st_util.get_font_path(st_dict, folder)
        if not path:
            return
        if not os.path.exists(path):
            return

        font_size = os.path.getsize(path)
        font_max_size = DCP_SETTINGS['subtitle']['font_max_size']

        if font_size > font_max_size:
            raise CheckException(
                "Subtitle font maximum size is {}, got {}".format(
                    human_size(font_max_size), human_size(font_size)))

    def check_subtitle_cpl_font_glyph(self, playlist, asset, folder):
        """ Check for missing font glyphs.

            Reference : N/A
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        subtitles = keys_by_name_dict(st_dict, 'Subtitle')
        if not subtitles:
            return

        # See SMPTE ST 428-7-2014 sections 6.3 and 6.4 for possible
        # Subtitle Text and Font hierarchy. Note that here we just
        # recursively iterate to extract all relevant childs whitout
        # checking if the specific hierarchy is valid or not.
        all_text = self.st_util.extract_subtitle_text(subtitles[0])
        unique_chars = set()
        for text in all_text:
            for char in text:
                unique_chars.add(char)

        path, uri = self.st_util.get_font_path(st_dict, folder)
        if not path:
            return
        if not os.path.exists(path):
            return

        face = freetype.Face(path)
        font_chars = [six.unichr(c) for c, n in face.get_chars()]

        missing_glyphs = []
        for char in unique_chars:
            if char not in font_chars:
                missing_glyphs.append(char)

        if missing_glyphs:
            raise CheckException(
                "Font ({}) is missing required glyphs : {}"
                .format(os.path.basename(path), ", ".join(missing_glyphs)))


    def check_subtitle_cpl_st_timing(self, playlist, asset, folder):
        """ Subtitle individual duration / fade time check.

            Reference : N/A
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        subtitles = keys_by_name_dict(st_dict, 'Subtitle')
        editrate = self.st_util.get_subtitle_editrate(asset, st_dict)
        if not subtitles:
            return

        for st in subtitles[0]:
            st_idx = st['Subtitle@SpotNumber']
            st_in, st_out = st['Subtitle@TimeIn'], st['Subtitle@TimeOut']
            dur = (
                self.st_util.st_tc_frames(st_out, editrate)
                - self.st_util.st_tc_frames(st_in, editrate))

            if dur <= 0:
                raise CheckException(
                    "Subtitle {} null or negative duration".format(st_idx))

            f_s, f_d = self.st_util.get_subtitle_fade_io(st, editrate)
            if f_s and f_s > dur:
                raise CheckException(
                    "Subtitle {} FadeUpTime longer than duration".format(
                        st_idx))
            if f_d and f_d > dur:
                raise CheckException(
                    "Subtitle {} FadeDownTime longer than duration".format(
                        st_idx))

    def check_subtitle_cpl_duration(self, playlist, asset, folder):
        """ Subtitle duration coherence with CPL.

            Reference : N/A
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        st_rate = self.st_util.get_subtitle_editrate(asset, st_dict)
        subtitles = keys_by_name_dict(st_dict, 'Subtitle')
        _, asset = asset
        if not subtitles:
            return

        last_tc = 0
        for st in subtitles[0]:
            st_out = self.st_util.st_tc_frames(st['Subtitle@TimeOut'], st_rate)
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
        """ Subtitle editrate coherence with CPL.

            Reference : N/A
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        st_rate = self.st_util.get_subtitle_editrate(asset, st_dict)
        _, asset = asset
        cpl_rate = asset['EditRate']

        if self.dcp.schema == 'SMPTE':
            if st_rate != cpl_rate:
                raise CheckException(
                    "Subtitle EditRate mismatch, Subtitle claims {} but CPL "
                    "{}".format(st_rate, cpl_rate))

    def check_subtitle_cpl_uuid(self, playlist, asset, folder):
        """ Subtitle UUID coherence.

            For Interop, XML DCSubtitle/SubtitleID should match the CPL
            MainSubtitle/Id and the XML subfolder name should contain the Id.
            For SMPTE, XML SubtitleReel/Id should match the
            MXF ResourceId, here we rely on the fact that asdcp-info parser
            (As_02_TimedText parser) store the TimedTextDescriptor/ResourceID
            in a global AssetID key.

            Reference :
                SMPTE 429-5-2017
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        st_uuid = self.st_util.get_subtitle_uuid(st_dict).lower()
        _, asset = asset

        if self.dcp.schema == 'Interop':
            cpl_uuid = asset['Id'].lower()
            if st_uuid != cpl_uuid:
                raise CheckException(
                    "Subtitle UUID mismatch, Subtitle claims {} but CPL {}"
                    .format(st_uuid, cpl_uuid))
            folder_name = os.path.basename(folder).lower()
            if st_uuid not in folder_name:
                raise CheckException(
                    "Subtitle directory name unexpected, should contain {} but"
                    " got {}".format(st_uuid, folder_name))
        elif self.dcp.schema == 'SMPTE':
            resource_uuid = asset['Probe'].get('AssetID', "").lower()
            if resource_uuid != st_uuid:
                raise CheckException(
                    "Subtitle UUID mismatch, Subtitle claims {} but MXF "
                    "{}".format(st_uuid, resource_uuid))

    def check_subtitle_cpl_uuid_case(self, playlist, asset, folder):
        """ Subtitle UUID case mismatch. """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        st_uuid = self.st_util.get_subtitle_uuid(st_dict)
        _, asset = asset

        if self.dcp.schema == 'Interop':
            cpl_uuid = asset['Id']
            if st_uuid != cpl_uuid and st_uuid.lower() == cpl_uuid.lower():
                raise CheckException(
                    "Subtitle UUID case mismatch, Subtitle {} - CPL {}".format(
                        st_uuid, cpl_uuid))
            folder_name = os.path.basename(folder)
            if (st_uuid not in folder_name
               and st_uuid.lower() in folder_name.lower()):
                raise CheckException(
                    "Subtitle directory name case mismatch, Folder {} - CPL {}"
                    .format(st_uuid, folder_name))

    def check_subtitle_cpl_duplicated_uuid(self, playlist, asset, folder):
        """ Issue when using the same UUID for Subtitle XML and MXF.

            This can cause issue on certain hardware, eg. Dolby server using
            a version prior to 2.8.18, see patch notes extract below :
            Fixed an error where the server did not extract SMPTE timedtext
            (as in subtitles/captions) from the MXF file that was incorrectly
            created using the same universally unique identifier (UUID) for
            the MXF file and the main XML inside the MXF files. [DCPLYR-3418]

            Reference : N/A
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        st_uuid = self.st_util.get_subtitle_uuid(st_dict)
        _, asset = asset

        if self.dcp.schema == 'SMPTE':
            mxf_uuid = asset['Probe'].get('AssetUUID', "")
            if st_uuid == mxf_uuid:
                raise CheckException(
                    "Using the same UUID for Subtitle ID and MXF UUID can "
                    "cause issue on Dolby server prior to 2.8.18 firmware.")

    def check_subtitle_cpl_empty(self, playlist, asset, folder):
        """ Empty Subtitle file check.

            Reference : N/A
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        subtitles = keys_by_name_dict(st_dict, 'Subtitle')
        if not subtitles:
            raise CheckException("Subtitle file is empty")

    def check_subtitle_cpl_content(self, playlist, asset, folder):
        """ Subtitle individual structure check.

            Reference :
                Interop TI Subtitle Spec 1.1 2.9
                SMPTE 428-7-2014 6
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
        if not st_dict:
            return

        subtitles = keys_by_name_dict(st_dict, 'Subtitle')
        if not subtitles:
            return

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

            Reference :
                Interop TI Subtitle Spec 1.1 2.10
                SMPTE 428-7-2014 6.2.4
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
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
        """ Subtitle image element must reference a valid PNG file.

            Reference :
                Interop TI Subtitle Spec 1.1 2.17
        """
        st_dict = self.st_util.get_subtitle_xml(asset, folder)
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
