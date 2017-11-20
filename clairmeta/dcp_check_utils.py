# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
import magic
from datetime import datetime
from dateutil import parser

from clairmeta.logger import get_log
from clairmeta.utils.uuid import check_uuid
from clairmeta.utils.xml import validate_xml
from clairmeta.dcp_check import CheckException
from clairmeta.settings import DCP_SETTINGS


def get_schema(name):
    for k, v in six.iteritems(DCP_SETTINGS['xmlns']):
        if name == k or name == v:
            return v


def check_xml(xml_path, xml_ns, schema_type, schema_dcp):
    # Correct file type (magic number)
    xml_magic = magic.from_file(xml_path)
    if "XML" not in xml_magic:
        raise CheckException(
            "File type unknown, expected XML Document but got {}".format(
                xml_magic))

    # Correct namespace
    schema_id = get_schema(xml_ns)
    if not schema_id:
        raise CheckException("Namespace unknown : {}".format(xml_ns))

    # Coherence with package schema
    if schema_type != schema_dcp:
        raise CheckException(
            "Schema is not valid got {} but was expecting {}".format(
                schema_type, schema_dcp))

    # XSD schema validation
    try:
        validate_xml(xml_path, schema_id)
    except LookupError as e:
        get_log().info("Schema validation skipped : {}".format(xml_path))
    except Exception as e:
        raise CheckException("Schema validation error : {}".format(str(e)))


def check_issuedate(date):
    # As a reminder, date should be already correctly formatted as checked
    # by XSD validation.
    parse_date = parser.parse(date)
    now_date = datetime.now().replace(tzinfo=parse_date.tzinfo)

    if parse_date > now_date:
        raise CheckException("IssueDate is post dated : {}".format(
            parse_date))


def compare_uuid(uuid_to_check, uuid_reference):
    name, uuid = uuid_to_check
    name_ref, uuid_ref = uuid_reference

    if not check_uuid(uuid):
        raise CheckException("Invalid {} uuid found : {}".format(
            name, uuid))
    if uuid != uuid_ref:
        raise CheckException("Uuid {} ({}) not equal to {} ({})".format(
            name, uuid, name_ref, uuid_ref))
