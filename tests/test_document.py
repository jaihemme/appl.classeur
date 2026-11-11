#!/usr/bin/env python3
"""Tests pour la classe Document."""

import os
import pytest
import tempfile
from pathlib import Path

# Ajouter le dossier src au path pour les imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from document import Document


class TestDocument:
    """Tests pour la classe Document."""
    
    def test_document_creation_with_path(self):
        """Test la création d'un Document avec un chemin."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = f.name
        
        try:
            doc = Document(temp_pdf)
            assert doc.path == Path(temp_pdf).resolve()
            assert doc.name == Path(temp_pdf).stem
            assert doc.extension == '.pdf'
        finally:
            os.unlink(temp_pdf)
    
    def test_document_from_path_valid_pdf(self):
        """Test la création via from_path avec un PDF valide."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = f.name
        
        try:
            doc = Document.from_path(temp_pdf)
            assert isinstance(doc, Document)
            assert doc.path == Path(temp_pdf).resolve()
            assert doc.extension == '.pdf'
        finally:
            os.unlink(temp_pdf)
    
    def test_document_from_path_nonexistent_file(self):
        """Test from_path avec un fichier inexistant."""
        with pytest.raises(ValueError, match="n'existe pas"):
            Document.from_path("/nonexistent/file.pdf")
    
    def test_document_from_path_not_pdf(self):
        """Test from_path avec un fichier qui n'est pas un PDF."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_txt = f.name
        
        try:
            with pytest.raises(ValueError, match="n'est pas un PDF"):
                Document.from_path(temp_txt)
        finally:
            os.unlink(temp_txt)
    
    def test_document_from_path_directory(self):
        """Test from_path avec un dossier."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="n'est pas un fichier"):
                Document.from_path(temp_dir)
    
    def test_document_str(self):
        """Test la représentation string du Document."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = f.name
        
        try:
            doc = Document(temp_pdf)
            str_repr = str(doc)
            assert doc.name in str_repr
            assert '.pdf' in str_repr
        finally:
            os.unlink(temp_pdf)
    
    def test_document_repr(self):
        """Test la représentation repr du Document."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = f.name
        
        try:
            doc = Document(temp_pdf)
            repr_str = repr(doc)
            assert 'Document' in repr_str
            assert 'path=' in repr_str
            assert 'name=' in repr_str
        finally:
            os.unlink(temp_pdf)
    
    def test_document_with_custom_name(self):
        """Test la création avec un nom personnalisé."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = f.name
        
        try:
            doc = Document(temp_pdf, name="custom_name")
            assert doc.name == "custom_name"
        finally:
            os.unlink(temp_pdf)
