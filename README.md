# Classeur - Outil de classement automatique de documents PDF

**Classeur** est une application CLI conçue pour automatiser le classement, l'identification et 
la validation de documents PDF dans une structure de dossiers organisée (classeurs).

## 📁 Structure du projet

```
src/
├── classement.py       # Script principal - orchestration du classement
├── classeur.py         # Gestion des classeurs et de leur configuration
├── document.py         # Traitement des documents PDF (extraction, validation)
└── logging_config.py   # Configuration centralisée du logging

Docker:
├── Dockerfile          # Image de l'outil (python:3.15-slim)
├── classement.sh       # Usage réel: serveur OCR + build + classement
├── test_docker.sh      # Test d'intégration de l'image
├── swiftocr_server.py  # Serveur OCR HTTP (:8765) lancé sur le host macOS
└── swiftocr_client.sh  # Test manuel du serveur OCR (curl)

SwiftOCR:
├── swiftocr            # Binaire compilé pour macOS
└── swift/              # Sources Swift
```

## 🎯 Fonctionnalités

- **Extraction de texte** : depuis des PDF (pdfplumber, ou SwiftOCR sur macOS)
- **Identification automatique** : reconnaissance des documents par motifs configurés
- **Validation** : vérification du nom, date, permissions des fichiers
- **Classement automatique** : déplacement et renommage selon les règles définies
- **Multi-classeurs** : gestion de plusieurs configurations de classeurs
- **Journalisation détaillée** : différents niveaux de verbosité

---

## 📦 Prérequis

### Système
- Python 3.9+
- macOS (pour l'extracteur `mac` avec SwiftOCR), ou Linux/Docker avec les extracteurs `simple`/`tolerant`

### Python (pip)
```bash
pip install -r requirements.txt
# principales dépendances: click, pdfplumber, pillow
```

---

## 🚀 Installation

1. Cloner le dépôt ou copier les fichiers dans un dossier
2. Installer les dépendances Python
3. Placer le binaire `swiftocr` dans `~/.local/bin/` ou définir la variable
   d'environnement `SWIFTOCR` (chemin vers le binaire)

---

## ⚙️ Configuration

### Structure d'un classeur

Un **classeur** est un dossier contenant un fichier de configuration JSON nommé `-classeur.json`.

**Exemple de configuration** (`/chemin/vers/classeur/-classeur.json`) :

```json
{
  "description": "Factures d'assurance voiture",
  "extracteur": "mac",
  "pages": 1,
  "identification": [
    "Facture des primes",
    "TOYOTA",
    "10859002"
  ],
  "patterns": {
    "titre": "(Facture des primes)",
    "voiture": "(TOYOTA .*?\\d{2}.\\d{2}.\\d{2} - \\d{2}.\\d{2}.\\d{2})",
    "timestamp": "Zurich,.*?(\\d{1,2}(?:\\s+\\w+\\s+\\d{4}|\\.\\d{2}\\.\\d{4}))"
  },
  "transform": {
    "ancien_texte": "nouveau_texte"
  },
  "nom_fichier": [
    ["identification", 0],
    ["values", "titre"],
    ["values", "timestamp"],
    ["values", "voiture?"]
  ]
}
```

### Clés de configuration

| Clé              | Type | Description                                                            |
|------------------|------|------------------------------------------------------------------------|
| `description`    | str  | Description du classeur                                                |
| `extracteur`     | str  | Extracteur par défaut (`mac`, `simple`, `tolerant`)                    |
| `pages`          | int  | Nombre minimal de pages à extraire (défaut: 2)                         |
| `identification` | list | Liste de motifs pour identifier le document                            |
| `patterns`       | dict | Expressions régulières pour extraire des valeurs                       |
| `transform`      | dict | Remplacements de texte dans le nom final                               |
| `nom_fichier`    | list | Règles de construction du nom de fichier                               |

### Construction du nom de fichier

Le nom est construit à partir de la liste `nom_fichier` :
- `[["identification", 0]]` → premier élément de la liste `identification`
- `[["values", "titre"]]` → valeur extraite avec le pattern `titre`
- `[["values", "champ?"]]` → champ optionnel (le `?` rend le champ optionnel)

---

## 📖 Utilisation

### 1. Vérifier un document (test)

```bash
# Vérifier un document (sans modification)
python3 src/classement.py mon_document.pdf

# Afficher le texte extrait
python3 src/classement.py mon_document.pdf --texte
```

### 2. Classer un document

```bash
# Avec base de classeurs personnalisée
python3 src/classement.py mon_document.pdf --base /chemin/vers/les/classeurs

# Forcer un extracteur
python3 src/classement.py mon_document.pdf --extracteur simple

# Limiter le nombre de pages extraites
python3 src/classement.py mon_document.pdf --pages 1
```

### 3. Traiter un dossier complet

```bash
# Vérifier tous les PDF d'un dossier
python3 src/classement.py /dossier/contenant/pdf/

# Classer automatiquement (déplacer et renommer)
python3 src/classement.py /dossier/contenant/pdf/ --ranger
```

### 4. Options avancées

```bash
# Niveau de journalisation (info, warn, error, debug, none)
python3 src/classement.py document.pdf --log debug

# Combiner les options
python3 src/classement.py /dossier/ --ranger --log info --base /classeurs/ --extracteur mac
```

---

## 🎛️ Options CLI

### `classement.py`

| Option             | Type   | Description                                                        |
|--------------------|--------|--------------------------------------------------------------------|
| `SOURCE`           | path   | Fichier PDF ou dossier à traiter (argument obligatoire)            |
| `--log, -l`        | choice | Niveau de journalisation: `info`, `warn`, `error`, `debug`, `none` |
| `--base, -b`       | path   | Dossier racine des classeurs (défaut: dossier de la source)        |
| `--extracteur, -e` | choice | Extracteur: `mac`, `simple`, `tolerant`                            |
| `--pages, -p`      | int    | Nombre de pages à extraire                                         |
| `--ranger, -r`     | flag   | Déplacer et renommer les documents                                 |
| `--texte, -t`      | flag   | Afficher le texte extrait                                          |

Sans `--base`, les classeurs sont recherchés dans le dossier de la source
(dossier parent si la source est un fichier).

---

## 🐳 Docker

L'application peut tourner dans un conteneur Docker. Les extracteurs
`simple` et `tolerant` (pdfplumber) fonctionnent entièrement dans le
conteneur; l'extracteur `mac` appelle SwiftOCR sur le **host macOS** via
une petite API HTTP.

### Image

| Élément        | Valeur                                        |
|----------------|-----------------------------------------------|
| Base           | `python:3.15-slim` (Debian)                   |
| Locale         | `fr_CH.UTF-8` (parsing des dates)             |
| Fuseau         | `Europe/Zurich`                               |
| Entrypoint     | `python3 /app/src/classement.py`              |
| Cmd par défaut | `/source --base /base`                        |

### Construction et test

```bash
# Test d'intégration: build + classement de test/in avec base test/
./test_docker.sh

# Arguments transmis à classement.py
./test_docker.sh -l info -e simple

# Autres dossiers
SOURCE_DIR=... BASE_DIR=... ./test_docker.sh
```

### Usage réel

```bash
# Lance swiftocr_server.py sur le host, construit l'image, classe les PDF
# de ~/Desktop/A_classer vers les classeurs de ~/iCloud/Finances/
./classement.sh

# Arguments transmis à classement.py
./classement.sh -l info -e simple

# Autres dossiers
SOURCE_DIR=... BASE_DIR=... ./classement.sh
```

### Architecture OCR

```
┌─────────────┐                ┌──────────────────────────────┐
│  Host macOS │                │  Conteneur classeur          │
│             │  /source, /base│                              │
│  fichiers ──┼───────────────►│  classement.py               │
│             │                │   ├─ simple / tolerant       │
│  swiftocr ──┼◄── :8765/ocr ──┼───┤  = pdfplumber (autonome) │
│  _server.py │ host.docker.   │   └─ mac                     │
│             │ internal       │      = OCR via l'API du host │
└─────────────┘                └──────────────────────────────┘
```

Le conteneur détecte Docker et appelle `http://host.docker.internal:8765/ocr`.
Le serveur `swiftocr_server.py` (lancé sur le host par `classement.sh`)
n'accepte que les fichiers situés dans son dossier `SOURCE` — celui-ci doit
être **le même** que le dossier mappé sur `/source` (sinon HTTP 403).

```bash
# Lancement manuel du serveur OCR sur le host
SOURCE=/chemin/vers/source \
SWIFTOCR=/chemin/vers/swiftocr \
python3 swiftocr_server.py

# Test manuel
./swiftocr_client.sh
```

Une description prête à coller sur Docker Hub se trouve dans
[dockerhub-overview.md](dockerhub-overview.md).

---

## 📊 Processus de traitement

```
Fichier/Dossier en entrée
    ↓
1. Extraction du texte (selon extracteur)
    ↓
2. Identification (recherche dans les classeurs)
    ↓
3. Vérification des patterns (extraction des valeurs)
    ↓
4. Construction du nom de fichier
    ↓
5. Vérification de la date de modification
    ↓
6. Vérification des permissions (r--------)
    ↓
Document classé ✅
```

---

## 🔧 Extracteurs

| Extracteur  | Description                        | Cas d'utilisation           |
|-------------|------------------------------------|-----------------------------|
| `mac`       | SwiftOCR (binaire macOS, via API en Docker) | Documents scannés, images |
| `simple`    | pdfplumber avec extraction simple  | PDF textuels simples        |
| `tolerant`  | pdfplumber avec tolérance          | PDF avec espaces aléatoires |

Le choix de l'extracteur: valeur de `--extracteur` (CLI), sinon valeur
`extracteur` du classeur, sinon `mac` par défaut. Si `simple` ou `tolerant`
ne donnent aucun texte (p. ex. PDF image), l'extraction bascule
automatiquement sur `mac`.

---

## 📝 Symboles

| Symbole | Signification                      |
|---------|------------------------------------|
| ✅       | Validation réussie                 |
| ❌       | Échec de validation                |
| ⚠️      | Erreur non fatale                  |
| ℹ️      | Information                        |
| 🗂️      | Document traité                    |
| 📅      | Date appliquée                     |

---

## 🔍 Journalisation

Les niveaux de log disponibles :
- `none` : aucun message (défaut)
- `error` : erreurs critiques seulement
- `warn` : erreurs + avertissements
- `info` : informations générales (recommandé)
- `debug` : tous les détails (débugging)

---

## 📂 Organisation recommandée

```
Base_Classeurs/
├── Factures/
│   └── -classeur.json
├── Contrats/
│   └── -classeur.json
├── Assurances/
│   └── -classeur.json
└── Documents/
    └── -classeur.json

Dossier_Travail/
├── a_classer/
│   ├── doc1.pdf
│   └── doc2.pdf
└── classes/
    ├── Factures/
    │   ├── facture_2024_01.pdf
    │   └── -classeur.json
    └── Contrats/
        ├── contrat_XYZ.pdf
        └── -classeur.json
```

---

## 🎯 Bonnes pratiques

1. **Testez d'abord** : utilisez `--texte` pour vérifier l'extraction avant de classer
2. **Niveau de log** : commencez avec `--log info`, passez à `debug` si problème
3. **Base de classeurs** : définissez une base centrale avec `--base`
4. **Extracteurs** : essayez différents extracteurs si l'extraction échoue
5. **Sauvegardes** : faites des sauvegardes avant d'utiliser `--ranger`

---

## ⚠️ Limitations connues

- Dépendance à SwiftOCR pour macOS (extracteur `mac`)
- La reconnaissance OCR peut échouer sur des documents de mauvaise qualité
- Les permissions `r--------` peuvent poser problème sur certains systèmes

---

## 🔄 Workflow typique

```bash
# 1. Créer la structure de classeurs
mkdir -p ~/Documents/Classeurs/Factures

# 2. Créer un fichier de configuration pour Factures
cat > ~/Documents/Classeurs/Factures/-classeur.json << 'EOF'
{
  "description": "Factures personnelles",
  "extracteur": "mac",
  "pages": 1,
  "identification": ["Facture", "N°"],
  "patterns": {
    "num_facture": "N°\\s*(\\d+)",
    "date": "Date:\\s*(\\d{2}/\\d{2}/\\d{4})",
    "montant": "Montant:\\s*(\\d+\\.\\d{2})"
  },
  "nom_fichier": [
    ["values", "date"],
    ["values", "num_facture"],
    ["values", "montant"]
  ]
}
EOF

# 3. Vérifier le classement (sans modification)
python3 src/classement.py ~/Téléchargements/facture.pdf --base ~/Documents/Classeurs -t

# 4. Classer automatiquement
python3 src/classement.py ~/Téléchargements/ --ranger --base ~/Documents/Classeurs --log info
```
