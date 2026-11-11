#!/usr/bin/env python3
"""Tests pour les fonctions utilitaires du module classement."""

import os
import pytest
import tempfile
from pathlib import Path

# Ajouter le dossier src au path pour les imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from classement import trouver_base_recherche, trouver_fichiers_pdf


class TestTrouverBaseRecherche:
    """Tests pour la fonction trouver_base_recherche."""
    
    def test_base_provided(self):
        """Test quand base est fourni."""
        base = "/tmp/test_base"
        source = "/tmp/test_source.pdf"
        result = trouver_base_recherche(base, source)
        assert result == Path(base).resolve()
    
    def test_base_none_source_is_file(self):
        """Test quand base est None et source est un fichier."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = f.name
        
        try:
            result = trouver_base_recherche(None, temp_pdf)
            expected = Path(temp_pdf).resolve().parent
            assert result == expected
        finally:
            os.unlink(temp_pdf)
    
    def test_base_none_source_is_directory(self):
        """Test quand base est None et source est un dossier."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = trouver_base_recherche(None, temp_dir)
            assert result == Path(temp_dir).resolve()
    
    def test_base_empty_string(self):
        """Test quand base est une chaîne vide."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = trouver_base_recherche("", temp_dir)
            assert result == Path(temp_dir).resolve()


class TestTrouverFichiersPdf:
    """Tests pour la fonction trouver_fichiers_pdf."""
    
    def test_single_pdf_file(self):
        """Test avec un seul fichier PDF."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = f.name
        
        try:
            pdf_files = trouver_fichiers_pdf(temp_pdf)
            assert len(pdf_files) == 1
            assert pdf_files[0] == Path(temp_pdf).resolve()
        finally:
            os.unlink(temp_pdf)
    
    def test_directory_with_pdfs(self):
        """Test avec un dossier contenant plusieurs PDFs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer plusieurs fichiers PDF
            pdf_files_created = []
            for i in range(3):
                pdf_path = os.path.join(temp_dir, f"test{i}.pdf")
                with open(pdf_path, 'w') as f:
                    f.write(f"PDF content {i}")
                pdf_files_created.append(Path(pdf_path))
            
            # Créer un fichier non-PDF (doit être ignoré)
            txt_path = os.path.join(temp_dir, "test.txt")
            with open(txt_path, 'w') as f:
                f.write("Text content")
            
            pdf_files = trouver_fichiers_pdf(temp_dir)
            assert len(pdf_files) == 3
            for pdf in pdf_files_created:
                assert pdf.resolve() in pdf_files

    def test_directory_without_pdfs(self):
        """Test avec un dossier sans PDF."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer un fichier non-PDF
            txt_path = os.path.join(temp_dir, "test.txt")
            with open(txt_path, 'w') as f:
                f.write("Text content")
            
            with pytest.raises(ValueError, match="Aucun fichier PDF"):
                trouver_fichiers_pdf(temp_dir)
    
    def test_nonexistent_file(self):
        """Test avec un fichier inexistant."""
        with pytest.raises(ValueError, match="n'est ni un fichier ni un dossier"):
            trouver_fichiers_pdf("/nonexistent/file.pdf")
    
    def test_non_pdf_file(self):
        """Test avec un fichier qui n'est pas un PDF."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_txt = f.name
        
        try:
            with pytest.raises(ValueError, match="n'est pas un PDF"):
                trouver_fichiers_pdf(temp_txt)
        finally:
            os.unlink(temp_txt)
    
    def test_nonexistent_directory(self):
        """Test avec un dossier inexistant."""
        with pytest.raises(ValueError, match="n'est ni un fichier ni un dossier"):
            trouver_fichiers_pdf("/nonexistent/directory")
    
    def test_case_insensitive_extension(self):
        """Test que l'extension est insensible à la casse."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer des fichiers avec différentes casse d'extension
            pdf1 = os.path.join(temp_dir, "test1.PDF")
            pdf2 = os.path.join(temp_dir, "test2.Pdf")
            pdf3 = os.path.join(temp_dir, "test3.pdf")
            
            for pdf in [pdf1, pdf2, pdf3]:
                with open(pdf, 'w') as f:
                    f.write("PDF content")
            
            pdf_files = trouver_fichiers_pdf(temp_dir)
            assert len(pdf_files) == 3
