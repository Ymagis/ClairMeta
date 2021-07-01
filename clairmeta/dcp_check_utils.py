# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
from datetime import datetime
from dateutil import parser

from clairmeta.logger import get_log
from clairmeta.utils.uuid import check_uuid
from clairmeta.utils.xml import validate_xml
from clairmeta.settings import DCP_SETTINGS


def get_schema(name):
    for k, v in six.iteritems(DCP_SETTINGS['xmlns']):
        if name == k or name == v:
            return v


def check_xml(checker, xml_path, xml_ns, schema_type, schema_dcp):
    # Correct namespace
    schema_id = get_schema(xml_ns)
    if not schema_id:
        checker.error("Namespace unknown : {}".format(xml_ns), "namespace")

    # Coherence with package schema
    if schema_type != schema_dcp:
        message = "Schema is not valid got {} but was expecting {}".format(
            schema_type, schema_dcp)
        checker.error(message, "schema_coherence")

    # XSD schema validation
    try:
        validate_xml(xml_path, schema_id)
    except LookupError as e:
        get_log().info("Schema validation skipped : {}".format(xml_path))
    except Exception as e:
        message = (
            "Schema validation error : {}\n"
            "Using schema : {}".format(str(e), schema_id))
        checker.error(message, "schema_validation")


def check_issuedate(checker, date):
    # As a reminder, date should be already correctly formatted as checked
    # by XSD validation.
    parse_date = parser.parse(date)
    now_date = datetime.now().replace(tzinfo=parse_date.tzinfo)

    if parse_date > now_date:
        checker.error("IssueDate is post dated : {}".format(parse_date))


def compare_uuid(checker, uuid_to_check, uuid_reference):
    name, uuid = uuid_to_check
    name_ref, uuid_ref = uuid_reference

    if not check_uuid(uuid):
        checker.error("Invalid {} uuid found : {}".format(name, uuid))
    if uuid.lower() != uuid_ref.lower():
        checker.error("Uuid {} ({}) not equal to {} ({})".format(
            name, uuid, name_ref, uuid_ref))
