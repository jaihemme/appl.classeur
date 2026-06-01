"""Tests for document.py module."""
import pytest
import json
from pathlib import Path
from datetime import datetime
# from unittest.mock import patch, MagicMock
import os

# Import modules
from src.document import Document
from src.classeur import Classeur
from src.cli_options import CliOptions


class TestDocumentNew:
    """Tests for Document.__new__ method."""

    def test_new_with_nonexistent_file(self, tmp_path):
        """Test __new__ with a non-existent file."""
        with pytest.raises(FileNotFoundError):
            Document(tmp_path / "nonexistent.pdf", CliOptions())

    def test_new_with_directory(self, tmp_path):
        """Test __new__ with a directory - should return list of PDFs."""
        # Create test directory with PDFs
        test_dir = tmp_path / "pdfs"
        test_dir.mkdir()
        
        # Create some PDF files
        (test_dir / "test1.pdf").write_text("%PDF-1.4")
        (test_dir / "test2.pdf").write_text("%PDF-1.4")
        (test_dir / "ignored.txt").write_text("not a pdf")
        
        documents: list = Document.lister_fichiers(CliOptions(str(test_dir)))
        
        assert len(documents) == 2
        assert all("test" in str(f) for f in documents)
        assert all(str(f).endswith(".pdf") for f in documents)

    def test_new_with_valid_pdf(self, tmp_path):
        """Test __new__ with a valid PDF file - should return Document instance."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4\n1 0 obj\n>>\nendobj")
        
        result = Document(pdf_path, CliOptions(extractor='simple'))
        
        # Note: This will fail during __init__ because pdfplumber can't read this
        # puis il essaie avec 'mac' sans succès aussi
        assert result.chemin == pdf_path

    def test_new_with_non_pdf_file(self, tmp_path):
        """Test __new__ with a non-PDF file."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("not a pdf")
        
        #with pytest.raises(ValueError, match="Chemin de type indéfinie"):
        #    Document(str(text_file), None, None, False, False)
        document = Document(text_file, CliOptions(extractor='simple'))
        assert document.texte == ''

class TestDocumentTextExtraction:
    """Tests for text extraction methods."""

    def test_extraire_texte_swift_mock(self, tmp_path, monkeypatch):
        """Test SwiftOCR text extraction with mock."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Create mock swiftocr that returns predictable text
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
if [[ "$*" == *"test.pdf"* ]]; then
    echo "Facture TEST-1234 Date: 15.05.2024"
    exit 0
else
    echo ""
    exit 1
fi
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        doc.pages = 1
        
        texte = doc.extraire_texte_swift()
        
        assert "Facture" in texte
        assert "TEST-1234" in texte

    def test_extraire_texte_swift_error(self, tmp_path, monkeypatch):
        """Test SwiftOCR text extraction with error."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Create mock swiftocr that fails
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Error: File not found" >&2
exit 1
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        doc.pages = 1
        
        texte = doc.extraire_texte_swift()
        
        assert texte == ""


class TestDocumentTextNormalization:
    """Tests for text normalization."""

    def test_normalize_spaces(self, tmp_path, monkeypatch):
        """Test that spaces are normalized."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Mock extraction to return text with extra spaces
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture  n°   TEST-1234   Date:  15.05.2024"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        doc.pages = 1
        
        texte = doc.extraire_texte()
        
        # Should have normalized spaces
        assert "  " not in texte
        assert "Facture n° TEST-1234 Date: 15.05.2024" in texte

    def test_normalize_apostrophes(self, tmp_path, monkeypatch):
        """Test that apostrophes are normalized."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Mock extraction to return text with special apostrophe
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "c'est une facture d'assurance"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        doc.pages = 1
        
        texte = doc.extraire_texte()
        
        # Should have normalized apostrophe
        assert "c'est" in texte or "c'est" in texte.replace("'", "'")


class TestDocumentIdentification:
    """Tests for document identification."""

    def test_verifier_identification_success(self, tmp_path, monkeypatch):
        """Test successful identification."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture", "TEST-1234"],
            "patterns": {},
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture TEST-1234 Date: 15.05.2024"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='simple', base=str(classeur_dir)))
        
        assert doc.identification_ok is True

    def test_verifier_identification_failure(self, tmp_path, monkeypatch):
        """Test failed identification."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture", "MISSING-PATTERN"],
            "patterns": {},
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture TEST-1234 Date: 15.05.2024"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac', base=str(classeur_dir)))
        
        assert doc.identification_ok is False


class TestDocumentPatterns:
    """Tests for pattern verification."""

    def test_verifier_patterns_success(self, tmp_path, monkeypatch):
        """Test successful pattern matching."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture"],
            "patterns": {
                "reference": "(TEST-\\d{4})",
                "date": "(\\d{2}\\.\\d{2}\\.\\d{4})"
            },
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture TEST-1234 Date: 15.05.2024"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac', base=str(classeur_dir)))
        
        assert doc.patterns_ok is True
        assert doc.config["values"]["reference"] == "TEST-1234"
        assert doc.config["values"]["date"] == "15.05.2024"

    def test_verifier_patterns_failure(self, tmp_path, monkeypatch):
        """Test failed pattern matching."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture"],
            "patterns": {
                "reference": "(TEST-\\d{4})",
                "missing_pattern": "(NOT-PRESENT)"
            },
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture TEST-1234 Date: 15.05.2024"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        
        assert doc.patterns_ok is False


class TestDocumentNomFichier:
    """Tests for filename construction."""

    def test_traitement_nom_fichier_success(self, tmp_path, monkeypatch):
        """Test successful filename construction."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture"],
            "patterns": {
                "reference": "(TEST-\\d{4})",
                "date": "(\\d{2}\\.\\d{2}\\.\\d{4})"
            },
            "nom_fichier": [
                ["values", "date"],
                ["values", "reference"]
            ]
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF in classeur directory
        nom_fichier = "15.05.2024 TEST-1234.pdf"
        pdf_path = classeur_dir / nom_fichier
        pdf_path.write_text("%PDF-1.4")
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture TEST-1234 Date: 15.05.2024"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        
        assert doc.nom_fichier_ok is True
        assert doc.config["values"]["nom_fichier"] == nom_fichier

    def test_traitement_nom_fichier_with_transform(self, tmp_path, monkeypatch):
        """Test filename construction with transform."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture"],
            "patterns": {
                "type": "(Facture)",
                "reference": "(TEST-\\d{4})"
            },
            "transform": {
                "Facture": "FACT"
            },
            "nom_fichier": [
                ["values", "type"],
                ["values", "reference"]
            ]
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF in classeur directory
        pdf_path = classeur_dir / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture TEST-1234"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        
        # Should have transformed "Facture" to "FACT"
        assert "FACT" in doc.config["values"]["nom_fichier"]

#     def test_traitement_nom_fichier_with_optional_field(self, tmp_path, monkeypatch):
#         """Test filename construction with optional field.
#         ILLOGIQUE si pattern_ok est obligatoire
#         """
#         # Setup classeur config
#         classeur_dir = tmp_path / "classeur"
#         classeur_dir.mkdir()
#         config_file = classeur_dir / "-classeur.json"
#
#         config = {
#             "description": "Test Classeur",
#             "pages": 1,
#             "identification": ["Facture"],
#             "patterns": {
#                 "reference": "(TEST-\\d{4})",
#                 "optional_field": "(OPTIONAL-\\d+)"
#             },
#             "nom_fichier": [
#                 ["values", "reference"],
#                 ["values", "optional_field?"]
#             ]
#         }
#         with open(config_file, "w") as f:
#             json.dump(config, f)
#
#         # Create PDF in classeur directory
#         pdf_path = classeur_dir / "test.pdf"
#         pdf_path.write_text("%PDF-1.4")
#
#         # Mock SwiftOCR - no optional field in text
#         mock_script = tmp_path / "swiftocr"
#         mock_script.write_text("""#!/bin/bash
# echo "Facture TEST-1234"
# exit 0
# """)
#         mock_script.chmod(0o755)
#         monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
#
#         # Reset class variables
#         Classeur.LISTE_CLASSEUR = []
#         Classeur.LISTE_CONFIG = []
#         Classeur.NOM_BASE = Path(tmp_path)
#
#         doc = Document(str(pdf_path), str(tmp_path), "mac", False, False)
#
#         # Should not fail even without optional field
#         assert doc.nom_fichier_ok is True
#         # Should not include the optional field
#         assert "OPTIONAL" not in doc.config["values"]["nom_fichier"]


class TestDocumentDate:
    """Tests for date conversion and file date treatment."""

    def test_convertir_date_dd_mm_yyyy(self):
        """Test date conversion from dd.mm.yyyy format."""
        date_str = "15.05.2024"
        result = Document.convertir_date(date_str)
        
        assert result is not None
        assert result.day == 15
        assert result.month == 5
        assert result.year == 2024

    def test_convertir_date_dd_mm_yy(self):
        """Test date conversion from dd.mm.yy format."""
        date_str = "15.05.24"
        result = Document.convertir_date(date_str)
        
        assert result is not None
        assert result.day == 15
        assert result.month == 5
        assert result.year == 2024  # Should be 2024, not 1924

    def test_convertir_date_with_month_name(self):
        """Test date conversion with month name."""
        date_str = "15 janvier 2024"
        result = Document.convertir_date(date_str)
        
        assert result is not None
        assert result.day == 15
        assert result.month == 1
        assert result.year == 2024

    def test_convertir_date_none(self):
        """Test date conversion with None."""
        result = Document.convertir_date(None)
        assert result is None

    def test_convertir_date_invalid(self):
        """Test date conversion with invalid format."""
        date_str = "invalid-date"
        result = Document.convertir_date(date_str)
        assert result is None

    def test_traitement_date_fichier_success(self, tmp_path, monkeypatch):
        """Test successful file date treatment."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        # Use today's date for the test
        now = datetime.now()
        today = now.strftime("%d.%m.%Y")
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture", "test"],
            "patterns": {
                "timestamp": f"timestamp=({today})"
            },
            "nom_fichier": [["identification", 1]]
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF in classeur directory with today's timestamp
        pdf_path = classeur_dir / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        # Set file modification time to today

        timestamp_minuit = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        os.utime(pdf_path, (timestamp_minuit, timestamp_minuit))
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text(f"""#!/bin/bash
echo "Facture timestamp={today} test pour le nom du fichier"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        
        # Date should match
        assert doc.timestamp_fichier_ok is True


class TestDocumentPermissions:
    """Tests for file permission treatment."""

    def test_traitement_permissions_fichier_readonly(self, tmp_path, monkeypatch):
        """Test permission treatment for read-only file."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture", "test"],
            "patterns": {},
            "nom_fichier": [["identification", 1]]
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF in classeur directory with read-only permissions
        # le nom doit correspondre à "nom_fichier" de la config
        pdf_path = classeur_dir / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Set read-only permissions (r--------)
        pdf_path.chmod(0o400)
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture blabla test"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        
        # Permissions should match
        assert doc.permission_fichier_ok is True


class TestDocumentRanger:
    """Tests for ranger (file organization) functionality."""

    def test_ranger_option_false(self, tmp_path, monkeypatch):
        """Test that ranger=False doesn't modify files."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture"],
            "patterns": {
                "reference": "(TEST-\\d{4})"
            },
            "nom_fichier": [["values", "reference"]]
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF in different directory
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        original_path = pdf_path
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture TEST-1234"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        
        # File should not have been moved
        assert pdf_path.exists()
        assert doc.classement_ok is False

    def test_nom_fichier_ok_without_ranger(self, tmp_path, monkeypatch):
        """Test that nom_fichier_ok is False when file needs to be moved."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture"],
            "patterns": {
                "reference": "(NEW-NAME)"
            },
            "nom_fichier": [["values", "reference"]]
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF with different name
        pdf_path = classeur_dir / "old_name.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Facture NEW-NAME"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        
        # File name should not match
        assert doc.nom_fichier_ok is False


class TestDocumentResumer:
    """Tests for resumer (summary) method."""

    def test_resumer_with_all_ok(self, tmp_path, monkeypatch, capsys):
        """Test resumer with all validations passing."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        today = datetime.now().strftime("%d.%m.%Y")
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["Facture"],
            "patterns": {
                "reference": "(TEST-\\d{4})"
            },
            "nom_fichier": [["values", "reference"]]
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF with matching name
        pdf_path = classeur_dir / "TEST-1234.pdf"
        pdf_path.write_text("%PDF-1.4")
        pdf_path.chmod(0o400)  # Read-only
        
        # Set file modification time to today
        now = datetime.now().timestamp()
        pdf_path.touch()
        os.utime(pdf_path, (now, now))
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text(f"""#!/bin/bash
echo "Facture TEST-1234 Date: {today}"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        doc.resumer()
        
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "classé" in captured.out.lower()

    def test_resumer_with_errors(self, tmp_path, monkeypatch, capsys):
        """Test resumer with validation errors."""
        # Setup classeur config
        classeur_dir = tmp_path / "classeur"
        classeur_dir.mkdir()
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test Classeur",
            "pages": 1,
            "identification": ["MISSING-PATTERN"],
            "patterns": {},
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create PDF
        pdf_path = classeur_dir / "test.pdf"
        pdf_path.write_text("%PDF-1.4")
        
        # Mock SwiftOCR
        mock_script = tmp_path / "swiftocr"
        mock_script.write_text("""#!/bin/bash
echo "Some text without pattern"
exit 0
""")
        mock_script.chmod(0o755)
        monkeypatch.setattr(Document, "SWIFTOCR", str(mock_script))
        
        # Reset class variables
        Classeur.LISTE_CLASSEUR = []
        Classeur.LISTE_CONFIG = []
        Classeur.NOM_BASE = Path(tmp_path)
        
        doc = Document(pdf_path, CliOptions(extractor='mac'))
        doc.resumer()
        
        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "identification" in captured.out.lower()
