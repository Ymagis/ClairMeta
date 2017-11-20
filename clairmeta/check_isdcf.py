# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import re
import six
from collections import OrderedDict

from clairmeta.dcp_check import CheckException
from clairmeta.settings import DCP_SETTINGS


RULES_ORDER = [
    'film_title',
    'content_type',
    'projector_aspect_ratio',
    'language',
    'territory_rating',
    'audio_type',
    'resolution',
    'studio',
    'date',
    'facility',
    'standard',
    'package_type'
]

RULES = {
    '9.3': {
        'film_title': r'(^[a-zA-Z0-9-]{1,14}$)',
        'content_type':
            r'(^'
            '(?P<Type>FTR|TLR|TSR|PRO|TST|RTG-F|RTG-T|SHR|ADV|XSN|PSA|POL)'
            '(-(?P<Version>\d))?'
            '(-(?P<Temporary>Temp))?'
            '(-(?P<PreRelease>Pre))?'
            '(-(?P<RedBand>RedBand))?'
            '(-(?P<TheatreChain>[a-zA-Z0-9]))?'
            '(-(?P<Dimension>(2D|3D)))?'
            '(-(?P<MasteringLuminance>\d+fl))?'
            '(-(?P<FrameRate>\d+))?'
            '(-(?P<DolbyVision>DVIs))?'
            '$)',
        'projector_aspect_ratio':
            r'(^'
            '(?P<AspectRatio>F|S|C)'
            '(-(?P<ImageAspectRatio>\d{1,3}))?'
            '$)',
        'language':
            r'(^'
            '(?P<AudioLanguage>[A-Z]{2,3})'
            '-(?P<SubtitleLanguage>[A-Za-z]{2,3})'
            '(-(?P<SubtitleLanguage2>[A-Za-z]{2,3}))?'
            '(-(?P<Caption>(CCAP|OCAP)))?'
            '$)',
        'territory_rating':
            r'(^'
            '(?P<ReleaseTerritory>([A-Z]{2,3}))'
            '(-(?P<LocalRating>[A-Z0-9\+]{1,3}))?'
            '$)',
        'audio_type':
            r'(^'
            '(?P<Channels>(10|20|51|61|71|MOS))'
            '(-(?P<HearingImpaired>HI))?'
            '(-(?P<VisionImpaired>VI))?'
            '(-(?P<ImmersiveSound>(ATMOS|AURO|DTS-X)))?'
            '(-(?P<MotionSimulator>DBOX))?'
            '$)',
        'resolution': r'(^2K|4K$)',
        'studio': r'(^[A-Z0-9]{2,4}$)',
        'date': r'(^\d{8}$)',
        'facility': r'(^[A-Z0-9]{2,3}$)',
        'standard':
            r'(^'
            '(?P<Schema>(IOP|SMPTE))'
            '(-(?P<Dimension>3D))?'
            '$)',
        'package_type':
            r'(^'
            '(?P<Type>(OV|VF))'
            '(-(?P<Version>\d))?'
            '$)',
     }
 }


def parse_isdcf_string(str):
    """ Regex based check of ISDCF Naming convention.

        Digital Cinema Naming Convention as defined by ISDCF
        ISDCF : Inter Society Digital Cinema Forum
        DCNC : Digital Cinema Naming Convention
        See : http://isdcf.com/dcnc/index.html

        Args:
            str (str): ContentTitle to check.

        Raises:
            CheckException: Basic parsing failed.

    """
    fields_list = str.split('_')
    if len(fields_list) != 12:
        raise CheckException("ContentTitle must have 12 parts")

    # Sort the fields to respect DCNC order
    # Note : in python3 we can declare an OrderedDict({...}) and the field
    # order is preserved so this is not needed, but not in python 2.7
    dcnc_version = DCP_SETTINGS['naming_convention']
    rules = OrderedDict(sorted(
        six.iteritems(RULES[dcnc_version]),
        key=lambda f: RULES_ORDER.index(f[0])))

    # Basic regex checking
    fields_dict = {}
    error_list = []

    for field, (name, regex) in zip(fields_list, six.iteritems(rules)):
        pattern = re.compile(regex)
        match = re.match(pattern, field)
        fields_dict[name] = {}
        fields_dict[name]['Value'] = field

        if match:
            fields_dict[name].update(match.groupdict())
        else:
            fields_dict[name].update({
                k: None for k in pattern.groupindex.keys()})
            error_list.append("ContentTitle Part {} : {} don't conform with "
                              "ISDCF naming convention version {}".format(
                               name, field, dcnc_version))

    fields_dict = post_parse_isdcf(fields_dict)
    return fields_dict, error_list


def post_parse_isdcf(fields):
    """ Use additional deduction rules to augment dictionary.

        Args:
            fields (dict): Dictionary of parsed ISDCF fields.

    """
    # Adjust schema format
    schema = fields['standard']['Schema']
    schema_map = {
        'SMPTE': 'SMPTE',
        'IOP': 'Interop'
    }
    if schema and schema in schema_map:
        fields['standard']['Schema'] = schema_map[schema]

    # See Appendix 1. Subtitles
    has_subtitle = fields['language'].get('SubtitleLanguage') != 'XX'
    has_burn_st = fields['language'].get('SubtitleLanguage', '').islower()
    fields['language']['BurnedSubtitle'] = has_burn_st
    fields['language']['Subtitle'] = has_subtitle

    return fields
