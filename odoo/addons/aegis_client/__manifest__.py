{
    "name": "AEGIS Client",
    "version": "1.0.0",
    "summary": "Client-side license verification for AEGIS-protected modules",
    "category": "Tools",
    "author": "BIZ4A",
    "license": "OPL-1",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "data/aegis_config.xml",
        "views/aegis_license_views.xml"
    ],
    "installable": True,
    "application": False,
    "external_dependencies": {
        "python": ["jwt", "cryptography"]
    }
}
