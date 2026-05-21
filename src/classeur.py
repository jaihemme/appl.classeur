#!/usr/bin/env python3
"""
Module pour gérer les classeurs de documents.
"""
import sys
from pathlib import Path
import json
import logging


logger = logging.getLogger(__name__)

class Classeur:
    """Classe pour gérer les classeurs de documents.
    Un dossier devient 'classeur' s'il contient un fichier (json) de configuration"""

    NOM_BASE:Path = Path('.')
    NOM_CONFIG: str = "-classeur.json"
    LISTE_CLASSEUR: list = []
    LISTE_CONFIG: list = []    
    SAUVE_CLASSEUR: Path = None
    SAUVE_CONFIG: dict = {}


    def __new__(cls, nom_dossier: str, option_base: bool):
        logger.debug(f"__new__: {nom_dossier} - base: {option_base}")
        chemin_dossier: Path = Path(nom_dossier)

        if not chemin_dossier.exists():
            # raise FileNotFoundError(f"Dossier introuvable: '{nom_dossier}'")
            logger.critical(f"FileNotFoundError - Dossier introuvable: '{nom_dossier}'")
            sys.exit(1)

        if not chemin_dossier.is_dir():
            # raise NotADirectoryError(f"Argument n'est pas un dossier: '{nom_dossier}'")
            logger.critical(f"NotADirectoryError - Argument n'est pas un dossier: '{nom_dossier}'")
            sys.exit(1)

        # si le dossier est une base, on retourne une liste de dossiers qui contiennent le fichier de configuration
        if option_base:
            Classeur.NOM_BASE = chemin_dossier.resolve()
            logger.debug(f"Recherche de classeurs sous la base '{Classeur.NOM_BASE}'")
            # liste des classeurs (dossiers avec un fichier de configuration)
            Classeur.LISTE_CLASSEUR=[fichier.parent.resolve() for fichier in chemin_dossier.rglob(Classeur.NOM_CONFIG)]
            logger.info(f"il y a {len(Classeur.LISTE_CLASSEUR)} classeur(s) dans '{chemin_dossier}'")
            # chargement des configurations
            Classeur.LISTE_CONFIG = [
                Classeur(classeur, False).config for classeur in Classeur.LISTE_CLASSEUR
            ]
            return True
            # return [str(dossier) for dossier in Classeur.LISTE_CLASSEUR]  # retourne une liste de noms de dossiers

        # sans l'option 'base', on retourne une instance de Classeur si le fichier de configuration s'y trouve
        if (chemin_dossier / Classeur.NOM_CONFIG).exists():
            return super().__new__(cls)

        logger.debug(f"FileNotFoundError - Le dossier ne contient pas de fichier de configuration"
                     f" '{Classeur.NOM_CONFIG}'")
        # raise FileNotFoundError(f"Le dossier ne contient pas de fichier de configuration '{Classeur.NOM_CONFIG}'")
        return None

    def __init__(self, nom_dossier, option_base: bool):
        """Initialise la classe Classeur avec les arguments donnés."""
        logger.debug(f"__init__: {nom_dossier} - base: {option_base}")
        self.chemin_classeur: Path = Path(nom_dossier)  # le dossier existe, vérifié dans __new__
        if Classeur.NOM_BASE:
            self.chemin_court = str(self.chemin_classeur).replace(str(Classeur.NOM_BASE), "")
        else:
            self.chemin_court = self.chemin_classeur
        self.chemin_config: Path = self.chemin_classeur / Classeur.NOM_CONFIG
        # vérifier si la configuration du classeur a déjà été chargée
        # si oui, la charger depuis la sauvegarde
        if Classeur.SAUVE_CLASSEUR == self.chemin_classeur:
            self.config = Classeur.SAUVE_CONFIG
            logger.debug(f"classeur: {Classeur.SAUVE_CLASSEUR} - charge config de sauvegarde")
        else:
            self.config = self.load_config()
            Classeur.SAUVE_CLASSEUR = self.chemin_classeur
            Classeur.SAUVE_CONFIG = self.config
            logger.debug(f"classeur: {Classeur.SAUVE_CLASSEUR} - config sauvegardée")


    def load_config(self) -> dict:
        """Charge la configuration depuis un fichier JSON. Retourne le dictionnaire
        de configuration s'il existe ou None. Example de configuration:
        {
          "description": "Factures d'assurance voiture (casco partielle et RC) chez VZ",
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
          },
          "nom_fichier": [["identification", 0], ["values","voiture"]]
        }"""
        try:
            config: dict = json.loads(self.chemin_config.read_text(encoding="utf-8"))
            logger.debug(f"load_config : {json.dumps(config, indent=2)}")
        except FileNotFoundError:
            logger.error(f"Dossier non configuré (ne contient pas de fichier {Classeur.NOM_CONFIG}.")
            return {}
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Erreur dans fichier de configuration '{Classeur.NOM_CONFIG}': {e}")
            sys.exit(1)

        return config

    def affiche(self) -> None:
        """Affiche les détails de la configuration du classeur."""
        print(f"\n📁 Classeur: {self.chemin_classeur}")
        identification = self.config.get("identification", None)
        if identification:
            print(f"✅ Identification: {identification}")
        else:
            print(f"❌ Identification: cet attribut n'est pas configuré'")

        patterns = self.config.get("patterns", None)
        if patterns:
            print(f"✅ Patterns      : {patterns}")
        else:
            print(f"❌ Patterns      : cet attribut n'est pas configuré'")

        transform = self.config.get("transform", None)
        if transform:
            print(f"✅ Transform      : {transform}")
        # else:
        #     print(f"❌ Transform      : cet attribut n'est pas configuré'")

        nom_fichier = self.config.get("nom_fichier", None)
        if nom_fichier:
            print(f"✅ Nom du fichier: {nom_fichier}")
        else:
            print(f"❌ Nom du fichier: cet attribut n'est pas configuré")


# print(f"✅...)
# print(f"❌...)
# print(f"⚠️...)
# print(f"ℹ️...)