#!/usr/bin/env bash
# test_docker.sh — construit l'image Docker et lance un test de classement
#
# Les dossiers 'source' (PDF à classer) et 'base' (classeurs avec -classeur.json)
# sont mappés sur les volumes /source et /base du conteneur.
#
# Usage:
#   ./test_docker.sh                 # test par défaut sur test/in avec base test/
#   ./test_docker.sh -l info -e simple   # arguments transmis à classement.py
#   SOURCE_DIR=... BASE_DIR=... ./test_docker.sh   # autres dossiers
#
# Prérequis pour l'extracteur 'mac': swiftocr_server.py doit tourner sur le host
# macOS avec SWIFTOCR_DIR pointant sur la base. Le test par défaut utilise
# l'extracteur 'simple' (pdfplumber), qui fonctionne entièrement dans le conteneur.
set -euo pipefail
cd "$(dirname "$0")"

IMAGE="${IMAGE:-appl-classeur}"
SOURCE_DIR="${SOURCE_DIR:-$PWD/test/in}"
BASE_DIR="${BASE_DIR:-$PWD/test}"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Le dossier source n'existe pas: $SOURCE_DIR" >&2
    exit 1
fi
if [ ! -d "$BASE_DIR" ]; then
    echo "❌ Le dossier base n'existe pas: $BASE_DIR" >&2
    exit 1
fi

echo "🏗️  Construction de l'image $IMAGE..."
docker build -t "$IMAGE" .

echo "🐳 Test: source=$SOURCE_DIR base=$BASE_DIR"
if [ $# -gt 0 ]; then
    # Tous les arguments sont transmis à classement.py
    exec docker run --rm \
        --add-host=host.docker.internal:host-gateway \
        -v "$SOURCE_DIR:/source" \
        -v "$BASE_DIR:/base" \
        "$IMAGE" \
         /source --base /base -l warn "$@"
else
    # Test par défaut: extraction pdfplumber (autonome dans le conteneur)
    exec docker run --rm \
        --add-host=host.docker.internal:host-gateway \
        -v "$SOURCE_DIR:/source" \
        -v "$BASE_DIR:/base" \
        "$IMAGE" \
        /source --base /base -e simple -l info
fi
