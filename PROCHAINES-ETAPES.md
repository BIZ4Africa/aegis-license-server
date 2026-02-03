# AEGIS POC - Prochaines Étapes

## ✅ Ce qui a été accompli (Option A)

Nous avons créé un **POC fonctionnel complet** qui valide tous les concepts techniques d'AEGIS :

### 1. Génération de Clés ✅
- Script `generate_keys.py` créé
- Génération de paires Ed25519
- Gestion des permissions (0600 pour privée, 0644 pour publique)
- Fichiers de métadonnées

### 2. Émission de Licenses ✅
- Module `issue_license.py` implémenté
- Support des 3 types de license (perpetual, subscription, demo)
- Format JWT avec signature EdDSA
- Instance fingerprinting optionnel
- Exemples générés automatiquement

### 3. Vérification de Licenses ✅
- Module `verify_license.py` créé (simulation client Odoo)
- Vérification de signature cryptographique
- Validation des règles métier :
  - Nom du module
  - Version Odoo
  - Date d'expiration
  - Instance binding
- Gestion complète des erreurs

### 4. Tests Complets ✅
- Suite de tests d'intégration (21 tests)
- Couverture à 100% des cas d'usage
- Tests de tampering et edge cases
- **Tous les tests passent** 🎉

## 📊 Résultats du POC

```
Total Tests: 21
Passed: 21 ✅
Failed: 0 ❌

Performances:
- Génération de clés: ~50ms
- Émission de license: ~1ms
- Vérification: ~1ms
```

---

## 🎯 Prochaines Étapes Recommandées

### Phase 1 : Serveur de Production (2-3 semaines)

#### 1.1 API REST
**Objectif :** Exposer les fonctionnalités via HTTP

**Tâches :**
- [ ] Choisir framework (recommandation : **FastAPI**)
- [ ] Créer endpoints :
  - `POST /api/v1/licenses` - Émettre une license
  - `GET /api/v1/licenses/{id}` - Obtenir une license
  - `POST /api/v1/licenses/{id}/validate` - Valider (optionnel)
  - `DELETE /api/v1/licenses/{id}` - Révoquer
- [ ] Authentification (JWT ou API keys)
- [ ] Rate limiting
- [ ] Documentation OpenAPI/Swagger

**Livrable :** API fonctionnelle avec documentation

---

#### 1.2 Persistence des Données
**Objectif :** Stocker les licenses émises

**Tâches :**
- [ ] Choisir base de données (recommandation : **PostgreSQL**)
- [ ] Schéma de base :
  ```sql
  CREATE TABLE licenses (
    id UUID PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    customer_name VARCHAR(200) NOT NULL,
    module_name VARCHAR(100) NOT NULL,
    license_type VARCHAR(20) NOT NULL,
    token TEXT NOT NULL,
    issued_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
  );
  
  CREATE TABLE customers (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
  );
  ```
- [ ] ORM (SQLAlchemy ou similaire)
- [ ] Migrations (Alembic)

**Livrable :** Base de données configurée avec schéma initial

---

#### 1.3 Gestion des Clés
**Objectif :** Sécuriser les clés privées

**Options :**

**Option A - Simple (développement/staging):**
- Fichier chiffré avec passphrase
- Passphrase dans variable d'environnement
- Permissions strictes (0600)

**Option B - Production (recommandé):**
- AWS KMS / Azure Key Vault / HashiCorp Vault
- Rotation automatique des clés
- Audit logging

**Tâches :**
- [ ] Implémenter chargement sécurisé des clés
- [ ] Documenter procédure de rotation
- [ ] Créer backup chiffré

**Livrable :** Clés stockées de manière sécurisée

---

#### 1.4 Déploiement
**Objectif :** Conteneuriser et déployer

**Tâches :**
- [ ] Créer `Dockerfile`
- [ ] Configuration via variables d'environnement
- [ ] `docker-compose.yml` (API + PostgreSQL)
- [ ] Health checks
- [ ] Logs structurés (JSON)

**Livrable :** Application déployable en container

---

### Phase 2 : Client Odoo (2-3 semaines)

#### 2.1 Module AEGIS Client
**Objectif :** Créer le module Odoo de vérification

**Structure :**
```
aegis_client/
├── __manifest__.py
├── __init__.py
├── models/
│   └── aegis_license.py
├── security/
│   ├── ir.model.access.csv
│   └── public_keys/
│       └── aegis-2026-01.public.pem
├── data/
│   └── aegis_config.xml
├── views/
│   └── aegis_license_views.xml
└── controllers/
    └── main.py
```

**Tâches :**
- [ ] Structure de base du module
- [ ] Modèle `aegis.license` pour stocker la config
- [ ] Hook `pre_init_hook` pour vérification
- [ ] Vue de configuration pour les admins
- [ ] Tests unitaires

**Livrable :** Module Odoo installable

---

#### 2.2 Mécanisme de Blocage
**Objectif :** Empêcher l'utilisation sans license valide

**Stratégies :**

1. **Blocage à l'installation** (recommandé) :
   ```python
   def pre_init_hook(cr):
       # Vérifier license avant installation
       if not verify_license():
           raise Exception("License invalide")
   ```

2. **Vérification au démarrage** :
   ```python
   @api.model
   def _check_license_on_startup(self):
       if not self._verify_license():
           # Désactiver le module ou bloquer actions
           pass
   ```

3. **Hook sur actions critiques** :
   - Désactiver menu items
   - Bloquer création de records
   - Afficher watermark

**Tâches :**
- [ ] Implémenter vérification au pre_init_hook
- [ ] Message d'erreur clair pour utilisateurs
- [ ] Fallback pour migration (grace period)

**Livrable :** Module qui se bloque si license invalide

---

#### 2.3 Gestion de Configuration
**Objectif :** Permettre aux admins de configurer la license

**Interface :**
- Champ texte pour coller le JWT
- Bouton "Valider"
- Affichage des infos de license :
  - Type (perpetual/demo/subscription)
  - Client
  - Expiration
  - Modules couverts
  - Versions Odoo

**Tâches :**
- [ ] Vue de configuration (Settings > AEGIS License)
- [ ] Validation en temps réel
- [ ] Stockage sécurisé du token (ir.config_parameter)
- [ ] Notification d'expiration (pour demo/subscription)

**Livrable :** Interface admin fonctionnelle

---

### Phase 3 : Fonctionnalités Avancées (2-3 semaines)

#### 3.1 Révocation de Licenses
**Tâches :**
- [ ] Table `license_revocations` (liste noire)
- [ ] Endpoint `DELETE /api/v1/licenses/{id}`
- [ ] Client peut vérifier online (optionnel)
- [ ] Mécanisme de synchronisation (cronjob Odoo)

---

#### 3.2 Analytics & Monitoring
**Tâches :**
- [ ] Dashboard admin (nombre de licenses actives, etc.)
- [ ] Logs d'audit (qui a émis quelle license, quand)
- [ ] Alertes :
  - License proche de l'expiration
  - Tentatives de validation échouées
  - Clé compromise

---

#### 3.3 Portail Client
**Tâches :**
- [ ] Interface web pour clients BIZ4A
- [ ] Téléchargement de licenses
- [ ] Historique des licenses
- [ ] Demande de renouvellement

---

## 🗓️ Planning Suggéré

### Semaine 1-2 : API REST + Base de données
- API FastAPI fonctionnelle
- PostgreSQL configuré
- Endpoints de base

### Semaine 3-4 : Sécurité + Déploiement
- Gestion sécurisée des clés
- Docker / docker-compose
- Tests d'intégration API

### Semaine 5-6 : Module Odoo Client
- Structure de base
- Vérification offline
- Interface admin

### Semaine 7-8 : Tests & Documentation
- Tests end-to-end
- Documentation utilisateur
- Guide de déploiement

### Semaine 9+ : Fonctionnalités avancées
- Révocation
- Monitoring
- Portail client

---

## 🔧 Stack Technique Recommandé

### Serveur
- **Langage :** Python 3.11+
- **Framework :** FastAPI
- **Base de données :** PostgreSQL 15+
- **ORM :** SQLAlchemy 2.0
- **Migrations :** Alembic
- **Containerisation :** Docker + docker-compose
- **Secrets :** HashiCorp Vault (ou AWS KMS)

### Client Odoo
- **Version Odoo :** 17.0, 18.0
- **Dépendances :** `pyjwt[crypto]`, `cryptography`
- **Tests :** pytest (pour tests isolés du module)

### DevOps
- **CI/CD :** GitHub Actions
- **Monitoring :** Prometheus + Grafana
- **Logs :** ELK Stack ou Loki

---

## 📚 Documentation à Créer

### Technique
- [ ] Architecture Decision Records (ADRs)
  - ADR-0002: Choix du framework API
  - ADR-0003: Stratégie de révocation
  - ADR-0004: Mécanisme de blocage Odoo
- [ ] Guide de déploiement
- [ ] Procédures opérationnelles (runbooks)

### Utilisateur
- [ ] Guide d'installation du module Odoo
- [ ] FAQ pour les clients
- [ ] Troubleshooting

### Commerciale
- [ ] Modèle de license OPL-1 + Addendum
- [ ] Conditions générales
- [ ] Grille tarifaire

---

## 💡 Recommandations Immédiates

### À faire cette semaine :
1. **Valider le POC** avec l'équipe BIZ4A
2. **Choisir le stack** pour le serveur (recommandation : FastAPI)
3. **Définir le schéma de base de données**
4. **Créer le repository Git** pour le serveur
5. **Planifier le sprint 1** (API REST)

### Décisions à prendre :
- [ ] Hébergement du serveur de licenses (cloud ? on-premise ?)
- [ ] Stratégie de backup (RPO/RTO ?)
- [ ] Politique de rotation des clés (12 mois ? 24 mois ?)
- [ ] Support multi-tenancy ? (un serveur pour tous les clients ?)

---

## 🎓 Leçons du POC

### Ce qui fonctionne bien ✅
- Ed25519 est **très rapide** (~1ms)
- JWT est **standard** et bien outillé (jwt.io)
- Clés publiques sont **compactes** (113 bytes)
- Vérification **offline** fiable

### Points d'attention ⚠️
- PyJWT ne gère pas `exp: null` nativement (résolu dans le POC)
- Instance fingerprinting peut changer (migration de DB)
- Rotation de clés nécessite **versioning** (`kid`)
- Private key **DOIT** être chiffrée en production

---

## 📞 Support

Pour questions/aide :
- **Technique :** Référencer ADR-0001 et ce POC
- **Architecture :** Consulter `docs/specs/`
- **Code :** Voir exemples dans `aegis-poc/`

---

**Prêt pour la Phase 1 ?** 🚀

La prochaine étape logique est de créer l'API REST avec FastAPI.
Voulez-vous que je vous aide à démarrer ?
