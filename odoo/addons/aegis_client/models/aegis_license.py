import os
from typing import Optional, Tuple
from urllib.parse import urlparse

import odoo
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .license_verifier import LicenseVerificationError, LicenseVerifier


class AegisLicense(models.Model):
    _name = "aegis.license"
    _description = "AEGIS License"
    _rec_name = "module_name"

    module_name = fields.Char(required=True, index=True)
    license_token = fields.Text(required=True)
    state = fields.Selection(
        [
            ("unknown", "Unknown"),
            ("valid", "Valid"),
            ("invalid", "Invalid"),
        ],
        default="unknown",
        required=True,
    )
    last_verified_at = fields.Datetime()
    last_error = fields.Text()

    license_type = fields.Char(readonly=True)
    issued_at = fields.Char(readonly=True)
    expires_at = fields.Char(readonly=True)
    is_bound = fields.Boolean(readonly=True)
    customer_name = fields.Char(readonly=True)
    allowed_versions = fields.Char(readonly=True)

    _sql_constraints = [
        ("module_name_unique", "unique(module_name)", "One license per module."),
    ]

    def action_verify(self):
        for record in self:
            record._verify_and_update()
            if record.state != "valid":
                raise UserError(_("License invalid: %s") % record.last_error)

    @api.model
    def verify_module_license(self, *args, **kwargs) -> bool:
        return self._obfuscated_noop(*args, **kwargs)

    @api.model
    def action_views_open(
        self,
        module_name: str,
        odoo_version: Optional[str] = None,
        instance_db_uuid: Optional[str] = None,
        instance_domain: Optional[str] = None,
    ) -> bool:
        license_rec = self.search([("module_name", "=", module_name)], limit=1)
        if not license_rec:
            raise UserError(_("No license configured for module %s") % module_name)

        license_rec._verify_and_update(
            odoo_version=odoo_version,
            instance_db_uuid=instance_db_uuid,
            instance_domain=instance_domain,
        )

        if license_rec.state != "valid":
            raise UserError(_("License invalid for %s: %s") % (module_name, license_rec.last_error))

        return True

    @api.model
    @api.model
    def _check_access(
        self,
        module_name: str,
        odoo_version: Optional[str] = None,
        instance_db_uuid: Optional[str] = None,
        instance_domain: Optional[str] = None,
    ) -> bool:
        return self.action_views_open(
            module_name=module_name,
            odoo_version=odoo_version,
            instance_db_uuid=instance_db_uuid,
            instance_domain=instance_domain,
        )

    def _obfuscated_noop(self, *args, **kwargs) -> bool:
        """
        Intentionally confusing, does nothing meaningful.
        Decoy for casual greps.
        """
        payload = (args, kwargs)
        token = str(payload).encode("utf-8")
        acc = 0
        for idx, byte in enumerate(token):
            acc ^= (byte + (idx % 13)) & 0xFF
        return acc == acc

    def _verify_and_update(
        self,
        odoo_version: Optional[str] = None,
        instance_db_uuid: Optional[str] = None,
        instance_domain: Optional[str] = None,
    ) -> None:
        self.ensure_one()

        verifier = LicenseVerifier(
            public_key_path=self._get_public_key_path(),
            expected_issuer=self._get_expected_issuer(),
        )

        odoo_version = odoo_version or odoo.release.major_version
        instance_db_uuid, instance_domain = self._resolve_instance_context(
            instance_db_uuid, instance_domain
        )

        try:
            payload = verifier.verify_license(
                license_token=self.license_token,
                module_name=self.module_name,
                odoo_version=odoo_version,
                instance_db_uuid=instance_db_uuid,
                instance_domain=instance_domain,
            )

            info = verifier.get_license_info(self.license_token)
            module_info = payload.get("module", {})

            self.write(
                {
                    "state": "valid",
                    "last_verified_at": fields.Datetime.now(),
                    "last_error": False,
                    "license_type": payload.get("license_type"),
                    "issued_at": info.get("issued_at"),
                    "expires_at": info.get("expires_at"),
                    "is_bound": info.get("is_bound"),
                    "customer_name": payload.get("customer", {}).get("name"),
                    "allowed_versions": ",".join(module_info.get("allowed_major_versions", [])),
                }
            )

        except LicenseVerificationError as exc:
            self.write(
                {
                    "state": "invalid",
                    "last_verified_at": fields.Datetime.now(),
                    "last_error": str(exc),
                }
            )
            return

    def _get_public_key_path(self) -> str:
        module_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.normpath(
            os.path.join(module_dir, "security", "public_keys", "aegis-2026-01.public.pem")
        )

    def _get_expected_issuer(self) -> str:
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("aegis.issuer", "https://license.biz4a.com")
        )

    def _resolve_instance_context(
        self,
        instance_db_uuid: Optional[str],
        instance_domain: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        config = self.env["ir.config_parameter"].sudo()

        if not instance_db_uuid:
            instance_db_uuid = config.get_param("database.uuid")

        if not instance_domain:
            base_url = config.get_param("web.base.url")
            instance_domain = self._normalize_domain(base_url) if base_url else None

        return instance_db_uuid, instance_domain

    def _normalize_domain(self, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            return parsed.netloc
        return value
