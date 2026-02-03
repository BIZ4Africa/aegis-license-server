# AEGIS POC - Quick Start Guide

## 🚀 Démarrage en 5 Minutes

### Prérequis
- Python 3.8+
- pip

### Installation

```bash
cd aegis-poc/
pip install -r requirements.txt
```

### Test Complet

```bash
# Exécuter la suite de tests d'intégration
python test_integration.py
```

**Résultat attendu :**
```
Total Tests: 21
Passed: 21 ✅
Failed: 0 ❌

🎉 All tests passed!
```

---

## 📖 Utilisation

### 1. Générer une Paire de Clés

```bash
python generate_keys.py --key-id aegis-2026-01
```

**Sortie :**
- `keys/aegis-2026-01.private.pem` 🔒 (GARDER SECRET)
- `keys/aegis-2026-01.public.pem` 📖 (à embarquer dans Odoo)

---

### 2. Émettre des Licenses

#### License Perpetuelle
```python
from issue_license import LicenseIssuer

issuer = LicenseIssuer("keys/aegis-2026-01.private.pem")

token = issuer.issue_license(
    customer_id="CUST-001",
    customer_name="Acme Corporation",
    module_name="biz4a_payroll_drc",
    allowed_versions=["17", "18"],
    license_type="perpetual"
)

print(token)
# eyJhbGciOiJFZERTQSIsImtpZCI6ImFlZ2lzLTIwMjYtMDEiLCJ0eXAiOiJKV1QifQ...
```

#### License Demo (30 jours)
```python
token = issuer.issue_license(
    customer_id="DEMO-001",
    customer_name="Prospect Inc",
    module_name="biz4a_payroll_drc",
    allowed_versions=["18"],
    license_type="demo",
    duration_days=30  # ⚠️ Obligatoire pour demo/subscription
)
```

#### License Liée à une Instance
```python
from issue_license import generate_instance_fingerprint

# Générer le fingerprint
fingerprint = generate_instance_fingerprint(
    db_uuid="550e8400-e29b-41d4-a716-446655440000",
    domain="acme.odoo.com"
)

token = issuer.issue_license(
    customer_id="CUST-002",
    customer_name="SecureCorp Ltd",
    module_name="biz4a_accounting_ohada",
    allowed_versions=["17"],
    license_type="perpetual",
    instance_fingerprint=fingerprint  # 🔒 Lie la license à cette instance
)
```

---

### 3. Vérifier des Licenses

```python
from verify_license import LicenseVerifier

verifier = LicenseVerifier("keys/aegis-2026-01.public.pem")

try:
    payload = verifier.verify_license(
        license_token=token,
        module_name="biz4a_payroll_drc",
        odoo_version="17"
    )
    print("✅ License valide !")
    print(f"Client: {payload['customer']['name']}")
    
except LicenseVerificationError as e:
    print(f"❌ License invalide: {e}")
```

#### Vérifier avec Instance Binding
```python
payload = verifier.verify_license(
    license_token=token,
    module_name="biz4a_accounting_ohada",
    odoo_version="17",
    instance_db_uuid="550e8400-e29b-41d4-a716-446655440000",
    instance_domain="acme.odoo.com"
)
```

---

## 🔍 Inspecter une License

```python
from verify_license import LicenseVerifier

verifier = LicenseVerifier("keys/aegis-2026-01.public.pem")

# Obtenir les infos sans vérification complète
info = verifier.get_license_info(token)

print(f"ID: {info['license_id']}")
print(f"Client: {info['customer']['name']}")
print(f"Type: {info['license_type']}")
print(f"Émise: {info['issued_at']}")
print(f"Expire: {info['expires_at'] or 'Jamais'}")
print(f"Liée à une instance: {info['is_bound']}")
```

---

## 🧪 Exemples Fournis

Le POC génère automatiquement 3 exemples dans `licenses/` :

| Fichier | Type | Module | Versions | Binding |
|---------|------|--------|----------|---------|
| `example-perpetual.jwt` | Perpetual | biz4a_payroll_drc | 17, 18 | Non |
| `example-demo.jwt` | Demo (30j) | biz4a_payroll_drc | 18 | Non |
| `example-bound.jwt` | Perpetual | biz4a_accounting_ohada | 17 | Oui |

### Tester les Exemples

```bash
python verify_license.py
```

Exécute 6 tests de vérification sur ces exemples.

---

## 📊 Comprendre le Format JWT

### Anatomie d'un Token

```
eyJhbGc...  .  eyJqdGk...  .  XGbPm2...
   ↑               ↑             ↑
 Header        Payload       Signature
```

### Décoder (sans vérifier)

```python
import jwt

# Décoder sans vérifier la signature (pour debug uniquement)
decoded = jwt.decode(token, options={"verify_signature": False})

print(decoded)
# {
#   "jti": "0bfb0cef-a864-400f-83d4-e8c6bd41dda5",
#   "iss": "https://license.biz4a.com",
#   "iat": 1770145930,
#   "customer": {...},
#   "module": {...},
#   "license_type": "perpetual"
# }
```

**⚠️ Attention :** Toujours vérifier la signature en production !

### Vérifier Online (jwt.io)

1. Aller sur https://jwt.io
2. Coller le token dans "Encoded"
3. Coller la clé publique dans "Verify Signature"

---

## 🛠️ Intégration dans Odoo

### Côté Serveur (Émission)

```python
# Dans votre système de billing/CRM
from issue_license import LicenseIssuer

issuer = LicenseIssuer(
    private_key_path="/secure/keys/aegis-2026-01.private.pem",
    key_id="aegis-2026-01"
)

# Quand un client achète
def on_purchase(customer, module, odoo_version):
    token = issuer.issue_license(
        customer_id=customer.id,
        customer_name=customer.name,
        module_name=module.technical_name,
        allowed_versions=[odoo_version],
        license_type="perpetual"
    )
    
    # Envoyer le token au client (email, portail, etc.)
    send_license_to_customer(customer.email, token)
```

### Côté Client Odoo (Vérification)

```python
# Dans aegis_client/models/aegis_license.py

from odoo import models, api, _
from odoo.exceptions import UserError
from verify_license import LicenseVerifier, LicenseVerificationError

class AegisLicense(models.Model):
    _name = 'aegis.license'
    
    @api.model
    def verify_module_license(self, module_name):
        """Vérifie la license pour un module donné."""
        
        # Charger le token de la config
        token = self.env['ir.config_parameter'].sudo().get_param(
            f'aegis.license.{module_name}'
        )
        
        if not token:
            raise UserError(_("Aucune license configurée pour %s") % module_name)
        
        # Charger la clé publique
        public_key_path = os.path.join(
            os.path.dirname(__file__), 
            '../security/public_keys/aegis-2026-01.public.pem'
        )
        
        verifier = LicenseVerifier(public_key_path)
        
        try:
            # Vérifier
            verifier.verify_license(
                license_token=token,
                module_name=module_name,
                odoo_version=odoo.release.major_version
            )
            return True
            
        except LicenseVerificationError as e:
            raise UserError(_("License invalide: %s") % str(e))
```

### Hook de Vérification au Démarrage

```python
# Dans aegis_client/__init__.py

def pre_init_hook(cr):
    """Vérifier la license avant l'installation du module."""
    from .models.aegis_license import AegisLicense
    
    # Note: Cette logique doit être adaptée car on n'a pas accès
    # au registry complet dans pre_init_hook
    
    # Alternative: vérifier au premier démarrage du module
    pass

def post_load():
    """Appelé au chargement du module."""
    # Vérifier la license
    # Si invalide, désactiver les fonctionnalités
    pass
```

---

## 🔒 Sécurité - Bonnes Pratiques

### ✅ À FAIRE

1. **Clé Privée**
   - ❌ **Jamais** committer dans Git
   - ✅ Stocker dans un KMS (AWS KMS, Azure Key Vault, HashiCorp Vault)
   - ✅ Permissions 0600 (owner read/write only)
   - ✅ Backup chiffré dans un lieu sûr

2. **Rotation des Clés**
   - ✅ Planifier rotation annuelle
   - ✅ Utiliser `kid` pour gérer plusieurs clés
   - ✅ Garder les anciennes clés publiques (backward compatibility)

3. **Monitoring**
   - ✅ Logger toutes les émissions de license
   - ✅ Alerter sur échecs de vérification répétés
   - ✅ Tracker les licenses proches de l'expiration

### ❌ À ÉVITER

- ❌ Hardcoder la clé privée dans le code
- ❌ Envoyer des licenses par email non chiffré (utiliser HTTPS)
- ❌ Négliger les backups de clés
- ❌ Réutiliser la même clé pour d'autres systèmes

---

## 🐛 Troubleshooting

### Erreur: "Invalid signature"

**Causes possibles:**
- Token altéré/corrompu
- Mauvaise clé publique utilisée pour vérification
- Token généré avec une autre clé privée

**Solution:**
1. Vérifier que la clé publique correspond à la clé privée
2. Régénérer le token si nécessaire
3. Vérifier l'intégrité du token (pas de caractères manquants)

---

### Erreur: "License has expired"

**Cause:** License demo/subscription expirée

**Solution:**
1. Vérifier la date d'expiration: `verifier.get_license_info(token)`
2. Émettre une nouvelle license avec `duration_days` approprié

---

### Erreur: "Odoo version '16' not allowed"

**Cause:** Version Odoo non dans `allowed_major_versions`

**Solution:**
1. Émettre une nouvelle license incluant la version voulue
2. Ou mettre à jour Odoo vers une version autorisée

---

### Erreur: "Instance fingerprint mismatch"

**Cause:** License liée à une autre instance

**Solution:**
1. Vérifier le `db_uuid` et `domain` de l'instance actuelle
2. Émettre une nouvelle license pour cette instance
3. Ou utiliser une license non-bound

---

## 📚 Pour Aller Plus Loin

- **ADR-0001:** Détails sur le choix de Ed25519/JWT
- **README.md:** Documentation complète du POC
- **test_integration.py:** Suite de tests complète
- **PROCHAINES-ETAPES.md:** Roadmap pour la production

---

## 🆘 Support

Questions ? Problèmes ?

1. Consulter la documentation dans `aegis-poc/README.md`
2. Exécuter les tests : `python test_integration.py`
3. Vérifier les ADRs dans `docs/adr/`

---

**Bon développement ! 🚀**
