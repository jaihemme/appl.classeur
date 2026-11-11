#!/usr/bin/env python3
"""Tests pour l'identification des documents par les classeurs."""

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
    
    def test_classeur_config_creation(self):
        """Test la création de ClasseurConfig avec tous les champs."""
        config = ClasseurConfig(
            description="Test description",
            identification=["pattern1", "pattern2"],
            patterns={"timestamp": r"\d{2}\.\d{2}\.\d{4}"},
            transform=None,
            nom_fichier=[["values", "timestamp"]],
            pages=2,
            extracteur="simple"
        )
        assert config.description == "Test description"
        assert config.identification == ["pattern1", "pattern2"]
        assert config.patterns == {"timestamp": r"\d{2}\.\d{2}\.\d{4}"}
        assert config.pages == 2
        assert config.extracteur == "simple"
    
    def test_classeur_config_from_dict_complete(self):
        """Test from_dict avec toutes les données."""
        data = {
            "description": "Factures",
            "identification": ["facture", "paiement"],
            "patterns": {"date": r"\d{2}\.\d{2}\.\d{4}"},
            "transform": {"old": "new"},
            "nom_fichier": [["values", "date"]],
            "pages": 3,
            "extracteur": "simple"
        }
        config = ClasseurConfig.from_dict(data)
        assert config.description == "Factures"
        assert config.identification == ["facture", "paiement"]
        assert config.patterns == {"date": r"\d{2}\.\d{2}\.\d{4}"}
        assert config.pages == 3
        assert config.extracteur == "simple"
    
    def test_classeur_config_from_dict_partial(self):
        """Test from_dict avec des données partielles."""
        data = {"description": "Test", "identification": ["pattern"]}
        config = ClasseurConfig.from_dict(data)
        assert config.description == "Test"
        assert config.identification == ["pattern"]
        assert config.patterns == {}
        assert config.pages is None
        assert config.extracteur is None


class TestClasseurIdentification:
    """Tests pour l'identification des documents par les classeurs."""
    
    def test_can_identify_document_all_patterns_match(self):
        """Test can_identify_document quand tous les patterns correspondent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Factures",
                "identification": ["facture", "paiement"]
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            text = "Voici une FACTURE avec un PAIEMENT à effectuer"
            assert classeur.can_identify_document(text) is True
    
    def test_can_identify_document_case_insensitive(self):
        """Test que l'identification est insensible à la casse."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Test",
                "identification": ["FACTURE"]
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            text = "voici une facture en minuscules"
            assert classeur.can_identify_document(text) is True
    
    def test_can_identify_document_missing_one_pattern(self):
        """Test can_identify_document quand un pattern est manquant."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Factures",
                "identification": ["facture", "paiement"]
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            text = "Voici une facture mais pas de p a i e m e n t"
            assert classeur.can_identify_document(text) is False
    
    def test_can_identify_document_no_patterns(self):
        """Test can_identify_document quand il n'y a pas de patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Test",
                "identification": []
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            text = "n'importe quel texte"
            assert classeur.can_identify_document(text) is False
    
    def test_can_identify_document_partial_match(self):
        """Test can_identify_document avec une correspondance partielle."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Factures",
                "identification": ["facture", "paiement"]
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            # Seulement un des deux patterns est présent
            text = "Ceci est une facture"
            assert classeur.can_identify_document(text) is False
    
    def test_can_identify_document_regex_pattern(self):
        """Test can_identify_document avec des patterns regex."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Factures",
                "identification": [r"facture\s*n°\d+"]
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            text = "Document: facture n°12345"
            assert classeur.can_identify_document(text) is True
    
    def test_get_identification(self):
        """Test la méthode get_identification."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Test",
                "identification": ["pattern1", "pattern2"]
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            patterns = classeur.get_identification()
            assert patterns == ["pattern1", "pattern2"]
    
    def test_get_identification_empty(self):
        """Test get_identification avec une liste vide."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Test",
                "identification": []
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            patterns = classeur.get_identification()
            assert patterns == []
