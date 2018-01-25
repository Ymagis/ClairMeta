# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_check_utils import check_xml


class Checker(CheckerBase):
    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

    def run_checks(self):
        for source in self.dcp._list_vol:
            checks = self.find_check('vol')
            [self.run_check(check, source, message=source['FileName'])
             for check in checks]

        return self.check_executions

    def check_vol_xml(self, vol):
        """ VolIndex XML syntax and structure check. """
        check_xml(
            vol['FilePath'],
            vol['Info']['VolumeIndex']['__xmlns__'],
            vol['Info']['VolumeIndex']['Schema'],
            self.dcp.schema)

    def check_vol_name(self, vol):
        """ VolIndex file name respect DCP standard. """
        schema = vol['Info']['VolumeIndex']['Schema']
        mandatory_name = {
            'Interop': 'VOLINDEX',
            'SMPTE': 'VOLINDEX.xml'
        }

        if mandatory_name[schema] != vol['FileName']:
            raise CheckException(
                "{} VolIndex must be named {}, got {} instead".format(
                    schema, mandatory_name[schema], vol['FileName']))
