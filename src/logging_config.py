#!/usr/bin/env python3
"""Configuration centralisée du logging pour l'application classeur.

Conventions de style des textes écrits par les scripts du projet:

- tous les textes sont en français
- messages de logging (logger.debug/info/warning/error):
  * initiale en minuscule
  * pas de point final, pas de point d'exclamation
  * pas d'espace avant le deux-points (ex: "classeur trouvé: {path}")
  * pas de préfixe de nom de fonction ni de tiret en tête de message
  * f-string uniquement si le message contient une interpolation
  * symboles ✓ / 𐄂 pour marquer les vérifications réussies / échouées
- sorties CLI (print), visibles par l'utilisateur:
  * initiale en majuscule (après l'émoji s'il y en a un)
  * émoji de statut en tête: 🗂️ document, ✅ succès, ❌ échec,
    ℹ️ information, ⚠️ erreur non fatale, 📅 date appliquée
  * indentation de deux espaces pour les lignes sous un en-tête
  * pas de point final
- messages des exceptions levées (raise ... Error):
  * initiale en majuscule, même format que les sorties CLI
"""

import logging
import sys
from typing import Optional, Dict

# Mapping des niveaux CLI vers les constantes logging
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "none": None
}

def setup_logging_from_cli(
    cli_level: str,
    module_levels: Optional[Dict[str, str]] = None
) -> None:
    """
    Configure le logging à partir d'un niveau CLI (debug/info/warn/error/none).

    Args:
        cli_level: Niveau de journalisation depuis l'argument CLI
        module_levels: Niveaux spécifiques par module
    """
    niveau = LOG_LEVELS.get(cli_level.lower(), logging.INFO)

    if niveau is None:
        logging.disable(logging.CRITICAL)
        return

    setup_logging(
        level=logging.getLevelName(niveau),
        module_levels=module_levels
    )

def setup_logging(
    level: str = "INFO",
    console: bool = True,
    file_path: Optional[str] = None,
    module_levels: Optional[Dict[str, str]] = None
) -> None:
    """Configure le logging avec un niveau standard (DEBUG/INFO/WARNING/ERROR/CRITICAL)."""
    level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[]
    )

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    root_logger.setLevel(level)

    if module_levels:
        for module_name, module_level in module_levels.items():
            module_logger = logging.getLogger(module_name)
            module_level = getattr(logging, module_level.upper(), logging.INFO)
            module_logger.setLevel(module_level)

    logging.getLogger("pdfplumber").setLevel(logging.WARNING)
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("pdf2image").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("easyocr").setLevel(logging.WARNING)

class LoggingConfig:
    DEFAULT_LEVEL = logging.INFO
    DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    def __init__(self):
        self._configured = False

    def configure(
        self,
        level: str = "INFO",
        console: bool = True,
        file_path: Optional[str] = None
    ) -> None:
        if self._configured:
            return
        setup_logging(
            level=level,
            console=console,
            file_path=file_path
        )
        self._configured = True

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)