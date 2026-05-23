# Classeur - Outil de classement automatique de documents PDF

**Classeur** est une application CLI conçue pour automatiser le classement, l'identification et la validation de documents PDF dans une structure de dossiers organisée (classeurs).

## 📁 Structure du projet

```
src/
├── classement.py      # Script principal - orchestration du classement
├── classeur.py        # Gestion des classeurs et de leur configuration
├── document.py        # Traitement des documents PDF (extraction, validation)
└── extraire_text.py   # Utilitaire d'extraction de texte
```

## 🎯 Fonctionnalités

- **Extraction de texte** : depuis des PDF (via pdfplumber, SwiftOCR, ou EasyOCR)
- **Identification automatique** : reconnaissance des documents par motifs configurés
- **Validation** : vérification du nom, date, permissions des fichiers
- **Classement automatique** : déplacement et renommage selon les règles définies
- **Multi-classeurs** : gestion de plusieurs configurations de classeurs
- **Journalisation détaillée** : différents niveaux de verbosité

---

## 📦 Prérequis

### Système
- Python 3.8+
- macOS (pour SwiftOCR) ou Linux
- **Dépendances externes** :
  - [SwiftOCR](https://github.com/martinsciborr/SwiftOCR) (pour le module `mac`)

### Python (pip)
```bash
pip install click pdfplumber pdf2image easyocr pillow
```

---

## 🚀 Installation

1. Cloner le dépôt ou copier les fichiers dans un dossier
2. Installer les dépendances Python
3. Placer `swiftocr` dans `/Users/yogi/Docker/appl.classeur/` ou modifier `Document.SWIFTOCR`

---

## ⚙️ Configuration

### Structure d'un classeur

Un **classeur** est un dossier contenant un fichier de configuration JSON nommé `-classeur.json`.

**Exemple de configuration** (`/chemin/vers/classeur/-classeur.json`) :

```json
{
  "description": "Factures d'assurance voiture",
  "module": "mac",
  "pages": 1,
  "images": false,
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

| Clé | Type | Description |
|-----|------|-------------|
| `description` | str | Description du classeur |
| `module` | str | Module d'extraction par défaut (`mac`, `simple`, `tolerant`) |
| `pages` | int | Nombre de pages à extraire (défaut: 2) |
| `images` | bool | Indique si le PDF contient des images |
| `identification` | list | Liste de motifs pour identifier le document |
| `patterns` | dict | Expressions régulières pour extraire des valeurs |
| `transform` | dict | Remplacements de texte dans le nom final |
| `nom_fichier` | list | Règles de construction du nom de fichier |

### Construction du nom de fichier

Le nom est construit à partir de la liste `nom_fichier` :
- `[["identification", 0]]` → premier élément de la liste `identification`
- `[["values", "titre"]]` → valeur extraite avec le pattern `titre`
- `[["values", "champ?"]]` → champ optionnel (le `?` rend le champ optionnel)

---

## 📖 Utilisation

### 1. Extraire du texte (test)

```bash
# Extraire le texte d'un PDF
./extraire_text.py mon_document.pdf

# Avec options
./extraire_text.py mon_document.pdf --pages 2 --module tolerant
```

### 2. Classer un document

```bash
# Vérifier un document (sans modification)
./classement.py mon_document.pdf

# Avec base de classeurs personnalisée
./classement.py mon_document.pdf --base /chemin/vers/les/classeurs

# Forcer un module d'extraction
./classement.py mon_document.pdf --module simple
```

### 3. Traiter un dossier complet

```bash
# Vérifier tous les PDF d'un dossier
./classement.py /dossier/contenant/pdf/

# Classer automatiquement (déplacer et renommer)
./classement.py /dossier/contenant/pdf/ --ranger

# Afficher le texte extrait
./classement.py /dossier/contenant/pdf/ --texte
```

### 4. Options avancées

```bash
# Niveau de journalisation (info, warn, error, debug, none)
./classement.py document.pdf --log debug

# Combiner les options
./classement.py /dossier/ --ranger --log info --base /classeurs/ --module mac
```

---

## 🎛️ Options CLI

### `classement.py`

| Option | Type | Description |
|--------|------|-------------|
| `--log, -l` | choice | Niveau de journalisation: `info`, `warn`, `error`, `debug`, `none` |
| `--base, -b` | path | Dossier racine des classeurs |
| `--module, -m` | choice | Module d'extraction: `mac`, `simple`, `tolerant` |
| `--ranger, -r` | flag | Déplacer et renommer les documents |
| `--texte, -t` | flag | Afficher le texte extrait |

### `extraire_text.py`

| Option | Type | Description |
|--------|------|-------------|
| `--pages, -p` | int | Nombre de pages à extraire (défaut: 1) |
| `--module, -m` | choice | Module: `mac`, `simple`, `tolerant` (défaut: `mac`) |

---

## 📊 Processus de traitement

```
Fichier/Dossier en entrée
    ↓
1. Extraction du texte (selon module)
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

## 🔧 Modules d'extraction

| Module | Description | When to use |
|--------|-------------|-------------|
| `mac` | Utilise SwiftOCR (native macOS) | Documents scannés, images |
| `simple` | pdfplumber avec extraction simple | PDF textuels simples |
| `tolerant` | pdfplumber avec tolérance | PDF avec espaces aléatoires |

---

## 📝 Codes de sortie et symboles

| Symbole | Signification |
|---------|---------------|
| ✅ | Validation réussie |
| ❌ | Échec de validation |
| ⚠️ | Avertissement (action recommandée) |
| ℹ️ | Information |
| 📂 | Classeur identifié |
| 📅 | Date modifiée |

---

## 🔍 Journalisation

Les niveaux de log disponibles :
- `none` : aucun message
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
4. **Modules** : essayez différents modules si l'extraction échoue
5. **Sauvegardes** : faites des sauvegardes avant d'utiliser `--ranger`

---

## ⚠️ Limitations connues

- Dépendance à SwiftOCR pour macOS (module `mac`)
- EasyOCR nécessite GPU pour de meilleures performances
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
  "module": "mac",
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

# 3. Tester l'extraction
./extraire_text.py ~/Téléchargements/facture.pdf --module mac

# 4. Vérifier le classement (sans modification)
./classement.py ~/Téléchargements/facture.pdf --base ~/Documents/Classeurs

# 5. Classer automatiquement
./classement.py ~/Téléchargements/ --ranger --base ~/Documents/Classeurs --log info
```
