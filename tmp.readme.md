
## **src/classeur.py**

```python
#!/usr/bin/env python3
"""
Module pour gérer les classeurs de documents.

Un classeur est un dossier contenant un fichier de configuration JSON (-classeur.json)
qui définit les règles d'identification, d'extraction et de classement des documents.

Classes:
    ClasseurConfig: Structure de données pour la configuration d'un classeur.
    Classeur: Gère la découverte et le chargement des configurations de classeurs.
"""
```

---

### **ClasseurConfig** *(dataclass)*
Structure de configuration d'un classeur définie dans un fichier JSON.

**Attributs :**

| Attribut | Type | Description | Défaut |
|----------|------|-------------|--------|
| `description` | `str` | Description du classeur | *Requis* |
| `identification` | `List[str]` | Liste de chaînes à rechercher pour identifier un document | *Requis* |
| `patterns` | `Dict[str, str]` | Expressions régulières pour extraire des informations du texte | *Requis* |
| `transform` | `Optional[Dict[str, str]]` | Remplacements de texte à appliquer au nom de fichier | `None` |
| `nom_fichier` | `Optional[List[List[str]]]` | Structure pour générer le nom du fichier | `None` |
| `pages` | `int` | Nombre de pages à extraire par défaut | `2` |
| `extracteur` | `str` | Module d'extraction de texte (`'simple'`, `'tolerant'`, `'mac'`) | `'simple'` |


---

### **Classeur** *(class)*

Gère la découverte et le chargement des configurations de classeurs.

**Attributs de classe :**

| Attribut | Type | Description |
|----------|------|-------------|
| `CHEMIN_BASE` | `Optional[Path]` | Chemin du dossier racine des classeurs |
| `NOM_CONFIG` | `str` | Nom du fichier de configuration (`"-classeur.json"`) |
| `LISTE_CLASSEUR` | `list` | Liste des chemins des classeurs trouvés |
| `LISTE_CONFIG` | `list` | Liste des configurations chargées |
| `SAUVE_CLASSEUR` | `Optional[Path]` | Dernier classeur chargé (cache) |
| `SAUVE_CONFIG` | `Optional[ClasseurConfig]` | Dernière configuration chargée (cache) |

---

**Méthodes :**

#### `@classmethod lister_classeurs(nom_dossier: str) -> list[Path]`
Recherche récursivement tous les classeurs dans un dossier.

**Paramètres :**
- `nom_dossier` : Chemin du dossier racine à explorer

**Retourne :**
- `list[Path]` : Liste des chemins des dossiers contenant un fichier `-classeur.json`

**Lève :**
- `NotADirectoryError` : Si `nom_dossier` n'est pas un dossier valide

**Effets de bord :**
- Remplit `CHEMIN_BASE`, `LISTE_CLASSEUR`, `LISTE_CONFIG`

---

#### `__init__(chemin_dossier: str)`
Initialise une instance de Classeur pour un dossier spécifique.

**Paramètres :**
- `chemin_dossier` : Chemin du dossier du classeur

**Lève :**
- `FileNotFoundError` : Si le dossier ne contient pas de fichier `-classeur.json`

**Attributs d'instance :**

| Attribut | Type | Description |
|----------|------|-------------|
| `chemin_classeur` | `Path` | Chemin absolu du dossier du classeur |
| `nom_court` | `str` | Nom court du classeur (relatif à `CHEMIN_BASE` si défini) |
| `chemin_config` | `Path` | Chemin complet du fichier de configuration |
| `config` | `ClasseurConfig` | Configuration chargée depuis le fichier JSON |

---
---
#### `load_config() -> Optional[ClasseurConfig]`
Charge et valide la configuration depuis le fichier JSON.

**Retourne :**
- `ClasseurConfig` : Objet de configuration validé
- `None` : Si le fichier est introuvable ou invalide

**Comportement :**
- Lit le fichier JSON
- Valide les champs requis (`description`, `identification`, `patterns`)
- Instancie et retourne un objet `ClasseurConfig`

---
---
#### `affiche() -> None`
Affiche les détails de la configuration du classeur dans la console.

**Affichage :**
- ✅/❌ Identification
- ✅/❌ Patterns
- ✅/❌ Transform
- ✅/❌ Nom du fichier

---

---

## **src/document.py**

```python
"""
Module pour gérer l'extraction, l'identification et le classement des documents PDF.

Un document est identifié, analysé et classifié selon les règles définies dans un classeur.
Si le document correspond à un classeur, il peut être renommé, déplacé et verrouillé.

Classes:
    Document: Gère le cycle de vie complet d'un document PDF.
"""
```

---

### **Document** *(class)*

Gère le traitement complet d'un document PDF : extraction de texte, identification, vérification et classement.

**Constantes de classe :**

| Constante | Type | Description |
|-----------|------|-------------|
| `SWIFTOCR` | `str` | Chemin vers l'outil SwiftOCR (`"/Users/yogi/Docker/appl.classeur/swiftocr"`) |
| `MODE` | `int` | Permissions en lecture seule (`0o100400` = `r--------`) |
| `DOCUMENT_PATTERN` | `str` | Pattern pour rechercher les fichiers PDF (`"[a-z|A-Z|0-9]*.pdf"`) |

---

**Méthodes :**

#### `@classmethod lister_fichiers(options: CliOptions) -> list[Path]`
Recherche récursivement les fichiers PDF à traiter.

**Paramètres :**
- `options` : Options CLI contenant `source` (fichier ou dossier)

**Retourne :**
- `list[Path]` : Liste des chemins de fichiers PDF trouvés (normalisés NFC)
- `[]` : Si aucun fichier PDF n'est trouvé

**Comportement :**
- Si `source` est un fichier : retourne `[fichier]` si PDF, sinon `[]`
- Si `source` est un dossier : recherche récursive avec `DOCUMENT_PATTERN`

---
---
#### `__init__(chemin_fichier: Path, options: CliOptions)`
Initialise et traite un document PDF.

**Paramètres :**
- `chemin_fichier` : Chemin vers le fichier PDF (doit exister)
- `options` : Options CLI (`CliOptions`)

**Attributs d'instance :**

| Attribut | Type | Description |
|----------|------|-------------|
| `chemin` | `Path` | Chemin du fichier source (normalisé NFC) |
| `cli_options` | `CliOptions` | Options de la ligne de commande |
| `mtime` | `datetime` | Date de modification du fichier |
| `mode` | `int` | Permissions du fichier |
| `extracteur` | `str` | Module d'extraction de texte |
| `pages` | `int` | Nombre de pages à extraire |
| `classeur` | `Optional[Classeur]` | Classeur correspondant au document |
| `config` | `Optional[ClasseurConfig]` | Configuration du classeur |
| `config_ok` | `bool` | `True` si une configuration de classeur est présente |
| `extractor` | `str` | Module d'extraction effectif |
| `texte` | `str` | Texte extrait du document |
| `identification_ok` | `bool` | Résultat de l'identification du document |
| `patterns_ok` | `bool` | Résultat de la vérification des patterns |
| `chemin_document` | `Optional[Path]` | Chemin cible du document classé |
| `nom_fichier_ok` | `bool` | Résultat de la vérification du nom de fichier |
| `timestamp_fichier_ok` | `bool` | Résultat de la vérification de la date |
| `permission_fichier_ok` | `bool` | Résultat de la vérification des permissions |
| `classement_ok` | `bool` | `True` si toutes les vérifications sont OK |

**Traitement automatique :**
1. Extraction du texte (`extraire_texte()`)
2. Identification (`verifier_identification()`)
3. Vérification des patterns (`verifier_patterns()`)
4. Traitement du nom de fichier (`traitement_nom_fichier()`)
5. Vérification de la date (`traitement_date_fichier()`)
6. Vérification des permissions (`traitement_permissions_fichier()`)
7. Affichage du résumé (`resumer()`)

---
---
#### `extraire_texte() -> str`
Extrait le texte du document PDF.

**Retourne :**
- `str` : Texte extrait et normalisé (NFC, espaces, apostrophes)
- `''` : Si l'extraction échoue

**Stratégie :**
1. Utilise `extractor` spécifié dans les options ou la config
2. Si `extractor` = `'mac'` : utilise `extraire_texte_swift()`
3. Sinon : utilise `extraire_texte_pdf()`
4. Si échec : tente avec `extraire_texte_swift()`

---
---
#### `extraire_texte_pdf() -> str`
Extrait le texte avec `pdfplumber`.

**Retourne :**
- `str` : Texte des `pages` premières pages
- `''` : Si le PDF est vide ou illisible

**Options d'extraction :**
- `'simple'` : `extract_text_simple()`
- `'tolerant'` : `extract_text(x_tolerance=4, y_tolerance=1, layout=True)`

---
---
#### `extraire_texte_swift() -> str`
Extrait le texte avec l'outil **SwiftOCR** (macOS).

**Exécute :**
```bash
swiftocr <chemin_fichier> --lang fr-FR --pages <nombre_pages>
```

**Retourne :**
- `stdout` si succès (code 0)
- `''` si erreur

---
---
#### `extraire_texte_easyocr() -> str`
Extrait le texte avec **EasyOCR** (alternative).

**Comportement :**
- Convertit le PDF en images avec `pdf2image`
- Utilise `easyocr.Reader(['fr'], gpu=True)`
- Extrait le texte de chaque page

**Retourne :**
- `str` : Texte combiné de toutes les pages
- `''` : En cas d'erreur

---
---
#### `verifier_identification() -> bool`
Vérifie si le texte du document correspond aux critères d'identification du classeur.

**Retourne :**
- `True` : Si tous les critères sont trouvés (insensible à la casse)
- `False` : Si au moins un critère n'est pas trouvé

**Comportement :**
- Si aucun classeur n'est spécifié, parcourt tous les classeurs de `CHEMIN_BASE`
- Charge la configuration du premier classeur qui identifie le document

---
---
#### `verifier_patterns() -> bool`
Extrait les informations du texte selon les patterns de la configuration.

**Retourne :**
- `True` : Si tous les patterns sont trouvés
- `False` : Si au moins un pattern échoue

**Effets de bord :**
- Remplit `config['values']` avec les valeurs extraites :
  ```python
  {"pattern_nom": "valeur_trouvée", ...}
  ```

---
---
#### `traitement_nom_fichier() -> bool`
Génère et vérifie le nom du fichier selon la configuration.

**Structure de `nom_fichier` :**
```python
# Exemple dans config :
"nom_fichier": [
    ["identification", 0],   # 1er élément de la liste identification
    ["values", "titre"],       # Valeur extraite du pattern "titre"
    ["values", "timestamp"],   # Valeur extraite du pattern "timestamp"
    ["values", "police?"]      # Optionnel (le ? à la fin)
]
```

**Comportement :**
- Construit le nom à partir des éléments spécifiés
- Applique les transformations (`transform` dans config)
- Remplace les caractères interdits (`<>:"/\|?*` → `_`)
- Limite à 100 caractères
- Normalise en NFC
- Ajoute l'extension `.pdf`

**Avec option `--ranger` :**
- Déplace et renomme le fichier vers `classeur.chemin_classeur / nom_généré.pdf`
- Gère les doublons en ajoutant un timestamp

**Retourne :**
- `True` : Si le nom est correct ou a été corrigé
- `False` : Sinon

---
---
#### `@staticmethod convertir_date(date_str: str) -> Optional[datetime]`
Convertit une chaîne de date en objet `datetime`.

**Paramètres :**
- `date_str` : Chaîne de date (ex: `"15 janvier 2024"`, `"15.01.24"`)

**Retourne :**
- `datetime` : Objet date converti
- `None` : Si le format est invalide

**Formats supportés :**
1. Conversion des mois en texte → format numérique (`"15 janvier 2024"` → `"15.1.2024"`)
2. Parsing avec les formats :
   - `%d.%m.%y` (ex: `15.01.24`)
   - `%d.%m.%Y` (ex: `15.01.2024`)
   - `%d.%m.%Y %H:%M:%S`

---
---
#### `traitement_date_fichier() -> bool`
Vérifie et corrige la date de modification du fichier.

**Comportement :**
- Compare `self.mtime` avec la date extraite (`timestamp` dans `values`)
- Si différent et `--ranger` activé : modifie la date avec `os.utime()`

**Retourne :**
- `True` : Si la date est correcte ou a été corrigée
- `False` : Sinon

---
---
#### `traitement_permissions_fichier() -> bool`
Vérifie et corrige les permissions du fichier.

**Comportement :**
- Compare `self.mode` avec `Document.MODE` (`0o100400` = `r--------`)
- Si différent et `--ranger` activé : applique les permissions avec `chmod()`

**Retourne :**
- `True` : Si les permissions sont correctes ou ont été corrigées
- `False` : Sinon

---
---
#### `resumer() -> None`
Affiche un résumé du traitement du document dans la console.

**Affichage :**
```
Traitement du fichier '<chemin>':

✅ configuration de classeur présente: <description>
✅ texte extrait avec module '<extracteur>', <pages> page(s)
✅ le document est identifié avec les critères <identification>
✅ tous les pattern sont trouvés: <values>
✅ le nom du fichier est correct: '<nom_fichier>'
✅ la date du fichier est correcte: <timestamp>
✅ le fichier est verrouillé (permission en lecture seule)
✅ le fichier est classé dans le bon classeur '<classeur>'

# Ou ❌ pour chaque étape échouée
```

**Si `--ranger` non activé :**
- Affiche `⚠️ active l'option 'ranger' pour classer le document`

---
---
#### `log_all() -> None`
Affiche toutes les informations de débogage via `logger.info()`.

**Informations loggées :**
- Chemin, mtime, mode
- Options (extractor, base, ranger, texte)
- Configuration (classeur, config, module, pages)
- Texte extrait (tronqué à 150 caractères)
- Résultats des vérifications (identification, patterns, values, nom_fichier, timestamp, permission)
- Résultat final (`classement_ok`)

---
---
---
## **Fichier de configuration JSON (exemple)**

```json
{
  "description": "Factures d'assurance voiture chez VZ",
  "pages": 1,
  "extracteur": "simple",
  "identification": [
    "Facture des primes",
    "TOYOTA",
    "10859002"
  ],
  "patterns": {
    "titre": "(Facture des primes)",
    "voiture": "(TOYOTA .*?\\d{2}\\.\\d{2}\\.\\d{2} - \\d{2}\\.\\d{2}\\.\\d{2})",
    "timestamp": "Zurich,.*?(\\d{1,2}(?:\\s+\\w+\\s+\\d{4}|\\.\\d{2}\\.\\d{4}))"
  },
  "transform": {
    " ": "_",
    "é": "e"
  },
  "nom_fichier": [
    ["identification", 0],
    ["values", "titre"],
    ["values", "timestamp"],
    ["values", "police?"]
  ]
}
```

---
---
## **Workflow typique**

```python
from classeur import Classeur
from document import Document
from cli_options import CliOptions

# 1. Lister les classeurs
Classeur.lister_classeurs("/chemin/vers/base")

# 2. Traiter un document
options = CliOptions(
    source="/chemin/vers/fichier.pdf",
    base="/chemin/vers/base",
    ranger=True,
    log="info"
)
document = Document(Path("/chemin/vers/fichier.pdf"), options)

# Résultat :
# - Le document est identifié, renommé, déplacé et verrouillé
# - Un résumé est affiché dans la console
```

---
---
## **Options CLI (`CliOptions`)**

| Option | Type | Défaut | Description |
|--------|------|--------|-------------|
| `source` | `str` | `None` | Chemin vers le fichier/dossier à traiter |
| `log` | `str` | `"none"` | Niveau de logging (`"none"`, `"info"`, `"debug"`) |
| `base` | `str` | `None` | Dossier racine des classeurs |
| `extracteur` | `str` | `"simple"` | Module d'extraction (`"simple"`, `"tolerant"`, `"mac"`) |
| `pages` | `int` | `1` | Nombre de pages à extraire |
| `ranger` | `bool` | `False` | Si `True`, déplace/renomme/verrouille le fichier |
| `texte` | `bool` | `False` | Si `True`, affiche le texte extrait |

---
---
## **Flux de traitement**

```
Fichier PDF
    │
    ▼
Extraire texte (simple/tolerant/mac)
    │
    ▼
Identifier (recherche des critères dans le texte)
    │
    ▼
Vérifier patterns (extraction des valeurs)
    │
    ▼
Générer nom de fichier (selon config)
    │
    ▼
Vérifier date de modification
    │
    ▼
Vérifier permissions (r--------)
    │
    ▼
[Si --ranger] Déplacer/Renommer/Verrouiller
    │
    ▼
Document classé ✅
```
