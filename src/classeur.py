#!/usr/bin/env python3
"""Module représentant un classeur (dossier avec configuration JSON)."""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import re

logger = logging.getLogger(__name__)

# Nom du fichier de configuration des classeurs
CLASSEUR_CONFIG_FILE = "-classeur.json"


@dataclass
class ClasseurConfig:
    """Configuration d'un classeur chargée depuis le fichier JSON.
    
    Attributes:
        description: Description du classeur
        identification: Liste de patterns à rechercher dans le texte du document
                       pour identifier s'il appartient à ce classeur
        patterns: texte à extraire pour utiliser en tant qu'élément
                comme titre, timestamp, etc
        transform: liste de texte avant/après pour remplacement
        nom_fichier: nom du fichier constitué d'une liste d'éléments
        pages: le nombre minimal de pages nécessaires pour l'identification et les patterns
        extracteur: module et méthode d'extraction de texte
    """
    description: str
    identification: List[str]
    patterns: Dict[str, str]
    transform: Optional[Dict[str, str]]
    nom_fichier: List[List[str]]
    pages: Optional[int]
    extracteur: Optional[str]

    # Ajout de la méthode pour rendre l'objet indexable
    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"Attribute '{key}' not found in ClasseurConfig")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClasseurConfig':
        """Crée une ClasseurConfig à partir d'un dictionnaire."""
        return cls(
            description=data.get("description", "pas de description"),
            pages=data.get("pages", None),
            extracteur=data.get("extracteur", None),
            identification=data.get("identification", []),
            patterns=data.get("patterns", {}),
            transform=data.get("transform", []),
            nom_fichier=data.get("nom_fichier",[])
        )


@dataclass
class Classeur:
    """Classe représentant un classeur (dossier avec fichier de configuration).
    
    Un classeur est un dossier contenant un fichier '-classeur.json' qui définit
    le type de document qu'il doit contenir.
    
    Attributes:
        path: Chemin absolu vers le dossier du classeur
        config: Configuration chargée depuis le fichier JSON (ClasseurConfig)
    """
    path: Path
    config: ClasseurConfig = field(default_factory=ClasseurConfig)
    
    @classmethod
    def from_directory(cls, directory: str) -> Optional['Classeur']:
        """Crée un Classeur à partir d'un dossier contenant un fichier -classeur.json.
        
        Args:
            directory: Chemin vers le dossier à vérifier
            
        Returns:
            Instance de Classeur si le fichier de configuration existe, None sinon
        """
        directory_path = Path(directory).resolve()
        config_file = directory_path / CLASSEUR_CONFIG_FILE
        
        if not config_file.exists():
            logger.debug(f"pas de fichier de configuration trouvé dans: {directory_path}")
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            config = ClasseurConfig.from_dict(config_data)
            logger.info(f"classeur trouvé: {directory_path} avec config {config}")
            return cls(directory_path, config)
            
        except json.JSONDecodeError as e:
            logger.error(f"erreur de lecture du fichier JSON: {config_file} - {e}")
            return None
        except Exception as e:
            logger.error(f"erreur lors de la création du classeur: {e}")
            return None
    
    @staticmethod
    def find_classeurs(base_dir: str) -> List['Classeur']:
        """Cherche tous les classeurs dans une arborescence de dossiers.
        
        Un classeur est un dossier contenant un fichier '-classeur.json'.
        
        Args:
            base_dir: Dossier de base pour la recherche (optionnel).
                     Si None, utilise le répertoire courant.
                     
        Returns:
            Liste des instances Classeur trouvées
        """
        classeurs = []
        
        base_dir = Path(base_dir).resolve()
        
        if not base_dir.exists():
            logger.warning(f"le dossier de base n'existe pas: {base_dir}")
            return classeurs
        
        if not base_dir.is_dir():
            logger.warning(f"le chemin n'est pas un dossier: {base_dir}")
            return classeurs
        
        logger.debug(f"recherche des classeurs dans: {base_dir}")
        
        for root, dirs, files in os.walk(base_dir):
            if CLASSEUR_CONFIG_FILE in files:
                classeur = Classeur.from_directory(root)
                if classeur:
                    classeurs.append(classeur)

        Classeur.path = base_dir
        return classeurs
    
    def get_config_path(self) -> Path:
        return self.path / CLASSEUR_CONFIG_FILE

    def get_description(self) -> Optional[str]:
        """Récupère la description du classeur.
        
        Returns:
            Description si définie dans la configuration, None sinon
        """
        return self.config.description
    
    def get_identification(self) -> List[str]:
        """Récupère les patterns d'identification du classeur.
        
        Returns:
            Liste des patterns à rechercher dans le texte du document
        """
        return self.config.identification or []

    def get_patterns(self) -> Union[dict[str, str], dict[Any, Any]]:
        """Récupère les patterns du classeur.

        Returns:
            Dictionnaire des patterns du classeur
        """
        return self.config.patterns or {}

    def get_config(self) -> ClasseurConfig:
        """Récupère la config classeur.

        Returns:
            Dictionnaire des consignes de configuration du classeur
        """
        return self.config

    def get_transform(self) -> dict[str, str]:
        """Récupère les ev. consignes de replacement de texte dans le nom de fichier

        Returns:
            Dictionnaire de remplacements: {'texte-à-remplacer': 'texte-de-remplacement', ...}
        """
        return self.config.transform or {}

    def get_nom_fichier(self) -> List[List[str]]:
        """Récupère le modèle pour le nom de fichier.

        Returns:
            Liste des éléments constituant le nom du fichier
        """
        return self.config.nom_fichier

    def can_identify_document(self, texte: str) -> bool:
        """Vérifie si le texte du document correspond aux patterns d'identification.
        
        Args:
            texte: Texte extrait du document
            
        Returns:
            True si tous les patterns sont présents dans le texte, False sinon
        """
        logger.debug(f"identification avec le classeur {self.get_description()}")
        patterns = self.get_identification()
        compteur = compteur_ok = 0
        nombre_elements = len(patterns)
        if nombre_elements == 0:
            return False
        for pattern in patterns:
            compteur += 1
            match = re.search(pattern, texte, re.IGNORECASE)
            if match:
                compteur_ok += 1
                logger.debug(f"{compteur}/{nombre_elements} ✓ '{pattern}' trouvé")
            else:
                logger.debug(f"{compteur}/{nombre_elements} 𐄂 '{pattern}' pas trouvé")
        if compteur_ok == nombre_elements:
            logger.info(f"le document est identifié avec {patterns}")
            logger.info(f"classeur trouvé: {self}")
            return True
        else:
            logger.info(f"le document n'a pas pu être identifié avec {patterns}")
            return False
    
    def __str__(self) -> str:
        description = self.get_description()
        # if Classeur.base:
        #     name = str(self.path.resolve()).replace(str(Classeur.base), "<base>")
        # else:
        #     name = self.path.name
        return f"Classeur({self.path.name}: {description})"
    
    def __repr__(self) -> str:
        return f"Classeur(path='{self.path}', config={self.config})"
