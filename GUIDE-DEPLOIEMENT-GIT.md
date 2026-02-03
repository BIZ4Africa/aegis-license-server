# Guide de Déploiement du POC AEGIS

## 📋 Prérequis

- Git configuré
- Accès au repository `aegis-license-server`
- Terminal avec bash/zsh

---

## 🎯 Méthode 1 : Déploiement Complet (Recommandé)

### Étape 1 : Extraire l'Archive POC

```bash
# Télécharger aegis-poc.tar.gz depuis les fichiers partagés
# Puis extraire :
tar -xzf aegis-poc.tar.gz
cd aegis-poc/
```

### Étape 2 : Naviguer vers votre Repository

```bash
# Aller à la racine de votre repository aegis-license-server
cd /chemin/vers/aegis-license-server
```

### Étape 3 : Créer la Branche POC

```bash
# Créer une nouvelle branche pour le POC
git checkout -b feature/poc-implementation
```

### Étape 4 : Copier les Fichiers du POC

```bash
# Créer le dossier poc/ à la racine
mkdir -p poc

# Copier tous les fichiers du POC
cp -r /chemin/vers/aegis-poc/* poc/

# Vérifier la structure
tree poc/
```

**Structure résultante :**
```
aegis-license-server/
├── README.md                    (existant)
├── LICENSE                      (existant)
├── docs/
│   ├── specs/                   (existant)
│   ├── adr/
│   │   ├── ADR-0001-license-signing.md  ⬅️ À AJOUTER
│   └── diagrams/                (existant)
│
├── poc/                         ⬅️ NOUVEAU DOSSIER
│   ├── README.md
│   ├── requirements.txt
│   ├── generate_keys.py
│   ├── issue_license.py
│   ├── verify_license.py
│   ├── test_integration.py
│   ├── keys/                    (gitignored)
│   └── licenses/                (exemples)
│
├── server/                      (vide pour l'instant)
└── .gitignore                   ⬅️ À METTRE À JOUR
```

### Étape 5 : Copier l'ADR-0001

```bash
# Copier l'ADR dans le bon dossier
cp /chemin/vers/ADR-0001-license-signing.md docs/adr/
```

### Étape 6 : Mettre à Jour le .gitignore

```bash
# Ajouter au .gitignore (ou créer si inexistant)
cat >> .gitignore << 'EOF'

# ===== AEGIS POC =====
# Clés privées (CRITIQUE - ne jamais committer)
poc/keys/*.private.pem
*.private.pem
*.key

# Clés de test (OK de committer les publiques)
# poc/keys/*.public.pem  # Commenté = on peut committer les clés publiques de demo

# Environnements virtuels Python
poc/venv/
poc/.venv/
poc/__pycache__/
poc/*.pyc

# Licenses générées (optionnel - peut être commité pour exemples)
# poc/licenses/*.jwt

# Fichiers temporaires
poc/.pytest_cache/
poc/.coverage
poc/htmlcov/

EOF
```

### Étape 7 : Vérifier ce qui sera Commité

```bash
# Voir les fichiers à ajouter
git status

# Devrait montrer :
# - docs/adr/ADR-0001-license-signing.md (nouveau)
# - poc/ (nouveau dossier)
# - .gitignore (modifié)
```

### Étape 8 : Commit Initial

```bash
# Ajouter tous les fichiers
git add docs/adr/ADR-0001-license-signing.md
git add poc/
git add .gitignore

# Vérifier qu'aucune clé privée n'est ajoutée
git status | grep -i "private"  
# ⚠️ Ne devrait rien retourner !

# Commit
git commit -m "feat(poc): Add AEGIS license signing POC

- Add ADR-0001: JWT + Ed25519 cryptographic decision
- Implement key generation (Ed25519)
- Implement license issuance (JWT signing)
- Implement license verification (signature validation)
- Add comprehensive integration tests (21 tests)
- Add documentation and examples

This POC validates the core AEGIS license control framework.
All tests passing (21/21).

Ref: AEGIS-001"
```

### Étape 9 : Push la Branche

```bash
# Push vers le remote
git push -u origin feature/poc-implementation
```

### Étape 10 : Créer une Pull Request

```bash
# Sur GitHub/GitLab/Bitbucket, créer une PR avec :
# - Titre : "POC: AEGIS License Control Framework"
# - Description : Voir template ci-dessous
```

---

## 🎯 Méthode 2 : Déploiement Sélectif

Si vous voulez uniquement certains fichiers :

### Option A : Uniquement l'ADR

```bash
cd aegis-license-server/
git checkout -b docs/add-adr-0001

cp /chemin/vers/ADR-0001-license-signing.md docs/adr/

git add docs/adr/ADR-0001-license-signing.md
git commit -m "docs: Add ADR-0001 for license signing algorithm"
git push -u origin docs/add-adr-0001
```

### Option B : POC dans un Sous-module Git

```bash
# Créer un repository séparé pour le POC
# Puis l'ajouter comme sous-module

git submodule add https://github.com/biz4a/aegis-poc.git poc
git commit -m "feat: Add POC as submodule"
```

---

## 📝 Template de Pull Request

```markdown
# POC: AEGIS License Control Framework

## 🎯 Objectif

Implémenter et valider le Proof of Concept (POC) pour le système de contrôle de licenses AEGIS.

## ✅ Ce qui a été fait

### 1. ADR-0001: Décision Architecturale
- **Choix technique :** JWT + EdDSA (Ed25519)
- **Justification :** Performance (~1ms), sécurité moderne, compatibilité
- **Fichier :** `docs/adr/ADR-0001-license-signing.md`

### 2. POC Fonctionnel
- **Génération de clés :** Ed25519 (256 bits)
- **Émission de licenses :** JWT signés avec EdDSA
- **Vérification :** Offline-first avec validation cryptographique + métier
- **Tests :** 21 tests d'intégration (100% de réussite)

### 3. Documentation
- README complet du POC
- Quick Start Guide
- Roadmap vers la production

## 🧪 Tests

```bash
cd poc/
pip install -r requirements.txt
python test_integration.py
```

**Résultat attendu :** 21/21 tests ✅

## 📊 Performances

- Génération de clés : ~50ms (one-time)
- Émission de license : ~1ms
- Vérification : ~1ms
- Taille clé publique : 113 bytes

## 🔒 Sécurité

⚠️ **Note POC :** Les clés privées ne sont PAS chiffrées dans ce POC.
En production, utiliser AWS KMS / Azure Key Vault / HashiCorp Vault.

Voir `poc/README.md` section "Security Considerations".

## 🚀 Prochaines Étapes

Après merge de ce POC :
1. Implémenter l'API REST (FastAPI)
2. Ajouter PostgreSQL pour persistence
3. Créer le module Odoo client

Détails dans `PROCHAINES-ETAPES.md`.

## 📋 Checklist

- [x] ADR-0001 rédigé et complet
- [x] Code POC fonctionnel
- [x] Tests passent (21/21)
- [x] Documentation complète
- [x] .gitignore mis à jour (clés privées exclues)
- [x] Aucune clé privée committée
- [x] README à jour

## 🔍 Revue Demandée

- [ ] Valider le choix technique (JWT + Ed25519)
- [ ] Approuver l'architecture du POC
- [ ] Confirmer la roadmap vers production

---

**Type :** Feature  
**Impact :** Foundation technique AEGIS  
**Breaking Changes :** Non (nouveau code)
```

---

## ⚠️ CRITIQUES - Vérifications de Sécurité

Avant de commiter, **TOUJOURS** vérifier :

### ✅ Checklist de Sécurité

```bash
# 1. Vérifier qu'aucune clé privée n'est stagée
git diff --cached | grep -i "private key"
git diff --cached | grep "BEGIN PRIVATE KEY"

# 2. Vérifier le .gitignore
cat .gitignore | grep "private"

# 3. Lister ce qui sera commité
git status

# 4. Dry-run du commit
git commit --dry-run

# 5. Vérifier l'historique après commit
git log --oneline -n 5
git show HEAD --stat

# 6. Scanner les secrets (si outil disponible)
git secrets --scan  # Si installé
# ou
gitleaks detect    # Si installé
```

### ❌ Ne JAMAIS Committer

- ❌ Fichiers `*.private.pem`
- ❌ Fichiers `*.key`
- ❌ Variables d'environnement avec secrets
- ❌ Tokens ou passwords en dur
- ❌ Configurations de production

### ✅ OK de Committer

- ✅ Clés publiques de démo (`*.public.pem`)
- ✅ Exemples de licenses JWT
- ✅ Code source Python
- ✅ Tests
- ✅ Documentation

---

## 🔄 Workflow Git Complet

```bash
# 1. Clone du repository (si pas déjà fait)
git clone https://github.com/biz4a/aegis-license-server.git
cd aegis-license-server/

# 2. Créer la branche
git checkout -b feature/poc-implementation

# 3. Extraire et copier le POC
tar -xzf /chemin/vers/aegis-poc.tar.gz
mkdir -p poc
cp -r aegis-poc/* poc/
cp /chemin/vers/ADR-0001-license-signing.md docs/adr/

# 4. Mettre à jour .gitignore
cat >> .gitignore << 'EOF'
# AEGIS POC
poc/keys/*.private.pem
*.private.pem
poc/venv/
poc/__pycache__/
EOF

# 5. Ajouter et vérifier
git add .
git status
git diff --cached --name-only | grep -i private  # Doit être vide !

# 6. Commit
git commit -m "feat(poc): Add AEGIS license signing POC

- Add ADR-0001: JWT + Ed25519 decision
- Implement key generation, issuance, verification
- Add 21 integration tests (all passing)
- Add comprehensive documentation"

# 7. Push
git push -u origin feature/poc-implementation

# 8. Créer la Pull Request sur GitHub/GitLab
```

---

## 📁 Structure Finale du Repository

Après déploiement :

```
aegis-license-server/
│
├── README.md                          # Mis à jour avec lien vers POC
├── LICENSE
│
├── docs/
│   ├── specs/
│   │   ├── 00-overview.md
│   │   ├── 01-requirements.md
│   │   └── ... (autres specs)
│   │
│   ├── adr/
│   │   ├── ADR-0001-license-signing.md    ⬅️ NOUVEAU
│   │   └── README.md                       (optionnel - index des ADRs)
│   │
│   └── diagrams/
│       └── aegis-reference-diagram.mmd
│
├── poc/                                     ⬅️ NOUVEAU DOSSIER
│   ├── README.md                            (Documentation POC)
│   ├── requirements.txt
│   ├── generate_keys.py
│   ├── issue_license.py
│   ├── verify_license.py
│   ├── test_integration.py
│   │
│   ├── keys/                                (gitignored partiellement)
│   │   ├── .gitkeep
│   │   ├── aegis-2026-01.public.pem        (OK de committer)
│   │   └── aegis-2026-01.private.pem       (gitignored)
│   │
│   └── licenses/                            (exemples OK)
│       ├── example-perpetual.jwt
│       ├── example-demo.jwt
│       └── example-bound.jwt
│
├── server/                                  (vide - Phase 1)
│   └── .gitkeep
│
├── deploy/                                  (vide - Phase 1)
│   └── .gitkeep
│
├── .github/
│   └── workflows/                           (optionnel)
│       └── poc-tests.yml                    (CI pour tester le POC)
│
├── .gitignore                               ⬅️ MIS À JOUR
└── .gitattributes                           (optionnel)
```

---

## 🤖 Optionnel : CI/CD pour le POC

Créer `.github/workflows/poc-tests.yml` :

```yaml
name: AEGIS POC Tests

on:
  push:
    branches: [ main, develop, feature/* ]
    paths:
      - 'poc/**'
  pull_request:
    branches: [ main, develop ]

jobs:
  test-poc:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd poc/
        pip install -r requirements.txt
    
    - name: Run POC integration tests
      run: |
        cd poc/
        python test_integration.py
    
    - name: Check for private keys in commits
      run: |
        ! git diff --cached | grep -i "BEGIN PRIVATE KEY"
```

---

## 📚 Mise à Jour du README Principal

Ajouter cette section au `README.md` principal :

```markdown
## 🧪 Proof of Concept (POC)

Un POC fonctionnel validant l'architecture AEGIS est disponible dans `poc/`.

### Quick Start

```bash
cd poc/
pip install -r requirements.txt
python test_integration.py
```

**Résultat attendu :** 21 tests passent ✅

### Documentation

- **POC README :** `poc/README.md`
- **ADR-0001 :** `docs/adr/ADR-0001-license-signing.md`
- **Quick Start :** Voir fichiers téléchargés

### Prochaines Étapes

Le POC valide les concepts de base. Pour la production :
1. API REST (FastAPI) → `server/`
2. Client Odoo → repository séparé
3. Déploiement → `deploy/`

Voir roadmap complète dans la documentation POC.
```

---

## 🎯 Commandes Récapitulatives

### Déploiement Complet en 1 Commande

```bash
# Créer un script deploy-poc.sh
cat > deploy-poc.sh << 'SCRIPT'
#!/bin/bash
set -e

echo "🚀 Déploiement du POC AEGIS..."

# Variables
POC_ARCHIVE="aegis-poc.tar.gz"
ADR_FILE="ADR-0001-license-signing.md"
BRANCH="feature/poc-implementation"

# Vérifications
if [ ! -f "$POC_ARCHIVE" ]; then
    echo "❌ Erreur: $POC_ARCHIVE introuvable"
    exit 1
fi

if [ ! -f "$ADR_FILE" ]; then
    echo "❌ Erreur: $ADR_FILE introuvable"
    exit 1
fi

# Extraire
echo "📦 Extraction de l'archive POC..."
tar -xzf "$POC_ARCHIVE"

# Créer la branche
echo "🌿 Création de la branche $BRANCH..."
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"

# Copier les fichiers
echo "📁 Copie des fichiers..."
mkdir -p poc docs/adr
cp -r aegis-poc/* poc/
cp "$ADR_FILE" docs/adr/

# Mettre à jour .gitignore
echo "🔒 Mise à jour du .gitignore..."
cat >> .gitignore << 'EOF'

# AEGIS POC - Security
poc/keys/*.private.pem
*.private.pem
poc/venv/
poc/__pycache__/
EOF

# Ajouter les fichiers
echo "➕ Ajout des fichiers au staging..."
git add poc/ docs/adr/ADR-0001-license-signing.md .gitignore

# Vérifier sécurité
echo "🔍 Vérification de sécurité..."
if git diff --cached | grep -qi "BEGIN PRIVATE KEY"; then
    echo "❌ ERREUR: Clé privée détectée dans le staging !"
    git reset
    exit 1
fi

# Commit
echo "💾 Commit..."
git commit -m "feat(poc): Add AEGIS license signing POC

- Add ADR-0001: JWT + Ed25519 decision
- Implement key generation, issuance, verification
- Add 21 integration tests (all passing)
- Add comprehensive documentation"

echo "✅ Déploiement local terminé !"
echo ""
echo "Prochaines étapes :"
echo "  1. Tester : cd poc/ && python test_integration.py"
echo "  2. Push : git push -u origin $BRANCH"
echo "  3. Créer une Pull Request sur GitHub/GitLab"

SCRIPT

chmod +x deploy-poc.sh
./deploy-poc.sh
```

---

## ✅ Validation Finale

Après déploiement, vérifier :

```bash
# 1. Tests passent
cd poc/
python test_integration.py
# ➜ Doit afficher : 21/21 tests ✅

# 2. Aucune clé privée committée
git log --all --full-history -- "*.private.pem"
# ➜ Doit être vide

# 3. Structure correcte
tree -L 2 .
# ➜ Doit montrer poc/ et docs/adr/

# 4. .gitignore fonctionne
git status
# ➜ Ne doit pas montrer *.private.pem

echo "✅ Validation complète réussie !"
```

---

**Besoin d'aide pour une étape spécifique ?** Dites-moi où vous en êtes !
