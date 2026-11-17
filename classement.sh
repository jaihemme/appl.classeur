#!/usr/bin/env bash 
# construit l'image Docker, lanche le serveur swiftocr et lance le docker avec classement
#
# Les dossiers 'source' (PDF à classer) et 'base' (classeurs avec -classeur.json)
# sont mappés sur les volumes /source et /base du conteneur.
#
# Usage:
#   ./classement.sh                 # test par défaut sur test/in avec base test/
#   ./classement.sh -l info -e simple   # arguments transmis à classement.py
#   SOURCE_DIR=... BASE_DIR=... ./classement.sh   # autres dossiers
#
# Prérequis pour l'extracteur 'mac': swiftocr_server.py doit tourner sur le host
# macOS avec SWIFTOCR_DIR pointant sur la base. Le test par défaut utilise
# l'extracteur 'simple' (pdfplumber), qui fonctionne entièrement dans le conteneur.
set -euo pipefail
cd "$(dirname "$0")"

which python || source venv/bin/activate || echo "❌ pas d'environnement python"
IMAGE="${IMAGE:-appl.classeur}"
#SOURCE_DIR="${SOURCE_DIR:-$PWD/test/in}"
SOURCE_DIR="${SOURCE_DIR:-$HOME/Desktop/A_classer}"
#BASE_DIR="${BASE_DIR:-$PWD/test}"
BASE_DIR="${BASE_DIR:-$HOME/iCloud/Finances/}"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Le dossier source n'existe pas: $SOURCE_DIR" >&2
    exit 1
fi
if [ ! -d "$BASE_DIR" ]; then
    echo "❌ Le dossier base n'existe pas: $BASE_DIR" >&2
    exit 1
fi

echo "ℹ️ liste des documents à classer:"
ls -l $SOURCE_DIR

echo "🏗️  Construction de l'image $IMAGE..."
orb start docker  # lance docker au cas où
docker build -t "$IMAGE" .

# lance le serveur swiftocr
nc -4zv localhost 8765 && pkill -f swiftocr_server.py && echo "⚠️ ancien processus swiftocr_server.py stoppé"
SOURCE=$SOURCE_DIR SWIFTOCR="/Users/yogi/Docker/appl.classeur/swiftocr" python swiftocr_server.py &
pid=$!
echo "👻 swiftocr_server.py lancé ($pid)"

echo "🐳 $IMAGE: source=$SOURCE_DIR base=$BASE_DIR"
# Tous les arguments sont transmis à classement.py
docker run --rm \
    --add-host=host.docker.internal:host-gateway \
    -v "$SOURCE_DIR:/source" \
    -v "$BASE_DIR:/base" \
    "$IMAGE" \
     /source --base /base -l warn "$@"

# arrêt du serveur swiftocr
echo -n "👻 swiftocr_server.py va être stoppé ... "
kill $pid && echo "OK" || echo "ERROR"
