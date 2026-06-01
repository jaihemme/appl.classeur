from pathlib import Path
from classeur import Classeur
from cli_options import CliOptions
import logging
import pdfplumber
from pdf2image import convert_from_path
import re
from datetime import datetime
from typing import Optional
import os
import subprocess
import easyocr
import unicodedata


logger = logging.getLogger(__name__)


class Document:
    SWIFTOCR = "/Users/yogi/Docker/appl.classeur/swiftocr"
    MODE: int = 0o100400  # 'r--------'
    DOCUMENT_PATTERN = "[a-z|A-Z|0-9]*.pdf"

    # def __init__(self, fichier, options.base, options.extractor, self.cli_options.ranger=False, options.texte=False):
    def __init__(self, chemin_fichier: Path, options: CliOptions):
        logger.debug(f"__init__: {chemin_fichier} - extracteur: {options.extractor} - ranger: {options.ranger} "
                     f"- texte: {options.texte}")
        self.chemin: Path = chemin_fichier  # le fichier existe, vérifié dans lister_fichiers
        self.cli_options: CliOptions = options
        # obtenir l'heure de modification (mtime) du fichier
        self.mtime: datetime = datetime.fromtimestamp(self.chemin.stat().st_mtime)
        # obtenir le type de fichier et ses permissions
        self.mode: int = self.chemin.stat().st_mode
        # classeur, si dossier avec fichier de configuration existe
        # s'il n'existe pas ou l'identification échoue, cherche le classeur qui correspond
        base_nfc = unicodedata.normalize('NFC', str(Path(options.base).resolve())) if options.base else None
        self.base: Path = Path(base_nfc) if base_nfc else Classeur.NOM_BASE
        self.classeur: Optional[Classeur] = Classeur(self.chemin.parent, option_base=False)
        self.config: dict = self.classeur.config if self.classeur else {}
        self.config_ok: bool = True if self.config else False
        self.extractor: str = options.extractor if options.extractor else self.config.get('module', None)
        self.pages: int = self.config.get('pages', 2)
        self.texte: str = self.extraire_texte()
        self.identification_ok: bool = self.verifier_identification() if self.texte else False
        # résultat de la recherche de patterns, résultat dans les values
        self.patterns_ok: bool = self.verifier_patterns() if self.identification_ok else False
        # résultat de la vérification du nom de fichier comparé à la config
        self.chemin_document: Optional[Path] = None
        self.nom_fichier_ok: bool = self.traitement_nom_fichier() if self.patterns_ok else False
        # résultat de la vérification de la date de modification du fichier, comparé à la config
        self.timestamp_fichier_ok: bool = self.traitement_date_fichier() if self.patterns_ok else False
        # résultat de la vérification des permissions du fichier
        self.permission_fichier_ok: bool = self.traitement_permissions_fichier() if self.nom_fichier_ok else False
        # résultat du placement de document (si tout est ok)
        self.classement_ok: bool = self.nom_fichier_ok and self.timestamp_fichier_ok and self.permission_fichier_ok

        self.log_all()
        if not options.texte:
            self.resumer()

    @classmethod
    def lister_fichiers(cls, options: CliOptions) -> list[Path]:
        source_path: Path = Path(options.source)
        fichier_nfc = unicodedata.normalize('NFC', str(source_path.resolve()))

        if source_path.is_file():
            if source_path.suffix == '.pdf':
                logger.info(f"liste avec 1 fichier pdf")
                return [Path(fichier_nfc)]
            else:
                logger.error(f"liste vide, le fichier '{options.source}' n'est pas PDF")
                return []
        if source_path.is_dir():
            liste = []
            for fichier_path in source_path.rglob(Document.DOCUMENT_PATTERN):
                fichier_nfc = unicodedata.normalize('NFC', str(fichier_path.resolve()))
                liste.append(Path(fichier_nfc))
            if liste:
                logger.info(f"liste avec {len(liste)} fichier(s) pdf")
                return liste
            else:
                logger.error(f"liste vide, pas trouvé de fichier pdf dans '{options.source}'")
                return []

        logger.error(f"liste vide, type de fichier non traité '{options.source}'")
        return []

    def log_all(self):
        logger.info(f"chemin: {self.chemin}")
        logger.info(f"mtime: {self.mtime}")
        logger.info(f"mode: {self.mode}")
        logger.info(f"options.extractor: {self.extractor}")
        logger.info(f"base: {self.base}")
        logger.info(f"classeur: {self.classeur}")
        logger.info(f"config: {self.config}")
        logger.info(f"module: '{self.extractor}'")
        logger.info(f"pages: '{self.pages}'")
        logger.info(f"texte: '{self.texte:.150s}'")
        logger.info(f"identification: {self.config.get('identification', [])}")
        logger.info(f"identification_ok: {self.identification_ok}")
        logger.info(f"patterns: {self.config.get('patterns', {})}")
        logger.info(f"patterns_ok: {self.patterns_ok}")
        logger.info(f"values: {self.config.get('values', {})}")
        logger.info(f"chemin_document: '{self.chemin_document}'")
        logger.info(f"nom_fichier_ok: {self.nom_fichier_ok}")
        logger.info(f"timestamp_fichier_ok: {self.timestamp_fichier_ok}")
        logger.info(f"permission_fichier_ok: {self.permission_fichier_ok}")
        logger.info(f"ranger: {self.cli_options.ranger}")
        logger.info(f"classement_ok: {self.classement_ok}\n")

    def extraire_texte(self) -> str:
        """extrait le texte du document pdf
        - vérification du suffixe .pdf
        - extraction de text standard (nombre de pages en fonction de config['pages'], par défaut 1)
        - si pas de texte (self.texte vide) et option_ocr, extraction de texte via ocr
        """

        if self.chemin.suffix != '.pdf':
            logger.error(f"Fichier non PDF")
            return ''

        if self.extractor is None or self.extractor == "mac":
            texte = self.extraire_texte_swift()
            self.extractor = "mac"
        else:
            texte = self.extraire_texte_pdf()
            if not texte:
                logger.info(f"Aucun texte extrait avec '{self.extractor}' -> essai avec 'mac'")
                texte = self.extraire_texte_swift()

        if texte == '':
            logger.warning(f"Fichier sans texte, essaie un autre --module")
            return ''

        if texte:
            # normaliser les espaces, saut de lignes, apostrophes
            texte_normalise = ' '.join(texte.split()).replace("’", "'")
            texte_nfc = unicodedata.normalize('NFC', texte_normalise) # !! problème découvert avec le ô de impôt
            logger.debug(f"texte normalisé de {self.pages} page(s):\n{texte_nfc}")
            logger.info(f"le texte a été extrait (affiché avec --log debug)")
            return texte_nfc

        logger.error(f"le texte n'a pas pu être extrait")
        return ''

    def extraire_texte_pdf(self):
        """Extrait du texte des <nombre_pages> premières pages"""
        logger.debug(f"extraire_texte_pdf : {self.chemin} - module: {self.extractor} - {self.pages} pages")
        try:
            with pdfplumber.open(self.chemin) as pdf:
                texte_extrait = ""
                for page in pdf.pages:
                    if self.extractor == "simple":
                        texte_extrait += page.extract_text_simple()
                    if self.extractor == "tolerant":
                    # pour les derniers pdf des extraits de compte de VZ qui comportent des espaces aléatoires:
                        texte_extrait += page.extract_text(
                            x_tolerance=4,  # tolérance horizontale pour grouper les caractères
                            y_tolerance=1,  # tolérance verticale
                            layout=True
                        )

                    if page.page_number == self.pages:
                        break

                if texte_extrait:
                    return texte_extrait

                logger.warning(f"Aucun texte extrait de {self.chemin.name}")
                return ''  # pas de texte

        except Exception as e:
            logger.error(f"Erreur lecture avec pdfplumber {self.chemin.name}: {e}")
            return ''

    def extraire_texte_swift(self):
        """Extrait le texte d'une image avec le programme swift sur MacOS."""
        self.extractor = 'mac'
        logger.debug(f"extraire_text_swift: {self.chemin} - {self.pages}")

        result = subprocess.run(
            [self.SWIFTOCR, str(self.chemin), "--lang", "fr-FR", "--pages", str(self.pages)],
            capture_output=True,
            text=True
        )

        stdout = result.stdout  # contenu de stdout (str)
        stderr = result.stderr  # contenu de stderr (str)
        code = result.returncode  # 0 = succès

        if code == 0:
            return stdout
        else:
            logger.error(f"Erreur swiftocr {stderr}")
            return ''

    def extraire_texte_easyocr(self):
        """Extrait le texte d'une image avec EasyOCR."""
        logger.debug(f"extraire_pages_image: {self.chemin} - {self.pages}")
        try:

            # Initialiser le lecteur (français)
            reader = easyocr.Reader(['fr'], gpu=True)

            # Convertir le PDF en images (une image par page)
            images = convert_from_path(self.chemin, fmt="jpeg")

            # Extraire le texte de chaque page
            textes = []
            for i, image in enumerate(images):
                logger.debug(f"Traitement page {i + 1}/{len(images)}...")

                # OCR sur l'image
                resultats = reader.readtext(image)

                # Extraire le texte
                texte_page = ' '.join([detection[1] for detection in resultats])
                textes.append(texte_page)

                # limiter le nombre de pages
                if i + 1 == self.pages:
                    logger.debug(f"limiter du nombre de pages {self.pages}")
                    logger.debug(f"texte normalisé de {i + 1} sur {len(images)} images:\n{textes}")
                    break

        except Exception as e:
            logger.error(f"Erreur lecture PDF avec easyocr {self.chemin.name}: {e}")
            return ''

        # Combiner toutes les pages
        # self.texte = '\n\n'.join(textes)
        return '\n\n'.join(textes)

    def verifier_identification(self) -> bool:
        # il faut du texte
        if not self.texte:
            logger.error(f"le document ne peut être identifié sans texte")
            return False

        # il faut les critères d'identification (fichier config d'un classeur)
        # sinon on cherche sur tous les classeurs
        self.identification_ok = False
        if not self.classeur or not self.config:
            Classeur(self.base, True)
            nombre_classeurs = len(Classeur.LISTE_CLASSEUR)
            logger.debug(f"recherche sur {nombre_classeurs} classeurs à partir de {self.base.name}")
            for index in range(0, nombre_classeurs):
                self.classeur = Classeur(Classeur.LISTE_CLASSEUR[index], False)
                self.config = Classeur.LISTE_CONFIG[index]
                logger.debug(f"classeur {index + 1}/{nombre_classeurs}: {self.config['description']}")
                if self.verifier_identification():
                    return True
            if not self.identification_ok:
                self.classeur = None
                self.config = {}
                return False

        # vérifie si le texte du document contient chacun des critères d'identification
        # le texte extrait contient par défaut 1 page. si la config l'exige, il faut en extraire plus
        if self.config['pages'] > self.pages:
            logger.debug(f"extraction de pages supplémentaires: {self.config['pages']} pages")
            self.extraire_texte()

        logger.debug(f"Identification classeur: {self.config.get('description', 'pas de description')}")
        config_identification = self.config['identification']
        logger.debug(f"Identification critères: {config_identification}")

        nombre_elements = len(config_identification)
        compteur = compteur_ok = 0
        for identification in config_identification:
            compteur += 1
            match = re.search(identification, self.texte, re.IGNORECASE)
            if match:
                compteur_ok += 1
                logger.debug(f"{compteur}/{nombre_elements} ✓ '{identification}' trouvé")
            else:
                logger.debug(f"{compteur}/{nombre_elements} 𐄂 '{identification}' pas trouvé")
        if compteur_ok == nombre_elements:
            logger.debug(f"le document est identifié avec {config_identification}")
            self.identification_ok = True
        else:
            logger.debug(f"document non identifié avec {config_identification}")
            self.identification_ok = False

        return self.identification_ok

    def verifier_patterns(self) -> bool:
        """Extrait les informations selon les définitions de la configuration
        (pattern) pour les ranger dans config.values
        """

        # les patterns définissent des informations à extraire du texte
        logger.debug(f"Informations à extraire (patterns)")
        patterns = self.config['patterns']
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
            logger.debug(f"toutes les informations ont été extraites")
            self.patterns_ok = True
        else:
            logger.debug(f"il manque des informations: "
                         f"{['✓ '+v if values[v] else '𐄂 '+v for v in values]}")
            self.patterns_ok = False

        self.config['values'] = values  # "values": {"pattern": "value", ...}
        return self.patterns_ok

    def traitement_nom_fichier(self) -> bool:
        # création du nom de fichier selon définition, liste d'éléments d'identification ou valeurs de patterns
        # (suffixe ? indique optionnel)
        # ex:   "nom_fichier": [["identification", 0], ["values","titre"], ["values","timestamp"], ["values","police?"]]
        logger.debug(f"config nom de fichier: {self.config['nom_fichier']}")
        if self.config.get('values', None) is None:
            logger.error(f"config/values n'existe pas")
            return False
        nom_fichier = ""
        for element in self.config['nom_fichier']:
            logger.debug(f"- partie: {element}")
            if self.config.get(element[0], None) is None:
                logger.error(f"config/{element[0]} n'existe pas")
                continue
            if element[0] == "values" and element[1].endswith('?'):  # element optionnel pour le nom de fichier
                partie = self.config[element[0]][element[1].rstrip('?')]
                nom_fichier += ' ' + partie if partie else nom_fichier
            else:
                partie = self.config[element[0]][element[1]]
                if partie is None:
                    logger.error(f"'{element[0]}.{element[1]}' est un élément obligatoire pour le nom de fichier")
                    nom_fichier = ""
                    break
                nom_fichier = nom_fichier + ' ' + partie
            logger.debug(f"> nom de fichier: {nom_fichier}")

        if nom_fichier != "":
            # remplacements de texte
            config_transform = self.config.get('transform', [])
            for texte_avant in config_transform:
                logger.debug(f"- transformation: {config_transform}")
                texte_apres = config_transform[texte_avant]
                nom_avant = nom_fichier
                nom_fichier = nom_fichier.replace(texte_avant, texte_apres)
                if nom_avant != nom_fichier:  # replacement a eu lieu
                    logger.info(f"remplacement '{texte_avant}' par '{texte_apres}'")

            # Remplacer les caractères interdits et limite la longueur
            nom_fichier = re.sub(r'[<>:"/\\|?*]', '_', nom_fichier)
            nom_fichier = unicodedata.normalize('NFC', nom_fichier[:100].strip() + '.pdf')

            self.config["values"]["nom_fichier"] = nom_fichier
            logger.info(f"nom du fichier selon config: '{nom_fichier}'")

        # chemin du document classé et nommé correctement
        self.chemin_document = self.classeur.chemin_classeur / nom_fichier
        if self.chemin == self.chemin_document:
            logger.info(f"nom_fichier_ok - base: {Classeur.NOM_BASE} "
                        f"/ classeur: {self.classeur.chemin_court} "
                        f"/ nom_fichier: {nom_fichier}")
            self.nom_fichier_ok = True
            return True

        if not self.cli_options.ranger:
            logger.error(f"le fichier doit être rangé: "
                         f"'{self.chemin}' -> '{self.classeur.chemin_court}/{nom_fichier}'")
            self.nom_fichier_ok = False
            return False

        # option ranger: déplace / renomme le fichier
        # si le nouveau nom existe déjà, il ne faut pas l'écraser et créer un nouveau nom avec un suffixe
        if self.chemin_document.exists():
            # ajoute un timestamp avant le suffixe
            nouveau_nom_avec_timestamp = self.chemin_document.name.replace(
                self.chemin_document.suffix, '_' + datetime.now().isoformat() + self.chemin_document.suffix)
            self.chemin_document = self.chemin_document.parent / nouveau_nom_avec_timestamp
            logger.warning(f"DOUBLON: renomme fichier -> {nouveau_nom_avec_timestamp}")

        # renomme et déplace de le fichier
        self.chemin = self.chemin.rename(self.chemin_document)
        print(f"ℹ️ document classé '{self.chemin}' -> '{self.chemin_document}'")
        self.nom_fichier_ok = True
        # touch CONFIG_FILE pour avoir ce fichier en-haut de la liste
        atime = mtime = datetime.now().timestamp()
        os.utime(self.classeur.chemin_config, (atime, mtime))
        return True

    @staticmethod
    def convertir_date(date_str: str) -> Optional[datetime]:
        # conversion de date en texte en date objet
        if date_str is None:
            logger.error(f"il manque une valeur pour la traitement de date")
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

        formats = ["%d.%m.%y", "%d.%m.%Y", "%d.%m.%Y %H:%M:%S"]
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_sub, fmt)
                logger.info(f"conversion date: {date_sub} -> {date_obj}")
                return date_obj
            except ValueError:
                continue

        logger.error(f"Format de date non reconnu : {date_str}")
        return None

    def traitement_date_fichier(self) -> bool:
        if self.config.get('values', None) is None:
            logger.error(f"config/values n'existe pas")
            return False
        # formatage du timestamp
        date_fichier = self.config['values'].get('timestamp', None)
        date_obj = self.convertir_date(date_fichier)

        if self.mtime == date_obj:
            logger.info(f"La date de modification du fichier est correcte: {self.mtime}")
            self.timestamp_fichier_ok = True
            return True
        else:
            logger.error(f"le fichier n'a pas la date de modification correcte: {self.mtime}")
            self.timestamp_fichier_ok = False
            if not self.cli_options.ranger:
                return False

        # option ranger: modifie le timestamp
        atime = mtime = date_obj.timestamp()
        os.utime(self.chemin_document, (atime, mtime))
        # modifier ou pas ?? self.mtime = datetime.fromtimestamp(self.chemin.stat().st_mtime)
        print(f"📅 date de modification appliquée -> {date_obj.strftime('%d.%m.%Y')}")
        self.timestamp_fichier_ok = True
        return True

    def traitement_permissions_fichier(self) -> bool:
        self.mode = self.chemin.stat().st_mode  # type de fichier et permissions
        if self.mode == Document.MODE:  # 'r--------'
            logger.info(f"Les permissions du fichier sont correctes: 'r--------'")
            self.permission_fichier_ok = True
            return True
        else:
            logger.error(f"Les permissions du fichier sont fausses.")
            self.permission_fichier_ok = False
            if not self.cli_options.ranger:
                return False

        # option ranger: modifie les permissions
        self.chemin_document.chmod(Document.MODE)
        self.permission_fichier_ok = True
        print(f"ℹ️ permission changée en lecture seule -> 'r--------'")
        # masque l'extension du fichier (Unexpected Error. (-5000) doit être writable)
        # subprocess.run(["SetFile", "-a", "E", str( self.chemin_document)], check=True)
        # logger.info(f"L'extension du fichier est masquée")
        return True

    def resumer(self):
        """Affiche l'état des vérifications"""
        print(f"\nTraitement du fichier '{self.chemin}':")
        if self.config_ok:
            print(f"✅ configuration de classeur présente: {self.config['description']}")
        else:
            print(f"❌ configuration manquante dans le classeur '{self.chemin.parent.name}'")
        if self.texte:
            print(f"✅ texte extrait avec module '{self.extractor}' "
                  f"({'config' if self.config.get('module') == self.extractor else 'argument'}), "
                  f"{self.pages} page(s)")
        else:
            print(f"❌ il n'y a pas de texte extrait avec module '{self.extractor}',"
                  f" essaie un autre module ('mac', 'simple', 'tolerant')")
            return

        if self.identification_ok:
            print(f"✅ le document est identifié avec les critères {self.config['identification']}")
            if not self.config_ok:
                print(f"📂 classeur '{self.classeur.chemin_classeur.name}' -> '{self.config['description']}'")
        else:
            print(f"❌ il manque des éléments d'identification {self.config.get('identification')}")
        if self.patterns_ok:
            print(f"✅ tous les pattern sont trouvés: {self.config['values']}")
        else:
            patterns = self.config.get('patterns',{})
            print(f"❌ il manque des pattern: "
                  f"{['✓ ' + p if self.config.get('values',{}).get(p) else '𐄂 ' + p for p in patterns]}"
            )
        nom_fichier = self.config.get("values", {}).get("nom_fichier")
        if self.nom_fichier_ok:
            print(f"✅ le nom du fichier est correct: '{nom_fichier}'")
            if self.chemin_document.name != nom_fichier:
                print(f"❗️ DOUBLON: -> {self.chemin_document.name}")
        else:
            print(f"❌ le nom du fichier ne correspond pas à '{nom_fichier}'")
        date_fichier = self.config.get("values", {}).get("timestamp")
        if self.timestamp_fichier_ok:
            print(f"✅ la date du fichier est correcte: {date_fichier}")
        else:
            print(f"❌ la date du fichier ne correspond pas à {date_fichier}")
        if self.permission_fichier_ok:
            print(f"✅ le fichier est verrouillé (permission en lecture seule)")
        else:
            print(f"❌ le fichier n'est pas verrouillé")
        if self.classement_ok:
            print(f"✅ le fichier est classé dans le bon classeur '{self.classeur.chemin_classeur.name}'")
        else:
            print(f"❌ le fichier n'est pas classé dans le bon classeur")
        if not self.cli_options.ranger and self.identification_ok and self.patterns_ok:
            print(f"⚠️ active l'option 'ranger' pour classer le document")


"""
document.__new__()
- chemin.isFile -> Document
- chemin.isDir -> List [str]
document.__init__()
- chemin: Path = Path du fichier source en NFC, le fichier existe, vérifié dans __new__
- mtime: datetime # Obtenir l'heure de modification (mtime) du fichier
- mode: int # type de fichier et permissions
- self.cli_options.ranger: bool # exécute le déplacement, renommage, changement de mtime et mode
- options.texte: bool # affiche le texte
- base: Path # argument ou Classeur.NOM_BASE, répertoire racine des classeurs
- classeur: Optional[Classeur] # parent du chemin ou None ou premier classeur identifié depuis base
- config: dict = self.classeur.config if self.classeur else {}
- config_ok: bool = True if self.config else False
- options.extractor: str # argument ou self.config.get('module', None). ??? simple
- pages:int = self.config.get('pages', 2)
- texte: str = self.extraire_texte(), toujours extraire_texte_swift() si texte est vide
- identification_ok: bool = self.verifier_identification() if self.texte else False
- patterns_ok: bool # résultat de la recherche de patterns, résultat dans les values if self.identification_ok else False
- chemin_document: Optional[Path] # chemin complet selon config if self.patterns_ok else False
- ??? chemin_ok: bool # si placement das le classeur est correct if self.patterns_ok else False
- nom_fichier_ok: bool # résultat de la vérification du nom de fichier comparé à la config
- timestamp_fichier_ok: bool # résultat de la vérification de la date de modification du fichier, comparé à la config
- permission_fichier_ok: bool # résultat de la vérification des permissions du fichier if self.nom_fichier_ok else False
- classement_ok: bool # résultat du placement de document (si tout est ok)
        
option_base dossier: définit la base des classeurs
option_log niveau: définit la verbosité des logs
options.extractor: module d'extraction ('mac' pour les images), easyocr s'il faut vraiment

logger.error(f"𐄂 ...)
logger.info(f"✓ ...)
logger.warning(f"⚠ ...)

print(f"✅...) 
print(f"❌...)
print(f"⚠️...)
print(f"ℹ️...)

"""
