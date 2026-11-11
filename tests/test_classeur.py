#!/usr/bin/env python3
"""Tests pour la classe Classeur."""

import json
import os
import pytest
import tempfile
from pathlib import Path

# Ajouter le dossier src au path pour les imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from classeur import Classeur, ClasseurConfig, CLASSEUR_CONFIG_FILE


class TestClasseurConfig:
    """Tests pour la classe ClasseurConfig."""
    
    def test_classeur_config_from_dict(self):
        """Test la création de ClasseurConfig à partir d'un dictionnaire."""
        data = {
            "description": "Dossier pour les factures",
            "identification": ["facture", "paiement"]
        }
        config = ClasseurConfig.from_dict(data)
        assert config.description == "Dossier pour les factures"
        assert config.identification == ["facture", "paiement"]
    
    def test_classeur_config_from_dict_partial(self):
        """Test ClasseurConfig avec des données partielles."""
        data = {"description": "contrat"}
        config = ClasseurConfig.from_dict(data)
        assert config.description == "contrat"
        assert config.identification == []
        assert config.patterns == {}
        assert config.transform == []
        assert config.nom_fichier == []



class TestClasseur:
    """Tests pour la classe Classeur."""
    
    def test_classeur_from_directory_with_config(self):
        """Test la création d'un Classeur à partir d'un dossier avec config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {"description": "Dossier pour les factures"}
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            assert classeur is not None
            assert classeur.path == Path(temp_dir).resolve()
            assert classeur.get_description() == "Dossier pour les factures"
    
    def test_classeur_from_directory_without_config(self):
        """Test from_directory avec un dossier sans fichier de config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            classeur = Classeur.from_directory(temp_dir)
            assert classeur is None
    
    def test_classeur_from_directory_invalid_json(self):
        """Test from_directory avec un fichier JSON invalide."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write("invalid json content")
            
            classeur = Classeur.from_directory(temp_dir)
            assert classeur is None
    
    def test_find_classeurs_in_directory(self):
        """Test la recherche de classeurs dans un dossier."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer un sous-dossier avec config
            subdir1 = os.path.join(temp_dir, "classeur1")
            os.makedirs(subdir1)
            config1 = {"description": "facture"}
            with open(os.path.join(subdir1, CLASSEUR_CONFIG_FILE), 'w') as f:
                json.dump(config1, f)
            
            # Créer un autre sous-dossier avec config
            subdir2 = os.path.join(temp_dir, "classeur2")
            os.makedirs(subdir2)
            config2 = {"description": "contrat"}
            with open(os.path.join(subdir2, CLASSEUR_CONFIG_FILE), 'w') as f:
                json.dump(config2, f)
            
            # Créer un dossier sans config (ne doit pas être trouvé)
            subdir3 = os.path.join(temp_dir, "autre")
            os.makedirs(subdir3)
            
            classeurs = Classeur.find_classeurs(temp_dir)
            assert len(classeurs) == 2
            descriptions_trouves = {c.get_description() for c in classeurs}
            assert descriptions_trouves == {"facture", "contrat"}
    
    def test_find_classeurs_no_config_files(self):
        """Test find_classeurs quand aucun fichier de config n'existe."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer des dossiers sans fichiers de config
            os.makedirs(os.path.join(temp_dir, "dossier1"))
            os.makedirs(os.path.join(temp_dir, "dossier2"))
            
            classeurs = Classeur.find_classeurs(temp_dir)
            assert len(classeurs) == 0
    
    def test_find_classeurs_nonexistent_directory(self):
        """Test find_classeurs avec un dossier inexistant."""
        classeurs = Classeur.find_classeurs("/nonexistent/directory")
        assert len(classeurs) == 0
    
    def test_classeur_str(self):
        """Test la représentation string du Classeur."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {"description": "test"}
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            str_repr = str(classeur)
            assert "Classeur" in str_repr
            assert "test" in str_repr
    
    def test_classeur_repr(self):
        """Test la représentation repr du Classeur."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {"type": "test"}
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            repr_str = repr(classeur)
            assert "Classeur" in repr_str
            assert "path=" in repr_str
            assert "config=" in repr_str

    def test_classeur_get_description_missing(self):
        """Test get_description quand la description n'est pas définie."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {}
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            assert classeur.get_description() == 'pas de description'
    
    def test_classeur_get_identification_patterns(self):
        """Test get_identification_patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {"description": "test", "identification": ["pattern1", "pattern2"]}
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            patterns = classeur.get_identification()
            assert patterns == ["pattern1", "pattern2"]
    
    def test_classeur_can_identify_document_true(self):
        """Test can_identify_document quand le texte correspond."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {"identification": ["facture", "paiement"]}
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            text = "Ce document contient une FACTURE et un PAIEMENT"
            assert classeur.can_identify_document(text) is True
    
    def test_classeur_can_identify_document_false(self):
        """Test can_identify_document quand le texte ne correspond pas."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {"identification": ["facture", "paiement"]}
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            text = "Ce document contient un contrat"
            assert classeur.can_identify_document(text) is False
    
    def test_classeur_can_identify_document_no_patterns(self):
        """Test can_identify_document quand il n'y a pas de patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {"type": "test"}
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            text = "n'importe quel texte"
            assert classeur.can_identify_document(text) is False
