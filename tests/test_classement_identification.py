#!/usr/bin/env python3
"""Tests pour la fonction identifier_document dans classement.py."""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Ajouter le dossier src au path pour les imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from classeur import Classeur, CLASSEUR_CONFIG_FILE
from classement import identifier_document


class TestIdentifierDocument:
    """Tests pour la fonction identifier_document."""
    
    def test_identifier_document_success(self):
        """Test identifier_document avec succès."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer un classeur
            config = {
                "description": "Factures",
                "identification": ["facture"]
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            
            # Créer un mock de document
            mock_doc = MagicMock()
            mock_doc.name = "test_doc"
            mock_doc.extract_text.return_value = "Ceci est une facture"
            
            result = identifier_document(mock_doc, [classeur])
            assert result == classeur
    
    def test_identifier_document_no_text(self):
        """Test identifier_document quand aucun texte n'est extrait."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Factures",
                "identification": ["facture"]
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            
            mock_doc = MagicMock()
            mock_doc.name = "empty_doc"
            mock_doc.extract_text.return_value = None
            
            result = identifier_document(mock_doc, [classeur])
            assert result is None
    
    def test_identifier_document_no_matching_classeur(self):
        """Test identifier_document quand aucun classeur ne correspond."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "description": "Factures",
                "identification": ["facture"]
            }
            config_file = os.path.join(temp_dir, CLASSEUR_CONFIG_FILE)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            classeur = Classeur.from_directory(temp_dir)
            
            mock_doc = MagicMock()
            mock_doc.name = "other_doc"
            mock_doc.extract_text.return_value = "Ceci est un contrat"
            
            result = identifier_document(mock_doc, [classeur])
            assert result is None
    
    def test_identifier_document_multiple_classeurs_first_match(self):
        """Test identifier_document avec plusieurs classeurs - premier match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer deux classeurs
            subdir1 = os.path.join(temp_dir, "classeur_factures")
            subdir2 = os.path.join(temp_dir, "classeur_contrats")
            os.makedirs(subdir1)
            os.makedirs(subdir2)
            
            config1 = {
                "description": "Factures",
                "identification": ["facture"]
            }
            config2 = {
                "description": "Contrats",
                "identification": ["contrat"]
            }
            
            with open(os.path.join(subdir1, CLASSEUR_CONFIG_FILE), 'w') as f:
                json.dump(config1, f)
            with open(os.path.join(subdir2, CLASSEUR_CONFIG_FILE), 'w') as f:
                json.dump(config2, f)
            
            classeur1 = Classeur.from_directory(subdir1)
            classeur2 = Classeur.from_directory(subdir2)
            
            # Test avec un document qui correspond au premier classeur
            mock_doc = MagicMock()
            mock_doc.name = "facture_doc"
            mock_doc.extract_text.return_value = "Ceci est une facture"
            
            result = identifier_document(mock_doc, [classeur1, classeur2])
            assert result == classeur1
    
    def test_identifier_document_multiple_classeurs_second_match(self):
        """Test identifier_document avec plusieurs classeurs - second match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer deux classeurs
            subdir1 = os.path.join(temp_dir, "classeur_factures")
            subdir2 = os.path.join(temp_dir, "classeur_contrats")
            os.makedirs(subdir1)
            os.makedirs(subdir2)
            
            config1 = {
                "description": "Factures",
                "identification": ["facture"]
            }
            config2 = {
                "description": "Contrats",
                "identification": ["contrat"]
            }
            
            with open(os.path.join(subdir1, CLASSEUR_CONFIG_FILE), 'w') as f:
                json.dump(config1, f)
            with open(os.path.join(subdir2, CLASSEUR_CONFIG_FILE), 'w') as f:
                json.dump(config2, f)
            
            classeur1 = Classeur.from_directory(subdir1)
            classeur2 = Classeur.from_directory(subdir2)
            
            # Test avec un document qui correspond au second classeur
            mock_doc = MagicMock()
            mock_doc.name = "contrat_doc"
            mock_doc.extract_text.return_value = "Ceci est un contrat"
            
            result = identifier_document(mock_doc, [classeur1, classeur2])
            assert result == classeur2
    
    def test_identifier_document_no_classeurs(self):
        """Test identifier_document avec une liste vide de classeurs."""
        mock_doc = MagicMock()
        mock_doc.name = "test_doc"
        mock_doc.extract_text.return_value = "Some text"
        
        result = identifier_document(mock_doc, [])
        assert result is None
    
    def test_identifier_document_all_classeurs_fail(self):
        """Test identifier_document quand tous les classeurs échouent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer deux classeurs
            subdir1 = os.path.join(temp_dir, "classeur1")
            subdir2 = os.path.join(temp_dir, "classeur2")
            os.makedirs(subdir1)
            os.makedirs(subdir2)
            
            config1 = {
                "description": "Type1",
                "identification": ["pattern1"]
            }
            config2 = {
                "description": "Type2",
                "identification": ["pattern2"]
            }
            
            with open(os.path.join(subdir1, CLASSEUR_CONFIG_FILE), 'w') as f:
                json.dump(config1, f)
            with open(os.path.join(subdir2, CLASSEUR_CONFIG_FILE), 'w') as f:
                json.dump(config2, f)
            
            classeur1 = Classeur.from_directory(subdir1)
            classeur2 = Classeur.from_directory(subdir2)
            
            # Test avec un document qui ne correspond à aucun classeur
            mock_doc = MagicMock()
            mock_doc.name = "other_doc"
            mock_doc.extract_text.return_value = "Some other text"
            
            result = identifier_document(mock_doc, [classeur1, classeur2])
            assert result is None
