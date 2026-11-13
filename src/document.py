#!/usr/bin/env python3
"""Module représentant un document PDF à classifier."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import unicodedata
from datetime import datetime
from classeur import Classeur
import re
import os
import subprocess
import urllib.request
import urllib.error
import json

logger = logging.getLogger(__name__)

MODE: int = 0o100400  # 'r--------'
SWIFTOCR = "/Users/yogi/Docker/appl.classeur/swiftocr"

def is_running_in_docker():
    # Vérifie l'existence du fichier .dockerenv ou la présence de 'docker' dans cgroup
    return Path('/.dockerenv').exists() or os.path.exists('/.dockerinit')

if is_running_in_docker():
    SWIFTOCR_URL = "http://host.docker.internal:8765/ocr"
else:
    SWIFTOCR_URL = "http://localhost:8765/ocr"

@dataclass
class Document:
    """Classe représentant un document PDF.
    
    Attributes:
        path: Chemin absolu vers le fichier PDF
        name: Nom du fichier (sans extension)
        extension: Extension du fichier
        pages: nombre minimal de pages à extraire
        mode: permissions du fichier
        classeur_ok: document placé dans le bon dossier (classeur)
        nom_fichier: Nom du fichier selon la consigne de la configuration
        nom_fichier_ok: le nom du fichier correspond à la consigne
    """
    path: Path
    name: Optional[str] = None
    extension: Optional[str] = None
    extracteur: Optional[str] = None
    pages: Optional[int] = None
    texte: Optional[str] = None
    pattern_values: Optional[dict[str, str]] = None
    patterns_ok: bool = False
    nom_fichier: Optional[str] = None
    nom_fichier_ok: bool = False
    timestamp_fichier_ok: bool = False
    permission_fichier_ok: bool = False
    classeur_ok: bool = False

    # sauvegardes
    texte_simple: str = ''
    texte_tolerant: str = ''
    texte_mac: str = ''

    def __post_init__(self):
        """Initialisation après la création de l'instance."""
        if isinstance(self.path, str):
            self.path = Path(self.path)
        self.path = self.path.resolve()
        if self.name is None:
            self.name = self.path.stem
        nfc = unicodedata.normalize('NFC', self.name or '')
        if nfc != self.name:
            logger.warning("le nom du fichier n'est pas au format unicode NFC")
        if self.extension is None:
            self.extension = self.path.suffix.lower()
        # obtenir l'heure de modification (mtime) du fichier
        self.mtime: datetime = datetime.fromtimestamp(self.path.stat().st_mtime)
        # obtenir le type de fichier et ses permissions
        self.mode: int = self.path.stat().st_mode

    @staticmethod
    def convertir_date(date_str: str) -> Optional[datetime]:
        # conversion de date en texte en date objet
        if date_str is '':
            logger.error("il manque une valeur pour le traitement de la date")
            return None

        # Dictionnaire de conversion des mois en minuscules
        # pour convertir en numéro du mois (index)
        table_mois = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre',
                      'novembre', 'décembre']
        date_sub = date_str
        for index, mois in enumerate(table_mois):
            date_sub = re.sub(f" {mois} ", f".{index + 1}.", date_str, count=1, flags=re.IGNORECASE)
            if date_sub != date_str:
                logger.info(f"transformation date: {date_str} -> {date_sub}")
                break

        formats = ["%d.%m.%y", "%d.%m.%Y", "%d.%m.%Y %H:%M:%S", "%d %b %Y"]
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_sub, fmt)
                logger.debug(f"conversion date: {date_sub} -> {date_obj}")
                return date_obj
            except ValueError:
                continue

        logger.error(f"format de date non reconnu: {date_str}")
        return None

    @classmethod
    def from_path(cls, path: str) -> 'Document':
        """Crée un Document à partir d'un chemin.
        
        Args:
            path: Chemin vers le fichier PDF
            
        Returns:
            Instance de Document
            
        Raises:
            ValueError: Si le fichier n'existe pas ou n'est pas un PDF
        """
        path_obj = Path(path).resolve()
        
        if not path_obj.exists():
            raise ValueError(f"Le fichier n'existe pas: {path_obj}")
        
        if not path_obj.is_file():
            raise ValueError(f"Le chemin n'est pas un fichier: {path_obj}")
        
        if path_obj.suffix.lower() != '.pdf':
            raise ValueError(f"Le fichier n'est pas un PDF: {path_obj}")
        
        logger.debug(f"document créé: {path_obj}")
        return cls(path_obj)

    def extract_text(self, classeur: Classeur) -> Optional[str]:
        """extrait le texte du document pdf avec swiftocr ou pdfplumer
        - vérification du suffixe .pdf
        - si extracteur est simple ou tolerant: extraire avec pdfplumer
        -   si texte, retourne texte
        -  extracteur is None ou mac, ou pas de texte avec pdfplumber: extraire avec swiftocr

        Returns:
            Texte extrait du PDF, ou None en cas d'erreur
        """

        if self.extension != '.pdf':
            logger.error("le fichier n'est pas un PDF")
            return None
        logger.debug("extraction de texte: vérifier les sauvegardes")
        # mettre les valeurs par défaut si elles n'ont pas été spécifiées en argument
        if self.pages is None:
            self.pages = classeur.config.pages or 2  # valeur du classeur ou par défaut
        if self.extracteur is None:
            self.extracteur = classeur.config.extracteur or "mac"  # valeur du classeur ou par défaut
        # vérifier les sauvegardes
        if self.extracteur == 'simple' and self.texte_simple:
            logger.debug("reprise de la sauvegarde texte_simple")
            self.texte = self.texte_simple
        if self.extracteur == 'tolerant' and self.texte_tolerant:
            logger.debug("reprise de la sauvegarde texte_tolerant")
            self.texte = self.texte_tolerant
        if self.extracteur == 'mac' and self.texte_mac:
            logger.debug("reprise de la sauvegarde texte_mac")
            self.texte = self.texte_mac
        if self.texte:
            return self.texte

        logger.debug(f"extraction de texte ({self.pages} page(s)) avec la méthode {self.extracteur}")
        texte:Optional[str] = None
        if self.extracteur == 'simple' or self.extracteur == "tolerant":
            texte = self.extract_text_pdf()
            if texte:
                if self.extracteur == "simple":
                    self.texte_simple = texte
                if self.extracteur == "tolerant":
                    self.texte_tolerant = texte
            else:
                logger.info(f"aucun texte extrait avec '{self.extracteur}' -> essai avec 'mac'")

        # si extracteur = 'mac' ou les autres méthodes n'ont rien donné (p. ex. image)
        if texte is None:
            texte = self.extract_text_swift()
            if texte:
                self.texte_mac = texte
            else:
                logger.warning(f"fichier sans texte avec la méthode {self.extracteur}, essayer un autre --extracteur")
                return None

        # normaliser les espaces, saut de lignes, apostrophes
        texte_normalise = ' '.join(texte.split()).replace("’", "'")
        texte_nfc = unicodedata.normalize('NFC', texte_normalise)  # !! problème découvert avec le ô de impôt
        logger.debug(f"texte normalisé de {self.pages} page(s):\n{texte_nfc}")
        logger.info(f"le texte ({self.pages} page(s)) extrait avec la méthode {self.extracteur}"
                    f" (affiché avec --log debug)")
        self.texte = texte_nfc
        if self.extracteur == "simple":
            self.texte_simple = texte_nfc
        if self.extracteur == "tolerant":
            self.texte_tolerant = texte_nfc
        if self.extracteur == "mac":
            self.texte_mac = texte_nfc

        return texte_nfc

    def extract_text_pdf(self) -> Optional[str]:
        """Extrait le texte du PDF en mode simple ou tolerant avec pdfplumber.
        Le nombre de pages extraites est limité par pages, argument cli ou configuration classeur
        
        Returns:
            Texte extrait du PDF, ou None en cas d'erreur
        """
        try:
            import pdfplumber
            with pdfplumber.open(self.path) as pdf:
                texte_extrait = ''
                for page in pdf.pages:
                    if self.extracteur == "simple":
                        texte_extrait += page.extract_text_simple()
                    if self.extracteur == "tolerant":
                    # pour les derniers pdf des extraits de compte de VZ qui comportent des espaces aléatoires:
                        texte_extrait += page.extract_text(
                            x_tolerance=4,  # tolérance horizontale pour grouper les caractères
                            y_tolerance=1,  # tolérance verticale
                            layout=True
                        )
                    if page.page_number == self.pages:
                        logger.debug(f"seules {self.pages} / {len(pdf.pages)} page(s) ont été extraites")
                        break
                if texte_extrait == '':
                    return None

            return texte_extrait

        except ImportError:
            raise ImportError("Le module pdfplumber n'est pas installé")
        except Exception as e:
            logger.error(f"erreur lors de l'extraction du texte: {e}")
            return None

    def extract_text_swift(self) -> Optional[str]:
        """Extrait le texte d'un fichier pdf avec le programme swift sur MacOS."""
        self.extracteur = 'mac'
        logger.debug(f"extraction swiftocr: {self.path} - {self.pages}")
        stdout = ''
        stderr = ''
        code = 0
        if Path(SWIFTOCR).exists():
            logger.info(f"appel du programme {SWIFTOCR} ...")
            result = subprocess.run(
                [SWIFTOCR, str(self.path), "--lang", "fr-FR", "--pages", str(self.pages)],
                capture_output=True,
                text=True
            )
            stdout = result.stdout  # contenu de stdout (str)
            stderr = result.stderr  # contenu de stderr (str)
            code = result.returncode  # 0 = succès
        else:
            logger.error(f"le programme swiftocr n'existe pas: {SWIFTOCR}")
            logger.info(f"essai du service ocr via api: {SWIFTOCR_URL} ...")
            req_data:bytes = (json.dumps({"file": str(self.path), "lang": "fr-FR", "pages": str(self.pages)})
                              .encode('utf-8'))
            req = urllib.request.Request(url=SWIFTOCR_URL, data=req_data, method="POST")

            try:
                with urllib.request.urlopen(req) as result:
                    if result.status == 200:
                        result_data = result.read().decode()
                        json_data = json.loads(result_data)
                        code = json_data.get("returncode", 1)
                        stdout = json_data.get("stdout", "")
                        stderr = json_data.get("stderr", "")
                    else:
                        logger.error(f"statut de la requête: {result.status}")
                        return None
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    logger.error(f"fichier non trouvé: {e}")
                else:
                    logger.error(f"une erreur est survenue: {e}")
            except Exception as e:
                logger.error(f"une erreur est survenue: {e}")
                return None

        if code == 0:
            return stdout
        else:
            logger.error(f"erreur swiftocr: {stderr}")
            return None

    def extract_pattern_values(self, classeur) -> bool:
        """Extrait les informations selon les définitions de la configuration
        (pattern) pour les ranger dans config.values
        """
        # les patterns définissent des informations à extraire du texte
        logger.debug("informations à extraire (patterns)")
        patterns = classeur.get_patterns()
        values = {}  # liste des valeurs trouvées
        compteur = compteur_ok = 0
        nombre_id = len(patterns)
        for pattern in patterns:
            compteur += 1
            match = re.search(patterns[pattern], self.texte)
            if match:
                compteur_ok += 1
                values[pattern] = match.group(1)
                logger.debug(f"{compteur}/{nombre_id} ✓ {pattern}: {patterns[pattern]} -> {match.group(1)}")
            else:
                values[pattern] = None
                logger.debug(f"{compteur}/{nombre_id} 𐄂 {pattern}: {patterns[pattern]} -> None")

        if compteur_ok == nombre_id:
            logger.info(f"patterns: {['✓ '+v+': '+values[v] if values[v] else '𐄂 '+v for v in values]}")
            self.patterns_ok = True
        else:
            logger.error(f"il manque des informations: "
                         f"{['✓ '+v if values[v] else '𐄂 '+v for v in values]}")
            self.patterns_ok = False

        self.pattern_values = values  # "values": {"pattern": "value", ...}
        return self.patterns_ok

    def check_nom_fichier(self, classeur) -> Optional[str]:
        # création du nom de fichier selon définition, liste d'éléments d'identification ou valeurs de patterns
        # (suffixe ? indique optionnel)
        # ex:   "nom_fichier": [["identification", 0], ["values","titre"], ["values","timestamp"], ["values","police?"]]
        pattern_fichier = classeur.get_nom_fichier()
        logger.debug(f"modèle du nom de fichier: {pattern_fichier}")
        if self.pattern_values is None:
            logger.error("il n'y a pas de valeur de pattern")
            return None
        nom_fichier = ""
        config = classeur.get_config()
        for element in pattern_fichier:
            logger.debug(f"partie: {element}")
            if element[0] == "values":
                if element[1].endswith('?'):  # element optionnel pour le nom de fichier
                    partie = self.pattern_values[element[1].rstrip('?')]
                    nom_fichier += ' ' + partie if partie else nom_fichier
                    logger.debug(f"{element[1]}: {partie} - nom_fichier: {nom_fichier}")
                else:
                    partie = self.pattern_values[element[1]]
                    if partie is None:
                        logger.error(f"'{element[0]}.{element[1]}' est un élément obligatoire pour le nom de fichier")
                        break
                    nom_fichier = nom_fichier + ' ' + partie
                    logger.debug(f"{element[1]}: {partie} - nom_fichier: {nom_fichier}")
            else:
                partie = config[element[0]][element[1]]
                if partie is None:
                    logger.error(f"'{element[0]}.{element[1]}' est un élément obligatoire pour le nom de fichier")
                    nom_fichier = ""
                    break
                nom_fichier = nom_fichier + ' ' + partie
                logger.debug(f"{element[1]}: {partie} - nom_fichier: {nom_fichier}")

        if nom_fichier != "":
            # remplacements de texte. exemple:
            # "transform": {
            #     "667.240.58.500": "(placements)",
            #     "667.238.47.500": "(pilier_3a)"
            # }
            config_transform:dict = classeur.get_transform()
            logger.debug(f"transformations: {config_transform}")
            for texte_avant in config_transform:
                texte_apres = config_transform[texte_avant]
                logger.debug(f"transformation: {texte_avant} -> {texte_apres}")
                nom_avant = nom_fichier
                nom_fichier = nom_avant.replace(texte_avant, texte_apres)
                if nom_avant != nom_fichier:  # replacement a eu lieu
                    logger.info(f"remplacement de '{texte_avant}' par '{texte_apres}'")

            # Remplacer les caractères interdits et limite la longueur
            nom_fichier = re.sub(r'[<>:"/\\|?*]', '_', nom_fichier)
            nom_fichier = unicodedata.normalize('NFC', nom_fichier[:100].strip() + '.pdf')

            logger.info(f"nom du fichier selon la configuration: '{nom_fichier}'")
            return nom_fichier
        return None

    def check_classeur(self, classeur) -> bool:
        self.classeur_ok = (self.path.parent == classeur.path)
        return self.classeur_ok

    def check_timestamp(self) -> bool:
        if not self.pattern_values:
            logger.error("la clé 'values' n'existe pas")
            return False
        date_fichier = self.pattern_values.get('timestamp', None)
        if not date_fichier:
            logger.error("la clé 'values/timestamp' n'existe pas")
            return False

        # formatage du timestamp
        date_obj = self.convertir_date(date_fichier)

        if self.mtime == date_obj:
            logger.info(f"la date de modification du fichier est correcte: {self.mtime}")
            self.timestamp_fichier_ok = True
        else:
            logger.error(f"le fichier n'a pas la date de modification correcte: {self.mtime}")
            self.timestamp_fichier_ok = False
        return self.timestamp_fichier_ok

    def check_permissions(self) -> bool:
        # chercher permissions
        if self.mode == MODE:  # 'r--------'
            logger.info("les permissions du fichier sont correctes: 'r--------'")
            self.permission_fichier_ok = True
        else:
            logger.error(f"les permissions du fichier sont fausses: {oct(self.mode)}")
            self.permission_fichier_ok = False

        return self.permission_fichier_ok

    def classement(self, classeur: Classeur) -> bool:
        # patterns
        pattern_ok = self.extract_pattern_values(classeur)
        if pattern_ok:
            self.nom_fichier = self.check_nom_fichier(classeur)
            self.nom_fichier_ok:bool = (self.path.name == self.nom_fichier)

        # path document ? path classeur
        self.check_classeur(classeur)

        # chercher timestamp
        timestamp_fichier_ok = self.check_timestamp()

        # chercher permissions
        permissions_ok = self.check_permissions()

        if self.nom_fichier_ok and timestamp_fichier_ok and permissions_ok:
            return True

        return False

    def ranger(self, classeur: Classeur) -> bool:
        # formatage du timestamp
        date_fichier = self.pattern_values.get('timestamp', None)
        date_obj = self.convertir_date(date_fichier)

        # option ranger: modifie le timestamp
        atime = mtime = date_obj.timestamp()
        os.utime(self.path, (atime, mtime))
        # self.mtime n'est pas modifié et garde le timestamp original
        print(f"  📅 Date de modification appliquée -> {date_obj.strftime('%d.%m.%Y')}")
        self.timestamp_fichier_ok = True

        # option ranger: modifie les permissions
        self.path.chmod(MODE)
        self.permission_fichier_ok = True
        print("  ℹ️ Permission changée en lecture seule -> 'r--------'")
        # masque l'extension du fichier (Unexpected Error. (-5000) doit être writable)
        # subprocess.run(["SetFile", "-a", "E", str( self.chemin_document)], check=True)
        # logger.info(f"L'extension du fichier est masquée")

        # option ranger: déplace / renomme le fichier
        # si le nouveau nom existe déjà, il ne faut pas l'écraser et créer un nouveau nom avec un suffixe
        nouveau_chemin: Path = classeur.path / self.nom_fichier
        if nouveau_chemin.exists():
            # ajoute un timestamp avant le suffixe
            nouveau_nom_avec_timestamp:str = self.nom_fichier.replace('.pdf', '_' + datetime.now().isoformat() + '.pdf')
            nouveau_chemin = classeur.path / nouveau_nom_avec_timestamp
            logger.warning(f"doublon: renommage du fichier -> {nouveau_nom_avec_timestamp}")

        # renomme et déplace de le fichier
        self.path = self.path.rename(nouveau_chemin)
        print(f"  ℹ️ Document classé -> '{self.path}'")

        # touch CONFIG_FILE pour avoir ce fichier en-haut de la liste
        atime = mtime = datetime.now().timestamp()
        os.utime(classeur.get_config_path(), (atime, mtime))

        return True

    def __str__(self) -> str:
        return f"Document({self.name}{self.extension})"
    
    def __repr__(self) -> str:
        return f"Document(path='{self.path}', name='{self.name}', extension='{self.extension}')"
