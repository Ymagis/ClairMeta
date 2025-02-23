# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from dateutil import parser
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

from clairmeta.settings import DCP_SETTINGS
from clairmeta.utils.xml import canonicalize_xml
from clairmeta.utils.sys import all_keys_in_dict
from clairmeta.dcp_check import CheckerBase


class Checker(CheckerBase):
    """This implement XML Signature validation.

    Check D-Cinema Certificate compliance. Steps follow SMPTE ST 430-2
    2006 : D-Cinema Operations - Digital Certificate, section 6.2.
    """

    def __init__(self, dcp):
        super(Checker, self).__init__(dcp)

        self.init_context()

    def init_context(self):
        self.context_certificate = ""
        # Minimal certificate chain length or zero for bypass check
        self.context_chain_length = 0
        self.context_role = "CS"
        # Time string (YYYYMMDDhhmmssZ)
        self.time_format = "%Y%m%d%H%M%SZ"
        # Special values :
        # - Empty string : no time validity check
        # - 'NOW' : use current time
        self.context_time = ""
        self.context_trusted_certificates = []
        self.context_revoked_certificates_id = []
        self.context_revoked_public_keys = []

        # Interop DCP can be signed with SMPTE compliant certificate
        self.certif_sig_algorithm_map = {
            "SMPTE": ["sha256"],
            "Interop": ["sha256", "sha1"],
            "Unknown": "sha256",
        }

        self.sig_algorithm_map = {
            "SMPTE": hashes.SHA256(),
            "Interop": hashes.SHA1(),
            "Unknown": hashes.SHA256(),
        }

        self.sig_func_map = {
            "SMPTE": hashlib.sha256,
            "Interop": hashlib.sha1,
            "Unknown": hashlib.sha256,
        }

        self.digest_func = hashlib.sha1

        self.sig_ns_map = {
            "SMPTE": DCP_SETTINGS["xmluri"]["smpte_sig"],
            "Interop": DCP_SETTINGS["xmluri"]["interop_sig"],
            "Unknown": DCP_SETTINGS["xmluri"]["smpte_sig"],
        }

    def certif_der_decoding(self, cert):
        """Certificate ASN.1 DER decoding."""
        try:
            certif_bytes = base64.b64decode(cert["X509Certificate"])
            certif = x509.load_der_x509_certificate(certif_bytes)
        except Exception as e:
            self.error("Invalid certificate encoding : {}".format(str(e)))

        try:
            _ = certif.extensions
            valid_extensions = True
        except ValueError as e:
            valid_extensions = False
            self.error(
                "Error while parsing extensions, skipping checks for certificate {}: {}".format(
                    certif.serial_number, e
                ),
                "extensions",
                "Encountered non-conformant extensions encoding.\n"
                "  Has been observed on certificate's BasicConstraints extension, see https://github.com/pyca/cryptography/issues/3856",
            )

        return certif, valid_extensions

    def run_checks(self):
        sources = self.dcp._list_pkl + self.dcp._list_cpl

        for source in sources:
            asset_stack = [source["FileName"]]

            if "PackingList" in source["Info"]:
                source_xml = source["Info"]["PackingList"]
            else:
                source_xml = source["Info"]["CompositionPlaylist"]

            if not all_keys_in_dict(source_xml, ["Signer", "Signature"]):
                continue

            # See check_certif_date documentation note for rational.
            if "IssueDate" in source_xml:
                # No timezone information seems to be encoded in IssueDate time format
                issue_date = parser.parse(source_xml["IssueDate"])
                self.context_time = datetime.strftime(issue_date, self.time_format)

            self.cert_list = []
            self.cert_chains = source_xml["Signature"]["KeyInfo"]["X509Data"]

            for index, cert in reversed(list(enumerate(self.cert_chains))):
                cert_x509, cert_valid = self.run_check(self.certif_der_decoding, cert, stack=asset_stack)
                if not cert_x509:
                    continue

                self.cert_list.append(cert_x509)

                stack = asset_stack + ["Certificate {}".format(cert_x509.serial_number)]

                if cert_valid:
                    [
                        self.run_check(check, cert_x509, index, stack=stack)
                        for check in self.find_check("certif")
                    ]

                    [
                        self.run_check(check, cert_x509, cert, stack=stack)
                        for check in self.find_check("xml_certif")
                    ]

            if not self.cert_list:
                return self.checks

            checks = self.find_check("sign")
            [self.run_check(check, source_xml, stack=asset_stack) for check in checks]

            checks = self.find_check("document")
            [
                self.run_check(check, source_xml, source["FilePath"], stack=asset_stack)
                for check in checks
            ]

        return self.checks

    def check_certif_version(self, cert, index):
        """Certificate version check (X509 v3).

        References:
            SMPTE ST 430-2:2017 6.2 2
        """
        if cert.version != x509.Version.v3:
            self.error("Invalid certificate version")

    def check_certif_extensions(self, cert, index):
        """Certificate mandatory extensions check.

        References:
            SMPTE ST 430-2:2017 6.2 3
        """
        required_extensions = {
            x509.OID_BASIC_CONSTRAINTS: "basicConstraints",
            x509.OID_KEY_USAGE: "keyUsage",
            x509.OID_SUBJECT_KEY_IDENTIFIER: "subjectKeyIdentifier",
            x509.OID_AUTHORITY_KEY_IDENTIFIER: "authorityKeyIdentifier",
        }

        # 3.a Required extensions are present
        for oid, name in required_extensions.items():
            try:
                cert.extensions.get_extension_for_oid(oid)
            except x509.ExtensionNotFound:
                self.error("Missing required extension marked : {}".format(name))

        # 3.b Unknown extensions marked critical
        for ext in cert.extensions:
            is_known = ext.oid in required_extensions
            if not is_known and ext.critical:
                self.error(
                    "Unknown extension marked as critical : " "{}".format(ext._name)
                )

    def check_certif_fields(self, cert, index):
        """Certificate mandatory fields check.

        References:
            SMPTE ST 430-2:2017 6.2 4
        """
        # 4. Missing required fields
        # Fields : Non signed part
        # SignatureAlgorithm SignatureValue
        # Fields : signed part
        # Version SerialNumber Signature Issuer Subject Validity
        # SubjectPublicKeyInfo AuthorityKeyIdentifier KeyUsage BasicConstraint
        if not cert.issuer:
            self.error("Missing Issuer field")
        if not cert.subject:
            self.error("Missing Subject field")

    def check_certif_fields_encoding(self, cert, index):
        """Certificate Issuer and Subject attributes encoding check.

        Dn, O, OU and CN fields shall be of type PrintableString.

        References:
            SMPTE ST 430-2:2017 5.3.1, 5.3.2, 5.3.3, 5.3.4
        """
        fields = {"Subject": cert.subject, "Issuer": cert.issuer}

        for name, field in fields.items():
            for a in field:
                if a._type != x509.name._ASN1Type.PrintableString:
                    type_str = str(a._type).split(".")[-1]
                    self.error(
                        "{} {} field encoding should be PrintableString"
                        ", got {}".format(name, a.oid._name, type_str)
                    )

    def check_certif_basic_constraint(self, cert, index):
        """Certificate basic constraint check.

        References:
            SMPTE ST 430-2:2017 6.2 5
        """
        # 5. Check BasicConstraint
        bc = cert.extensions.get_extension_for_oid(x509.OID_BASIC_CONSTRAINTS).value

        is_ca = index > 0
        is_leaf = not is_ca

        if bc.ca and is_leaf:
            self.error("CA True in leaf certificate")
        if not bc.ca and is_ca:
            self.error("CA False in authority certificate")
        if bc.ca and (bc.path_length < 0 or bc.path_length is None):
            self.error("CA True and Pathlen absent or not >= 0")
        if not bc.ca and (bc.path_length != 0 and bc.path_length is not None):
            self.error("CA False and Pathlen present or non-zero")

    def check_certif_key_usage(self, cert, index):
        """Certificate key usage check.

        References:
            SMPTE ST 430-2:2017 6.2 6
        """
        # 6. Check KeyUsage
        keyUsage = cert.extensions.get_extension_for_oid(x509.OID_KEY_USAGE).value
        keys = []

        # Manually construct a list of all known keys found
        # There is probably a better way of doing this.
        if keyUsage.digital_signature:
            keys.append("Digital Signature")
        if keyUsage.content_commitment:
            keys.append("Content Commitment")
        if keyUsage.key_encipherment:
            keys.append("Key Encipherment")
        if keyUsage.data_encipherment:
            keys.append("Data Encipherment")
        if keyUsage.key_agreement:
            keys.append("Key agreement")
            if keyUsage.encipher_only:
                keys.append("Encipher Only")
            if keyUsage.decipher_only:
                keys.append("Decipher Only")
        if keyUsage.key_cert_sign:
            keys.append("Certificate Sign")
        if keyUsage.crl_sign:
            keys.append("CRL Sign")

        is_ca = index > 0
        is_leaf = not is_ca

        if is_leaf:
            required_keys = ["Digital Signature", "Key Encipherment"]
            missing_keys = [k for k in required_keys if k not in keys]
            illegal_keys = ["Certificate Sign", "CRL Sign"]
            illegal_keys = [k for k in keys if k in illegal_keys]
        if is_ca:
            required_keys = ["Certificate Sign"]
            authorized_keys = ["Certificate Sign", "CRL Sign"]
            missing_keys = [k for k in required_keys if k not in keys]
            illegal_keys = [k for k in keys if k not in authorized_keys]

        if missing_keys:
            self.error("Missing flags in KeyUsage : {}".format(", ".join(missing_keys)))
        if illegal_keys:
            self.error("Illegal flags in KeyUsage : {}".format(", ".join(illegal_keys)))

    def check_certif_organization_name(self, cert, index):
        """Certificate organization name check.

        References:
            SMPTE ST 430-2:2017 6.2 7
        """
        # 7. Check OrganizationName
        if (
            cert.issuer.get_attributes_for_oid(x509.OID_ORGANIZATION_NAME)[0].value
            == ""
        ):
            self.error("Missing OrganizationName in Issuer name")
        if (
            cert.subject.get_attributes_for_oid(x509.OID_ORGANIZATION_NAME)[0].value
            == ""
        ):
            self.error("Missing OrganizationName in Subject name")
        if (
            cert.subject.get_attributes_for_oid(x509.OID_ORGANIZATION_NAME)[0].value
            != cert.issuer.get_attributes_for_oid(x509.OID_ORGANIZATION_NAME)[0].value
        ):
            self.error("OrganizationName mismatch for Issuer and Subject")

    def check_certif_role(self, cert, index):
        """Certificate role check.

        References:
            SMPTE ST 430-2:2017 6.2 8
        """
        # 8. Check Role
        cn = cert.subject.get_attributes_for_oid(x509.OID_COMMON_NAME)[0].value
        roles_str = cn.split(".", 1)[0]
        roles = roles_str.split()

        is_ca = index > 0
        is_leaf = not is_ca

        if is_leaf and self.dcp.schema == "SMPTE":
            if not roles:
                self.error("Missing role in CommonName ({})".format(cn))
            if self.context_role not in roles:
                self.error(
                    "Expecting {} role in CommonName ({})".format(self.context_role, cn)
                )
        if is_ca and roles:
            self.error(
                "Role(s) found in authority certificate CommonName ({})".format(cn)
            )

    def check_certif_multi_role(self, cert, index):
        """Leaf certificate role check.

        See https://github.com/wolfgangw/backports/issues/80

        References:
            DCI DCSS (v1.3) 9.4.3.5
        """
        cn = cert.subject.get_attributes_for_oid(x509.OID_COMMON_NAME)[0].value
        roles_str = cn.split(".", 1)[0]
        roles = roles_str.split()

        is_ca = index > 0
        is_leaf = not is_ca

        if is_leaf and self.dcp.schema == "SMPTE":
            if roles and len(roles) > 1:
                self.error("Superfluous roles found in CommonName ({})".format(cn))

    def check_certif_date(self, cert, index):
        """Certificate date validation.

        Note that as per DCI specification, the context time is set to that of
        the IssueDate.

        References:
            SMPTE ST 430-2:2017 6.2 9
            DCI DCSS (v1.4.4) 9.4.3.5 4.c
        """
        # 9. Check time validity
        # Note : Date are formatted in ASN.1 Time YYYYMMDDhhmmssZ

        if self.context_time == "NOW":
            validity_time = datetime.now(timezone.utc)
        elif self.context_time != "":
            validity_time = datetime.strptime(self.context_time, self.time_format)
            validity_time = validity_time.replace(tzinfo=timezone.utc)

        if self.context_time:
            not_before = cert.not_valid_before_utc
            not_after = cert.not_valid_after_utc

            if validity_time < not_before or validity_time > not_after:
                self.error(
                    "IssueDate ({}) outside certificate validity (from {} to {})".format(
                        validity_time, not_before, not_after
                    )
                )

    def check_certif_date_expired(self, cert, index):
        """Certificate date expiration.

        This is an informative note, when trying to play a CPL with an expired
        certificate may fail on older / non-updated systems not compliant with
        DCI specification 1.4.4.

        References:
            https://www.isdcf.com/certs-expiring/
        """
        # 9. Check time validity
        validity_time = datetime.now(timezone.utc)
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc

        if validity_time < not_before or validity_time > not_after:
            self.error(
                "Certificate validity expired (from {} to {}).\n"
                "Playback may fail on non DCI 1.4.4 compliant systems.".format(
                    not_before, not_after
                )
            )

    def check_certif_date_overflow(self, cert, index):
        """Certificate date overflow check.

        Field experience suggests some players do not support certificate
        extending too long in the future.

        References: N/A
        """
        not_after = cert.not_valid_after_utc
        int32_overflow = datetime.fromtimestamp(2**32 / 2 - 1, timezone.utc)
        ten_years_past = datetime.now(timezone.utc) + timedelta(days=365 * 10)

        if not_after >= int32_overflow:
            self.error(
                "Certificate validity extends past unix timestamp"
                " int32 overflow ({})".format(not_after)
            )
        elif not_after >= ten_years_past:
            self.error(
                "Certificate validity extends past 10 years ({})".format(not_after)
            )

    def check_certif_signature_algorithm(self, cert, index):
        """Certificate signature algorithm check.

        References:
            SMPTE ST 430-2:2017 6.2 10
        """
        # 10. Signature Algorithm
        signature_algorithm = cert.signature_hash_algorithm.name
        expected = self.certif_sig_algorithm_map[self.dcp.schema]

        if signature_algorithm not in expected:
            self.error(
                "Invalid Signature Algorithm, expected {} but got {}".format(
                    expected, signature_algorithm
                )
            )

    def check_certif_rsa_validity(self, cert, index):
        """Certificate characteristics (RSA 2048, 65537 exp) check.

        References:
            SMPTE ST 430-2:2017 5.2, 6.2 11
        """
        # 11. Subject's PublicKey RSA validity
        expected_type = rsa.RSAPublicKey
        expected_size = 2048
        expected_exp = 65537

        public_key = cert.public_key()
        key_size = public_key.key_size
        key_exp = public_key.public_numbers().e

        if not isinstance(public_key, expected_type):
            self.error("Subject's public key shall be an RSA key")
        if key_size != expected_size:
            self.error(
                "Subject's public key invalid size, expected {} but got {}".format(
                    expected_size, key_size
                )
            )
        if key_exp != expected_exp:
            self.error(
                "Subject's public key invalid public exponent,"
                " expected {} but got {}".format(expected_exp, key_exp)
            )

    def check_certif_revokation_list(self, cert, index):
        """Certificate revokation list check.

        References:
            SMPTE ST 430-2:2017 6.2 12
        """
        # 12. Revokation list check
        # - Subject public key
        # - Issuer or certificate serial number
        if self.context_revoked_certificates_id or self.context_revoked_public_keys:
            self.error("Revokation list check not implemented")

    def check_certif_publickey_thumbprint(self, cert, index):
        """Certificate public key thumbprint check.

        References:
            SMPTE ST 430-2:2017 6.2 13
        """
        # 13. Subject's public key thumb print match dnQualifier
        dn_thumbprint = cert.subject.get_attributes_for_oid(x509.OID_DN_QUALIFIER)[
            0
        ].value.encode("utf-8")
        key_bits = cert.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.PKCS1,
        )
        key_thumbprint = base64.b64encode(hashlib.sha1(key_bits).digest())

        if not dn_thumbprint:
            self.error("dnQualifier must be present")
        if dn_thumbprint != key_thumbprint:
            self.error(
                "dnQualifier mismatch, expected {} but got {}".format(
                    key_thumbprint, dn_thumbprint
                )
            )

    def check_certif_signature(self, cert, index):
        """Certificate signature check.

        References:
            SMPTE ST 430-2:2017 6.2 14
            SMPTE ST 430-2:2017 6.2 15
        """
        # 14. AuthorityKeyIdentifier

        # This follows SMPTE guidelines but produces errors on the DCP test set.
        # Instead, we use the certificate's issuer field.
        # aki_ext = cert.extensions.get_extension_for_oid(
        #     x509.OID_AUTHORITY_KEY_IDENTIFIER
        # ).value
        # issuer_name = aki_ext.authority_cert_issuer[0].value

        issuer_name = cert.issuer
        issuer_cert = None
        for c in self.cert_list:
            if c.subject == issuer_name:
                issuer_cert = c
                break

        if not issuer_cert:
            self.error("Certificate issuer's certificate not found")

        # 15. Validate signature using local issuer
        try:
            # Cryptography doesn't support SHA1 signatures
            # https://github.com/pyca/cryptography/issues/10727
            if cert.signature_algorithm_oid == x509.SignatureAlgorithmOID.RSA_WITH_SHA1:
                issuer_cert.public_key().verify(
                    signature=cert.signature,
                    data=cert.tbs_certificate_bytes,
                    padding=PKCS1v15(),
                    algorithm=cert.signature_hash_algorithm
                )
            else:
                cert.verify_directly_issued_by(issuer_cert)
        except Exception as e:
            self.error("Certificate signature check failure : {}".format(str(e)))

    def check_xml_certif_serial_coherence(self, cert, xml_cert):
        """XML / Certificate serial number coherence.

        References: N/A
        """
        # i. Serial number check
        xml_serial = xml_cert["X509IssuerSerial"]["X509SerialNumber"]
        if xml_serial != cert.serial_number:
            self.error(
                "Serial number mismatch, expected {} but got {}".format(
                    cert.serial_number, xml_serial
                )
            )

    def check_xml_certif_issuer_coherence(self, cert, xml_cert):
        """XML / Certificate Issuer coherence.

        References: N/A
        """
        # ii. Issuer name check
        xml_issuer = xml_cert["X509IssuerSerial"]["X509IssuerName"]
        issuer_str = cert.issuer.rfc4514_string({x509.OID_DN_QUALIFIER: "dnQualifier"})
        if xml_issuer != issuer_str:
            self.error(
                "IssuerName mismatch, expected {} but got {}".format(
                    issuer_str, xml_issuer
                )
            )

    def check_sign_chain_length(self, source):
        """Certificates minimum chain length.

        References:
            SMPTE ST 430-2:2017 6.2 16
        """
        # 16. Chain length
        if (
            self.context_chain_length
            and len(self.cert_chains) < self.context_chain_length
        ):
            self.error(
                "Certificate chain length should be at least {} long,"
                " got {}".format(self.context_chain_length, len(self.cert_chains))
            )

    def check_sign_chain_coherence(self, source):
        """Certificates chain coherence.

        References:
            SMPTE ST 430-2:2017 6.2 17, 18, 19
        """
        for index in range(1, len(self.cert_list)):
            parent, child = self.cert_list[index - 1], self.cert_list[index]

            # 17. Child Issuer match parent Subject
            if child.issuer != parent.subject:
                self.error("Certificate chain issuer / subject mismatch")

            # 18. Validity date of child contained in parent date
            child_A = child.not_valid_before_utc
            child_B = child.not_valid_after_utc
            parent_A = parent.not_valid_before_utc
            parent_B = parent.not_valid_after_utc

            if child_A < parent_A:
                self.error(
                    "Start date of the child certificate shall be \
                    identical to or later than the start date of the parent \
                    certificate"
                )

            if child_B > parent_B:
                self.error(
                    "End date of the child certificate shall be \
                    identical to or earlier than the end date of the parent \
                    certificate"
                )

            # 19. Root certificate shall appear in trusted certificate list
            if self.context_trusted_certificates:
                self.error("Trusted list check not implemented")

    def check_sign_chain_coherence_signature_algorithm(self, source):
        """Certificates chain coherence.

        References: N/A
        """
        sign_alg_set = set([c.signature_hash_algorithm.name for c in self.cert_list])
        if len(sign_alg_set) > 1:
            self.error(
                "Certificate chain contains certificates "
                "signed with different algorithm"
            )

    def check_sign_signature_algorithm(self, source):
        """XML signature algorithm check.

        References: N/A
        """
        # Additionnal. XML coherence checks
        signed_info = source["Signature"]["SignedInfo"]

        # Signature algorithm
        sig = signed_info["SignatureMethod@Algorithm"]
        if self.sig_ns_map[self.dcp.schema] != sig:
            self.error(
                "Invalid Signature Algorithm, expected {} but got {}".format(
                    self.sig_ns_map[self.dcp.schema], sig
                )
            )

    def check_sign_canonicalization_algorithm(self, source):
        """XML canonicalization algorithm check.

        References: N/A
        """
        signed_info = source["Signature"]["SignedInfo"]
        # Canonicalization algorithm
        can = signed_info["CanonicalizationMethod@Algorithm"]
        if can != DCP_SETTINGS["xmluri"]["c14n"]:
            self.error("Invalid canonicalization method")

    def check_sign_transform_algorithm(self, source):
        """XML signature transform algorithm check.

        References: N/A
        """
        signed_info = source["Signature"]["SignedInfo"]
        # Transform alogrithm
        trans = signed_info["Reference"]["Transforms"]["Transform@Algorithm"]
        if trans != DCP_SETTINGS["xmluri"]["enveloped_sig"]:
            self.error("Invalid transform method")

    def check_sign_digest_algorithm(self, source):
        """XML signature digest method check.

        References: N/A
        """
        signed_info = source["Signature"]["SignedInfo"]
        # Digest algorithm
        trans = signed_info["Reference"]["DigestMethod@Algorithm"]
        if trans != DCP_SETTINGS["xmluri"]["sha1"]:
            self.error("Invalid digest method")

    def check_sign_issuer_name(self, source):
        """XML signature issuer name check.

        References: N/A
        """
        signer = source["Signer"]["X509Data"]["X509IssuerSerial"]
        # Signer Issuer Name
        issuer_dn = self.cert_list[-1].issuer.rfc4514_string(
            {x509.OID_DN_QUALIFIER: "dnQualifier"}
        )
        if signer["X509IssuerName"] != issuer_dn:
            self.error("Invalid Signer Issuer Name")

    def check_sign_issuer_serial(self, source):
        """XML signature serial number check.

        References: N/A
        """
        sig = source["Signer"]["X509Data"]["X509IssuerSerial"]
        # Signer Serial number
        if sig["X509SerialNumber"] != self.cert_list[-1].serial_number:
            self.error("Invalid Signer Serial Number")

    def check_document_signature(self, source, path):
        """Digital signature validation.

        References:
            SMPTE ST 429-7:2006 6.13
            SMPTE ST 429-8:2007 5.10
            IETF RFC 3275
            IETF RFC 4051
        """
        # Check digest (XML document hash)
        signed_info = source["Signature"]["SignedInfo"]
        xml_digest = signed_info["Reference"]["DigestValue"]
        c14n_doc = canonicalize_xml(
            path, ns=DCP_SETTINGS["xmlns"]["xmldsig"], strip="{*}Signature"
        )

        c14n_digest = base64.b64encode(self.digest_func(c14n_doc).digest())
        c14n_digest = c14n_digest.decode("utf-8")
        if xml_digest != c14n_digest:
            self.error("XML Digest mismatch, signature can't be checked")

        # Check signature (XML document hash encrypted with certifier
        # private key)
        c14n_sign = canonicalize_xml(
            path, root="SignedInfo", ns=DCP_SETTINGS["xmlns"]["xmldsig"]
        )

        xml_sig = "".join(source["Signature"]["SignatureValue"].split("\n"))
        xml_sig = base64.b64decode(xml_sig)

        try:
            self.cert_list[-1].public_key().verify(
                signature=xml_sig,
                data=c14n_sign,
                padding=PKCS1v15(),
                algorithm=self.sig_algorithm_map[self.dcp.schema],
            )
        except Exception:
            self.error("Signature validation failed")
