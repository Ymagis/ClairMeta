# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import re
import six
from collections import OrderedDict
from itertools import islice

from clairmeta.settings import DCP_SETTINGS


RULES_ORDER = [
    'FilmTitle',
    'ContentType',
    'ProjectorAspectRatio',
    'Language',
    'TerritoryRating',
    'AudioType',
    'Resolution',
    'Studio',
    'Date',
    'Facility',
    'Standard',
    'PackageType'
]

RULES = {
    '9.6': {
        'FilmTitle': r'(^[a-zA-Z0-9-]{1,14}$)',
        'ContentType':
            r'(^'
            '(?P<Type>FTR|EPS|TLR|TSR|PRO|TST|RTG-F|RTG-T|SHR|ADV|XSN|PSA|POL)'
            '(-(?P<Version>\d))?'
            '(-(?P<Temporary>Temp))?'
            '(-(?P<PreRelease>Pre))?'
            '(-(?P<RedBand>RedBand))?'
            '(-(?P<TheatreChain>[a-zA-Z0-9]))?'
            '(-(?P<Dimension>(2D|3D)))?'
            '(-(?P<MasteringLuminance>\d+fl))?'
            '(-(?P<FrameRate>\d+))?'
            '(-(?P<DolbyVision>DVis))?'
            '(-(?P<EclairColor>EC))?'
            '$)',
        'ProjectorAspectRatio':
            r'(^'
            '(?P<AspectRatio>F|S|C)'
            '(-(?P<ImageAspectRatio>\d{1,3}))?'
            '$)',
        'Language':
            r'(^'
            '(?P<AudioLanguage>[A-Z]{2,3})'
            '-(?P<SubtitleLanguage>[A-Za-z]{2,3})'
            '(-(?P<SubtitleLanguage2>[A-Za-z]{2,3}))?'
            '(-(?P<Caption>(CCAP|OCAP)))?'
            '$)',
        'TerritoryRating':
            r'(^'
            '(?P<ReleaseTerritory>([A-Z]{2,3}))'
            '(-(?P<LocalRating>[A-Z0-9\+]{1,3}))?'
            '$)',
        'AudioType':
            r'(^'
            '(?P<Channels>(10|20|51|71|MOS))'
            '(-(?P<HearingImpaired>HI))?'
            '(-(?P<VisionImpaired>VI))?'
            '(-(?P<SignLanguage>SL))?'
            '(-(?P<ImmersiveSound>(ATMOS|Atmos|AURO|DTS-X)))?'
            '(-(?P<MotionSimulator>(DBOX|Dbox)))?'
            '$)',
        'Resolution': r'(^2K|4K$)',
        'Studio': r'(^[A-Z0-9]{2,4}$)',
        'Date': r'(^\d{8}$)',
        'Facility': r'(^[A-Z0-9]{2,3}$)',
        'Standard':
            r'(^'
            '(?P<Schema>(IOP|SMPTE))'
            '(-(?P<Dimension>3D))?'
            '$)',
        'PackageType':
            r'(^'
            '(?P<Type>(OV|VF))'
            '(-(?P<Version>\d))?'
            '$)',
     }
 }


DEFAULT = ''
DEFAULTS = {
    'Temporary': False,
    'PreRelease': False,
    'RedBand': False,
    'DolbyVision': False,
    'EclairColor': False,
    'Caption': False,
    'HearingImpaired': False,
    'VisionImpaired': False,
    'SignLanguage': False,
    'ImmersiveSound': False,
    'MotionSimulator': False,
}


def parse_isdcf_string(str):
    """ Regex based check of ISDCF Naming convention.

        Digital Cinema Naming Convention as defined by ISDCF
        ISDCF : Inter Society Digital Cinema Forum
        DCNC : Digital Cinema Naming Convention
        See : http://isdcf.com/dcnc/index.html

        Args:
            str (str): ContentTitle to check.

        Returns:
            Tuple consisting of a dictionary of all extracted fiels and a list
            of errors.

    """
    fields_dict = {}
    error_list = []

    if not isinstance(str, six.string_types):
        error_list.append("ContentTitle invalid type")
        return fields_dict, error_list

    # Sort the fields to respect DCNC order
    # Note : in python3 we can declare an OrderedDict({...}) and the field
    # order is preserved so this is not needed, but not in python 2.7
    dcnc_version = DCP_SETTINGS['naming_convention']
    rules = OrderedDict(sorted(
        six.iteritems(RULES[dcnc_version]),
        key=lambda f: RULES_ORDER.index(f[0])))

    fields_dict = init_dict_isdcf(rules)
    fields_list = str.split('_')

    if len(fields_list) != 12:
        error_list.append(
            "ContentTitle should have 12 parts to be fully compliant with"
            " ISDCF naming convention version {}, {} part(s) found"
            .format(dcnc_version, len(fields_list)))

    # Parsing title with some robustness to missing / additionals fields
    # Find a match in nearby fields only
    max_field_shift = 3

    fields_matched = []

    for idx_field, field in enumerate(fields_list):
        matched = False

        for idx_rule, (name, regex) in enumerate(six.iteritems(rules)):
            pattern = re.compile(regex)
            match = re.match(pattern, field)

            if idx_field == 0 and not match:
                error_list.append(
                    "ContentTitle Film Name does not respect naming convention"
                    " rules : {}".format(field))
            elif match and idx_rule < max_field_shift:
                fields_dict[name].update(match.groupdict(DEFAULT))
            else:
                continue

            fields_dict[name]['Value'] = field
            fields_matched.append(name)
            sliced = islice(six.iteritems(rules), idx_rule + 1, None)
            rules = OrderedDict(sliced)
            matched = True
            break

        if not matched:
            error_list.append(
                "ContentTitle Part {} not matching any naming convention field"
                .format(field))

    for name, _ in six.iteritems(RULES[dcnc_version]):
        if name not in fields_matched:
            error_list.append(
                "Field {} not found in ContentTitle".format(name))

    fields_dict = post_parse_isdcf(fields_dict)
    return fields_dict, error_list


def init_dict_isdcf(rules):
    """ Initialize naming convention metadata dictionary.

        Args:
            rules (dict): Dictionary of the rules.
    """
    res = {}

    for (name, regex) in six.iteritems(rules):
        pattern = re.compile(regex)

        res[name] = {}
        res[name]['Value'] = ''
        res[name].update({k: DEFAULT for k in pattern.groupindex.keys()})

    return res


def post_parse_isdcf(fields):
    """ Use additional deduction rules to augment dictionary.

        Args:
            fields (dict): Dictionary of parsed ISDCF fields.

    """
    # Custom default values
    for field, groups in six.iteritems(fields):
        for key, value in six.iteritems(groups):
            if value == DEFAULT and key in DEFAULTS:
                fields[field][key] = DEFAULTS[key]

    # Adjust schema format
    schema = fields['Standard']['Schema']
    schema_map = {
        'SMPTE': 'SMPTE',
        'IOP': 'Interop'
    }
    if schema and schema in schema_map:
        fields['Standard']['Schema'] = schema_map[schema]

    # See Appendix 1. Subtitles
    st_lang = fields['Language'].get('SubtitleLanguage')
    has_subtitle = st_lang != '' and st_lang != 'XX'
    has_burn_st = fields['Language'].get('SubtitleLanguage', '').islower()
    fields['Language']['BurnedSubtitle'] = has_burn_st
    fields['Language']['Subtitle'] = has_subtitle

    return fields
