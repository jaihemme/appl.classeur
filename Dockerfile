# Image Docker de l'outil de classement de documents PDF
# Base: image Python minimaliste (Debian slim)
FROM python:3.15-slim

# Prérequis système: locales françaises (fr_CH.UTF-8 pour le parsing des dates)
# et fuseau horaire suisse (pour la vérification des timestamps des fichiers)
RUN apt-get update && apt-get install -y --no-install-recommends \
        locales \
        tzdata \
    && sed -i '/fr_CH.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=fr_CH.UTF-8 \
    LC_ALL=fr_CH.UTF-8 \
    TZ=Europe/Zurich \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SOURCE="/source"

WORKDIR /app

# Prérequis Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Scripts de l'application
COPY src/ /app/src/

# Dossiers mappés sur des volumes au moment du run:
#   docker run -v /chemin/vers/source:/source -v /chemin/vers/base:/base ...
VOLUME ["/source", "/base"]

# Tous les arguments passés après le nom de l'image vont à classement.py
ENTRYPOINT ["python3", "/app/src/classement.py"]
CMD ["/source", "--base", "/base"]
