# AEGIS Odoo Client Template

This guide shows how to bind an existing Odoo module to AEGIS license verification using the `aegis_client` addon. It includes a minimal Hello World example in `odoo/addons/aegis_hello`.

## 1. Install the base client addon

Add `aegis_client` to your addons path and install it first. It provides:

- Model `aegis.license`
- Verification helper (Ed25519 + JWT)
- Embedded public key lookup

## 2. Configure a license record

Create one `aegis.license` record per protected module.

Fields:
- `module_name`: technical name of your addon
- `license_token`: the JWT license string

You can create the record from the UI under `Settings -> AEGIS -> Licenses`.

## 3. Protect an existing module (installable but not usable without a license)

### 3.1 Add dependency

In your module `__manifest__.py`:

```python
"depends": ["base", "aegis_client"]
```

### 3.2 Verify before critical actions

In any model method, call the verifier before executing sensitive logic:

```python
from odoo import models

class YourModel(models.Model):
    _name = "your.model"

    def action_do_sensitive_thing(self):
        self.env["aegis.license"].action_views_open("your_module_name")
        # continue with protected logic
```

### 3.3 Optional: verify on menu access or record access

If you want to block all access to a model when the license is invalid, you can
verify inside `create`, `write`, or `read` overrides for sensitive models.

## 4. Instance-bound licenses

If your licenses are bound to an instance, `aegis_client` will automatically use:

- `database.uuid` for DB binding
- `web.base.url` for domain binding (normalized to host)

Ensure these values match what the license was issued for.

## 5. Public key and issuer

- Public key lives in: `odoo/addons/aegis_client/security/public_keys/aegis-2026-01.public.pem`
- Issuer is configured by `ir.config_parameter` key `aegis.issuer` (defaults to `https://license.biz4a.com`)

## 6. Hello World reference

The module in `odoo/addons/aegis_hello` shows:

- Dependency on `aegis_client`
- A protected button that validates before showing a message

Use it as a starting point for integrating AEGIS into your own addon.
