# License Payload Schema

```json
{
  "license_id": "uuid",
  "customer": { "id": "string", "name": "string" },
  "module": { "technical_name": "string", "allowed_major_versions": ["1"] },
  "license_type": "perpetual | subscription | demo",
  "issued_at": "ISO-8601",
  "expires_at": null,
  "instance_fingerprint": "hash",
  "signature": "signature"
}
```
