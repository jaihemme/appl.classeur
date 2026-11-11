#!/usr/bin/env python3
"""Tests pour l'extraction de texte des documents."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajouter le dossier src au path pour les imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from document import Document
from classeur import ClasseurConfig


class TestDocumentExtractTextSimple:
    """Tests pour la méthode extract_text de Document."""
    
    def test_extract_text_method_exists(self):
        """Test que la méthode extract_text existe."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = Path(f.name)
        
        try:
            doc = Document(temp_pdf)
            assert hasattr(doc, 'texte')
            assert callable(doc.extract_text)
        finally:
            os.unlink(temp_pdf)
    
    @patch('pdfplumber.open')
    def test_extract_text_with_mock(self, mock_open):
        """Test extract_text avec un mock de pdfplumber."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = Path(f.name)
        
        try:
            doc = Document(temp_pdf)
            
            # Configurer le mock
            mock_pdf = MagicMock()
            mock_page1 = MagicMock()
            mock_page2 = MagicMock()
            mock_classeur = MagicMock()
            mock_classeur.config = ClasseurConfig(
                description='mock description',
                identification=[],
                patterns={},
                transform={},
                nom_fichier=[],
                pages=1,
                extracteur='simple'
            )
            mock_page1.extract_text_simple.return_value = "Page 1 text"
            mock_page2.extract_text_simple.return_value = "Page 2 text"
            mock_pdf.pages = [mock_page1, mock_page2]
            mock_open.return_value.__enter__.return_value = mock_pdf

            text = doc.extract_text(mock_classeur)
            assert text == "Page 1 textPage 2 text"
        finally:
            os.unlink(temp_pdf)
    
    @patch('pdfplumber.open')
    def test_extract_text_empty_text(self, mock_open):
        """Test extract_text quand le PDF n'a pas de texte."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = Path(f.name)
        
        try:
            doc = Document(temp_pdf)
            
            # Configurer le mock pour retourner un texte vide
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_classeur = MagicMock()
            mock_classeur.config = ClasseurConfig(
                description='description',
                identification=[],
                patterns={},
                transform={},
                nom_fichier=[],
                pages=1,
                extracteur='simple'
            )
            mock_page.extract_text_simple.return_value = ""
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf
            
            text = doc.extract_text(mock_classeur)
            assert text is None
        finally:
            os.unlink(temp_pdf)
    
    @patch('pdfplumber.open')
    def test_extract_text_exception(self, mock_open):
        """Test extract_text en cas d'exception."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = Path(f.name)
        
        try:
            doc = Document(temp_pdf)
            
            # Configurer le mock pour lever une exception
            mock_classeur = MagicMock()
            mock_classeur.config = ClasseurConfig(
                description='mock description',
                identification=[],
                patterns={},
                transform={},
                nom_fichier=[],
                pages=1,
                extracteur=None
            )
            mock_open.side_effect = Exception("Error opening PDF")
            
            text = doc.extract_text(mock_classeur)
            assert text is None
        finally:
            os.unlink(temp_pdf)
    
    @patch('pdfplumber.open')
    def test_extract_text_import_error(self, mock_open):
        """Test extract_text quand pdfplumber n'est pas installé."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = Path(f.name)
        
        try:
            doc = Document(temp_pdf)
            
            # Simuler ImportError
            mock_classeur = MagicMock()
            mock_classeur.config = ClasseurConfig(
                description='mock description',
                identification=[],
                patterns={},
                transform={},
                nom_fichier=[],
                pages=1,
                extracteur=None
            )
            mock_open.side_effect = ImportError("pdfplumber not installed")
            
            text = doc.extract_text(mock_classeur)
            assert text is None
        finally:
            os.unlink(temp_pdf)