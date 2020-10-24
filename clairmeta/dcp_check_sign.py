# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
import re
import base64
import hashlib
from datetime import datetime
from OpenSSL import crypto
from cryptography.hazmat.primitives import serialization
from cryptography.x509.name import _ASN1Type

from clairmeta.settings import DCP_SETTINGS
from clairmeta.utils.xml import canonicalize_xml
from clairmeta.utils.sys import all_keys_in_dict
from clairmeta.dcp_check import CheckerBase, CheckException


class Checker(CheckerBase):
    """ This implement XML Signature validation.

        Check D-Cinema Certificate compliance. Steps follow SMPTE ST 430-2
        2006 : D-Cinema Operations - Digital Certificate, section 6.2.
    """

    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

        self.init_context()

    def init_context(self):
        self.context_certificate = ''
        # Minimal certificate chain length or zero for bypass check
        self.context_chain_length = 0
        self.context_role = 'CS'
        # Time string (YYYYMMDDhhmmssZ)
        # Special values :
        # - Empty string : no time validity check
        # - 'NOW' : use current time
        self.context_time = 'NOW'
        self.context_trusted_certificates = []
        self.context_revoked_certificates_id = []
        self.context_revoked_public_keys = []

        # Interop DCP can be signed with SMPTE compliant certificate
        self.certif_sig_algorithm_map = {
            'SMPTE': ['sha256WithRSAEncryption'],
            'Interop': ['sha256WithRSAEncryption', 'sha1WithRSAEncryption'],
            'Unknown': 'sha256WithRSAEncryption'
        }

        self.sig_algorithm_map = {
            'SMPTE': 'sha256WithRSAEncryption',
            'Interop': 'sha1WithRSAEncryption',
            'Unknown': 'sha256WithRSAEncryption'
        }

        self.sig_func_map = {
            'SMPTE': hashlib.sha256,
            'Interop': hashlib.sha1,
            'Unknown': hashlib.sha256,
        }

        self.digest_func = hashlib.sha1

        self.sig_ns_map = {
            'SMPTE': DCP_SETTINGS['xmluri']['smpte_sig'],
            'Interop': DCP_SETTINGS['xmluri']['interop_sig'],
            'Unknown': DCP_SETTINGS['xmluri']['smpte_sig']
        }

    def issuer_to_str(self, issuer):
        """ String representation of X509Name object. """
        # Note : what are the escapes rule here ?
        issuer_dn = issuer.dnQualifier.replace('+', '\+')
        return "dnQualifier={},CN={},OU={},O={}".format(
            issuer_dn, issuer.CN, issuer.OU, issuer.O)

    def issuer_match(self, issuer_a, issuer_b):
        """ Compare two distinguished name. """
        issuers = []
        for issuer in [issuer_a, issuer_b]:
            fields = {}
            for field in issuer.split(','):
                k, v = field.split('=', 1)
                fields[k] = v
            issuers.append(fields)

        return issuers[0] == issuers[1]

    def certif_der_decoding(self, cert):
        # 1. ASN.1 DER decoding rules
        try:
            certif = base64.b64decode(cert['X509Certificate'])
            X509 = crypto.load_certificate(crypto.FILETYPE_ASN1, certif)
            return X509
        except (crypto.Error) as e:
            raise CheckException("Invalid certificate encoding : {}".format(
                str(e)))

    def certif_ext_map(self, cert):
        extensions_map = {}

        for ext_index in range(cert.get_extension_count()):
            ext = cert.get_extension(ext_index)
            ext_name = ext.get_short_name().decode("utf-8")
            extensions_map[ext_name] = ext

        return extensions_map

    def run_checks(self):
        sources = self.dcp._list_pkl + self.dcp._list_cpl

        for source in sources:
            asset_stack = [source['FileName']]

            if 'PackingList' in source['Info']:
                source_xml = source['Info']['PackingList']
            else:
                source_xml = source['Info']['CompositionPlaylist']

            if not all_keys_in_dict(source_xml, ['Signer', 'Signature']):
                continue

            self.cert_list = []
            self.cert_store = crypto.X509Store()
            self.cert_chains = source_xml['Signature']['KeyInfo']['X509Data']

            for index, cert in reversed(list(enumerate(self.cert_chains))):
                cert_x509 = self.certif_der_decoding(cert)
                self.cert_store.add_cert(cert_x509)
                self.cert_list.append(cert_x509)

                stack = asset_stack + ["Certificate {}".format(
                    cert_x509.get_serial_number())]

                [self.run_check(check, cert_x509, index, stack=stack)
                 for check in self.find_check('certif')]

                [self.run_check(check, cert_x509, cert, stack=stack)
                 for check in self.find_check('xml_certif')]

            checks = self.find_check('sign')
            [self.run_check(check, source_xml, stack=asset_stack)
             for check in checks]

            checks = self.find_check('document')
            [self.run_check(check, source_xml,
                source['FilePath'], stack=asset_stack)
             for check in checks]

        return self.checks

    def check_certif_version(self, cert, index):
        """ Certificate version check (X509 v3).

            Reference :
                SMPTE 430-2-2017 6.2 2
        """
        if cert.get_version() != crypto.x509.Version.v3.value:
            raise CheckException("Invalid certificate version")

    def check_certif_extensions(self, cert, index):
        """ Certificate mandatory extensions check.

            Reference :
                SMPTE 430-2-2017 6.2 3
        """
        extensions_map = self.certif_ext_map(cert)
        required_extensions = [
            'basicConstraints',
            'keyUsage',
            'subjectKeyIdentifier',
            'authorityKeyIdentifier',
        ]

        # 3.a Required extensions are present
        for ext_name in required_extensions:
            if ext_name not in extensions_map:
                raise CheckException(
                    "Missing required extension marked : {}".format(ext_name))

        # 3.b Unknown extensions marked critical
        for ext_name, ext in six.iteritems(extensions_map):
            is_known = ext_name in required_extensions
            is_critical = ext.get_critical() != 0
            if not is_known and is_critical:
                raise CheckException("Unknown extension marked as critical : "
                                     "{}".format(ext_name))

    def check_certif_fields(self, cert, index):
        """ Certificate mandatory fields check.

            Reference :
                SMPTE 430-2-2017 6.2 4
        """
        # 4. Missing required fields
        # Fields : Non signed part
        # SignatureAlgorithm SignatureValue
        # Fields : signed part
        # Version SerialNumber Signature Issuer Subject Validity
        # SubjectPublicKeyInfo AuthorityKeyIdentifier KeyUsage BasicConstraint
        if not isinstance(cert.get_issuer(), crypto.X509Name):
            raise CheckException("Missing Issuer field")
        if not isinstance(cert.get_subject(), crypto.X509Name):
            raise CheckException("Missing Subject field")

    def check_certif_fields_encoding(self, cert, index):
        """ Certificate Issuer and Subject attributes encoding check.

            Dn, O, OU and CN fields shall be of type PrintableString.

            Reference :
                SMPTE 430-2-2017 5.3.1, 5.3.2, 5.3.3, 5.3.4
        """
        cert = cert.to_cryptography()
        fields = {
            'Subject': cert.subject,
            'Issuer': cert.issuer
        }

        for name, field in six.iteritems(fields):
            for a in field:
                if a._type != _ASN1Type.PrintableString:
                    type_str = str(a._type).split('.')[-1]
                    raise CheckException(
                        "{} {} field encoding should be PrintableString"
                        ", got {}".format(name, a.oid._name, type_str))

    def check_certif_basic_constraint(self, cert, index):
        """ Certificate basic constraint check.

            Reference :
                SMPTE 430-2-2017 6.2 5
        """
        # 5. Check BasicConstraint
        extensions_map = self.certif_ext_map(cert)
        bc = str(extensions_map['basicConstraints'])

        is_ca = index > 0
        is_leaf = not is_ca

        if re.search('CA:TRUE', bc) and is_leaf:
            raise CheckException("CA True in leaf certificate")
        if re.search('CA:FALSE', bc) and is_ca:
            raise CheckException("CA False in authority certificate")
        if re.search('CA:TRUE', bc) and not re.search(r'pathlen:\d+', bc):
            raise CheckException("CA True and Pathlen absent or not >= 0")
        if re.search('CA:FALSE', bc) and re.search(r'pathlen:[^0]', bc):
            raise CheckException("CA False and Pathlen present or non-zero")

    def check_certif_key_usage(self, cert, index):
        """ Certificate key usage check.

            Reference :
                SMPTE 430-2-2017 6.2 6
        """
        # 6. Check KeyUsage
        extensions_map = self.certif_ext_map(cert)
        keyUsage = str(extensions_map['keyUsage'])
        keys = [k for k in keyUsage.split(', ')]

        is_ca = index > 0
        is_leaf = not is_ca

        if is_leaf:
            required_keys = ['Digital Signature', 'Key Encipherment']
            missing_keys = [k for k in required_keys if k not in keys]
            illegal_keys = ['Certificate Sign', 'CRL Sign']
            illegal_keys = [k for k in keys if k in illegal_keys]
        if is_ca:
            required_keys = ['Certificate Sign']
            authorized_keys = ['Certificate Sign', 'CRL Sign']
            missing_keys = [k for k in required_keys if k not in keys]
            illegal_keys = [k for k in keys if k not in authorized_keys]

        if missing_keys:
            raise CheckException("Missing flags in KeyUsage : {}".format(
                ', '.join(missing_keys)))
        if illegal_keys:
            raise CheckException("Illegal flags in KeyUsage : {}".format(
                ', '.join(illegal_keys)))

    def check_certif_organization_name(self, cert, index):
        """ Certificate organization name check.

            Reference :
                SMPTE 430-2-2017 6.2 7
        """
        # 7. Check OrganizationName
        if cert.get_issuer().O == '':
            raise CheckException("Missing OrganizationName in Issuer name")
        if cert.get_subject().O == '':
            raise CheckException("Missing OrganizationName in Subject name")
        if cert.get_subject().O != cert.get_issuer().O:
            raise CheckException(
                "OrganizationName mismatch for Issuer and Subject")

    def check_certif_role(self, cert, index):
        """ Certificate role check.

            Reference :
                SMPTE 430-2-2017 6.2 8
        """
        # 8. Check Role
        cn = cert.get_subject().CN
        roles_str = cn.split('.', 1)[0]
        roles = roles_str.split()

        is_ca = index > 0
        is_leaf = not is_ca

        if is_leaf and self.dcp.schema == 'SMPTE':
            if not roles:
                raise CheckException(
                    "Missing role in CommonName ({})".format(cn))
            if self.context_role not in roles:
                raise CheckException(
                    "Expecting {} role in CommonName ({})"
                    .format(self.context_role, cn))
        if is_ca and roles:
            raise CheckException(
                "Role(s) found in authority certificate CommonName ({})"
                .format(cn))

    def check_certif_multi_role(self, cert, index):
        """ Leaf certificate role check.

            See https://github.com/wolfgangw/backports/issues/80

            Reference :
                DCI Spec 1.3 9.4.3.5
        """
        cn = cert.get_subject().CN
        roles_str = cn.split('.', 1)[0]
        roles = roles_str.split()

        is_ca = index > 0
        is_leaf = not is_ca

        if is_leaf and self.dcp.schema == 'SMPTE':
            if roles and len(roles) > 1:
                raise CheckException(
                    "Superfluous roles found in CommonName ({})".format(cn))

    def check_certif_date(self, cert, index):
        """ Certificate date validation.

            Reference :
                SMPTE 430-2-2017 6.2 9
        """
        # 9. Check time validity
        # Note : Date are formatted in ASN.1 Time YYYYMMDDhhmmssZ
        time_format = '%Y%m%d%H%M%SZ'

        if self.context_time == 'NOW':
            validity_time = datetime.now()
        elif self.context_time != '':
            validity_time = datetime.strptime(self.context_time, time_format)

        if self.context_time:
            not_before_str = cert.get_notBefore().decode("utf-8")
            not_before = datetime.strptime(not_before_str, time_format)
            not_after_str = cert.get_notAfter().decode("utf-8")
            not_after = datetime.strptime(not_after_str, '%Y%m%d%H%M%SZ')

            if validity_time < not_before or validity_time > not_after:
                raise CheckException("Certificate is not valid at this time")

    def check_certif_signature_algorithm(self, cert, index):
        """ Certificate signature algorithm check.

            Reference :
                SMPTE 430-2-2017 6.2 10
        """
        # 10. Signature Algorithm
        signature_algorithm = cert.get_signature_algorithm().decode("utf-8")
        expected = self.certif_sig_algorithm_map[self.dcp.schema]

        if signature_algorithm not in expected:
            raise CheckException(
                "Invalid Signature Algorithm, expected {} but got {}".format(
                    expected, signature_algorithm))

    def check_certif_rsa_validity(self, cert, index):
        """ Certificate characteristics (RSA 2048, 65537 exp) check.

            Reference :
                SMPTE 430-2-2017 6.2 11
                SMPTE 430-2-2017 5.2
        """
        # 11. Subject's PublicKey RSA validity
        expected_type = crypto.TYPE_RSA
        expected_size = 2048
        expected_exp = 65537

        key_type = cert.get_pubkey().type()
        key_size = cert.get_pubkey().bits()
        key_exp = cert.get_pubkey().to_cryptography_key().public_numbers().e

        if key_type != expected_type:
            raise CheckException("Subject's public key shall be an RSA key")
        if key_size != expected_size:
            raise CheckException(
                "Subject's public key invalid size, expected {} but got {}"
                "".format(expected_size, key_size))
        if key_exp != expected_exp:
            raise CheckException(
                "Subject's public key invalid public exponent, \
                 expected {} but got {}".format(
                    expected_exp, key_exp))

    def check_certif_revokation_list(self, cert, index):
        """ Certificate revokation list check.

            Reference :
                SMPTE 430-2-2017 6.2 12
        """
        # 12. Revokation list check
        # - Subject public key
        # - Issuer or certificate serial number
        if (self.context_revoked_certificates_id or
                self.context_revoked_public_keys):
            raise CheckException("Revokation list check not implemented")

    def check_certif_publickey_thumbprint(self, cert, index):
        """ Certificate public key thumbprint check.

            Reference :
                SMPTE 430-2-2017 6.2 13
        """
        # 13. Subject's public key thumb print match dnQualifier
        dn_thumbprint = cert.get_subject().dnQualifier.encode("utf-8")
        key_bits = cert.get_pubkey().to_cryptography_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.PKCS1)
        key_thumbprint = base64.b64encode(hashlib.sha1(key_bits).digest())

        if not dn_thumbprint:
            raise CheckException("dnQualifier must be present")
        if dn_thumbprint != key_thumbprint:
            raise CheckException(
                "dnQualifier mismatch, expected {} but got {}".format(
                    key_thumbprint, dn_thumbprint))

    # def check_certif_authority(self, cert, index):
    #     # 14. AuthorityKeyIdentifier
    #     # Lookup issuer certificate using AuthorityKeyIdentifier Attribute
    #     # Where to lookup ?
    #     # (extensions_map['authorityKeyIdentifier'])

    def check_certif_signature(self, cert, index):
        """ Certificate signature check.

            Reference :
                SMPTE 430-2-2017 6.2 15
        """
        # 15. Validate signature using local issuer
        # Note : use openssl StoreContext object which should do this plus a
        # bunch of other checks.
        try:
            store_ctx = crypto.X509StoreContext(self.cert_store, cert)
            store_ctx.verify_certificate()
        except crypto.X509StoreContextError as e:
            raise CheckException(
                "Certificate signature check failure : {}".format(str(e)))

    def check_xml_certif_serial_coherence(self, cert, xml_cert):
        """ XML / Certificate serial number coherence.

            Reference : N/A
        """
        # i. Serial number check
        xml_serial = xml_cert['X509IssuerSerial']['X509SerialNumber']
        if xml_serial != cert.get_serial_number():
            raise CheckException(
                "Serial number mismatch, expected {} but got {}".format(
                    cert.get_serial_number(), xml_serial))

    def check_xml_certif_issuer_coherence(self, cert, xml_cert):
        """ XML / Certificate Issuer coherence.

            Reference : N/A
        """
        # ii. Issuer name check
        xml_issuer = xml_cert['X509IssuerSerial']['X509IssuerName']
        issuer_str = self.issuer_to_str(cert.get_issuer())
        if not self.issuer_match(xml_issuer, issuer_str):
            raise CheckException(
                "IssuerName mismatch, expected {} but got {}".format(
                    issuer_str, xml_issuer))

    def check_sign_chain_length(self, source):
        """ Certificates minimum chain length.

            Reference :
                SMPTE 430-2-2017 6.2 16
        """
        # 16. Chain length
        if (self.context_chain_length and
                len(self.cert_chains) < self.context_chain_length):
            raise CheckException(
                "Certificate chain length should be at least {} long, \
                 got {}".format(
                    self.context_chain_length, len(self.cert_chains)))

    def check_sign_chain_coherence(self, source):
        """ Certificates chain coherence.

            Reference :
                SMPTE 430-2-2017 6.2 17, 18, 19
        """
        for index in range(1, len(self.cert_list)):
            parent, child = self.cert_list[index-1], self.cert_list[index]

            # 17. Child Issuer match parent Subject
            if child.get_issuer() != parent.get_subject():
                raise CheckException(
                    "Certificate chain issuer / subject mismatch")

            # 18. Validity date of child contained in parent date
            child_A = datetime.strptime(
                child.get_notBefore().decode("utf-8"), '%Y%m%d%H%M%SZ')
            child_B = datetime.strptime(
                child.get_notAfter().decode("utf-8"), '%Y%m%d%H%M%SZ')
            parent_A = datetime.strptime(
                parent.get_notBefore().decode("utf-8"), '%Y%m%d%H%M%SZ')
            parent_B = datetime.strptime(
                parent.get_notAfter().decode("utf-8"), '%Y%m%d%H%M%SZ')

            if child_A < parent_A:
                raise CheckException(
                    "Start date of the child certificate shall be \
                    identical to or later than the start date of the parent \
                    certificate")

            if child_B > parent_B:
                raise CheckException(
                    "End date of the child certificate shall be \
                    identical to or earlier than the end date of the parent \
                    certificate")

            # 19. Root certificate shall appear in trusted certificate list
            if self.context_trusted_certificates:
                raise CheckException("Trusted list check not implemented")

    def check_sign_chain_coherence_signature_algorithm(self, source):
        """ Certificates chain coherence.

            Reference : N/A
        """
        sign_alg_set = set(
            [c.get_signature_algorithm() for c in self.cert_list])
        if len(sign_alg_set) > 1:
            raise CheckException(
                "Certificate chain contains certificates "
                "signed with different algorithm")

    def check_sign_signature_algorithm(self, source):
        """ XML signature algorithm check.

            Reference : N/A
        """
        # Additionnal. XML coherence checks
        signed_info = source['Signature']['SignedInfo']

        # Signature algorithm
        sig = signed_info['SignatureMethod@Algorithm']
        if self.sig_ns_map[self.dcp.schema] != sig:
            raise CheckException(
                "Invalid Signature Algorithm, expected {} but got {}".format(
                    self.sig_ns_map[self.dcp.schema], sig))

    def check_sign_canonicalization_algorithm(self, source):
        """ XML canonicalization algorithm check.

            Reference : N/A
        """
        signed_info = source['Signature']['SignedInfo']
        # Canonicalization algorithm
        can = signed_info['CanonicalizationMethod@Algorithm']
        if can != DCP_SETTINGS['xmluri']['c14n']:
            raise CheckException("Invalid canonicalization method")

    def check_sign_transform_algorithm(self, source):
        """ XML signature transform algorithm check.

            Reference : N/A
        """
        signed_info = source['Signature']['SignedInfo']
        # Transform alogrithm
        trans = signed_info['Reference']['Transforms']['Transform@Algorithm']
        if trans != DCP_SETTINGS['xmluri']['enveloped_sig']:
            raise CheckException("Invalid transform method")

    def check_sign_digest_algorithm(self, source):
        """ XML signature digest method check.

            Reference : N/A
        """
        signed_info = source['Signature']['SignedInfo']
        # Digest algorithm
        trans = signed_info['Reference']['DigestMethod@Algorithm']
        if trans != DCP_SETTINGS['xmluri']['sha1']:
            raise CheckException("Invalid digest method")

    def check_sign_issuer_name(self, source):
        """ XML signature issuer name check.

            Reference : N/A
        """
        signer = source['Signer']['X509Data']['X509IssuerSerial']
        # Signer Issuer Name
        issuer_dn = self.issuer_to_str(self.cert_list[-1].get_issuer())
        if not self.issuer_match(signer['X509IssuerName'], issuer_dn):
            raise CheckException("Invalid Signer Issuer Name")

    def check_sign_issuer_serial(self, source):
        """ XML signature serial number check.

            Reference : N/A
        """
        sig = source['Signer']['X509Data']['X509IssuerSerial']
        # Signer Serial number
        if sig['X509SerialNumber'] != self.cert_list[-1].get_serial_number():
            raise CheckException("Invalid Signer Serial Number")

    def check_document_signature(self, source, path):
        """ Digital signature validation.

            Reference :
                SMPTE 429-7-2006 6.13
                SMPTE 429-8-2007 5.10
                RFC 3275 https://www.ietf.org/rfc/rfc3275.txt
                RFC 4051 https://tools.ietf.org/html/rfc4051
        """
        # Check digest (XML document hash)
        signed_info = source['Signature']['SignedInfo']
        xml_digest = signed_info['Reference']['DigestValue']
        c14n_doc = canonicalize_xml(
            path,
            ns=DCP_SETTINGS['xmlns']['xmldsig'],
            strip='{*}Signature')

        c14n_digest = base64.b64encode(self.digest_func(c14n_doc).digest())
        c14n_digest = c14n_digest.decode("utf-8")
        if xml_digest != c14n_digest:
            raise CheckException(
                "XML Digest mismatch, signature can't be checked")

        # Check signature (XML document hash encrypted with certifier
        # private key)
        c14n_sign = canonicalize_xml(
            path,
            root='SignedInfo',
            ns=DCP_SETTINGS['xmlns']['xmldsig'])

        xml_sig = ''.join(source['Signature']['SignatureValue'].split('\n'))
        xml_sig = base64.b64decode(xml_sig)

        try:
            crypto.verify(
                self.cert_list[-1],
                xml_sig,
                c14n_sign,
                self.sig_algorithm_map[self.dcp.schema])
        except crypto.Error as e:
            raise CheckException("Signature validation failed")
