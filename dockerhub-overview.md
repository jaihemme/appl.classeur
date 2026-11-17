# Classeur — classement automatique de documents PDF

Image Docker de **Classeur**, outil CLI qui identifie, valide, renomme et range automatiquement des documents PDF dans une arborescence de « classeurs » décrite par des fichiers de configuration `-classeur.json`.

- ✅ Extraction de texte (pdfplumber ou OCR via SwiftOCR)
- ✅ Identification automatique par motifs configurés
- ✅ Validation du nom, de la date et des permissions des fichiers
- ✅ Déplacement et renommage selon les règles définies
- ✅ Multi-classeurs et journalisation à niveaux (`info`, `warn`, `error`, `debug`, `none`)

## Contenu de l'image

| Élément       | Valeur                                        |
|---------------|-----------------------------------------------|
| Base          | `python:3.15-slim` (Debian)                   |
| Locale        | `fr_CH.UTF-8` (parsing des dates)             |
| Fuseau        | `Europe/Zurich`                               |
| Entrypoint    | `python3 /app/src/classement.py`              |
| Cmd par défaut| `/source --base /base`                        |

## Architecture

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

## Modules d'extraction

| Module     | Moteur                        | Fonctionne dans le conteneur | Cas d'utilisation              |
|------------|-------------------------------|------------------------------|--------------------------------|
| `simple`   | pdfplumber                    | ✅ autonome                  | PDF textuels                   |
| `tolerant` | pdfplumber (tolérant espaces) | ✅ autonome                  | PDF avec espaces aléatoires    |
| `mac`      | SwiftOCR via API du host      | ⚠️ requiert le serveur OCR   | Documents scannés, images      |

## Utilisation

```bash
docker run --rm \
    --add-host=host.docker.internal:host-gateway \
    -v "$SOURCE_DIR:/source" \
    -v "$BASE_DIR:/base" \
    jaihemme/appl.classeur \
    /source --base /base -l warn
```

Tous les arguments passés après le nom de l'image sont transmis à `classement.py`.

### Options CLI

| Option         | Description                                                        |
|----------------|--------------------------------------------------------------------|
| `--log, -l`    | Niveau de journalisation : `info`, `warn`, `error`, `debug`, `none`|
| `--base, -b`   | Dossier racine des classeurs (défaut : `/base`)                    |
| `--module, -m` | Module d'extraction : `mac`, `simple`, `tolerant`                  |
| `--ranger, -r` | Déplacer et renommer les documents                                 |
| `--texte, -t`  | Afficher le texte extrait                                          |

### Volumes

| Volume   | Contenu                                        |
|----------|------------------------------------------------|
| `/source`| PDF à classer                                  |
| `/base`  | Classeurs avec leur fichier `-classeur.json`   |

## Prérequis pour le module `mac`

SwiftOCR ne tourne que sur macOS : le conteneur appelle un petit serveur HTTP
(`swiftocr_server.py`) lancé sur le host. Le dossier passé à `SOURCE` doit être
**le même** que celui mappé sur `/source` (le serveur refuse sinon tout fichier
hors de ce dossier — HTTP 403).

```bash
SOURCE=/chemin/vers/source \
SWIFTOCR=/chemin/vers/swiftocr \
python3 swiftocr_server.py
# → écoute sur localhost:8765
```

Le conteneur joint le serveur via `http://host.docker.internal:8765/ocr`
(`--add-host=host.docker.internal:host-gateway` requis sur Linux).

## Configuration d'un classeur

Chaque classeur est un dossier contenant un fichier `-classeur.json` :

```json
{
  "description": "Factures d'assurance voiture",
  "module": "mac",
  "pages": 1,
  "identification": ["Facture des primes", "TOYOTA"],
  "patterns": {
    "titre": "(Facture des primes)",
    "timestamp": "Zurich,.*?(\\d{1,2}(?:\\s+\\w+\\s+\\d{4}|\\.\\d{2}\\.\\d{4}))"
  },
  "nom_fichier": [
    ["identification", 0],
    ["values", "titre"],
    ["values", "timestamp"]
  ]
}
```

- `identification` : motifs recherchés pour identifier le document
- `patterns` : expressions régulières pour extraire des valeurs
- `nom_fichier` : règles de construction du nom final
  (`[["values", "champ?"]]` — le `?` rend un champ optionnel)

## Construction de l'image

```bash
git clone  && cd appl.classeur
docker build -t jaihemme/appl.classeur .
docker push jaihemme/appl.classeur
```

## Traitement d'un document

```
Entrée (fichier ou dossier)
    ↓
1. Extraction du texte (module simple / tolerant / mac)
    ↓
2. Identification du classeur (recherche des motifs)
    ↓
3. Extraction des valeurs (patterns)
    ↓
4. Construction du nom de fichier
    ↓
5. Vérification de la date de modification
    ↓
6. Vérification des permissions (r--------)
    ↓
Document classé ✅
```

## Limitations connues

- Le module `mac` nécessite un host macOS avec SwiftOCR et le serveur OCR
- L'OCR peut échouer sur des documents de mauvaise qualité
- Les permissions `r--------` peuvent poser problème sur certains systèmes
