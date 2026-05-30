"""Pytest configuration and fixtures for appl.classeur tests."""
import pytest
from pathlib import Path
import sys
import os

# Add src directory to Python path
SRC_PATH = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_PATH))


# =============================================================================
# FIXTURES: Paths
# =============================================================================

@pytest.fixture
def src_dir() -> Path:
    """Return the src directory path."""
    return SRC_PATH


@pytest.fixture
def tests_dir() -> Path:
    """Return the tests directory path."""
    return Path(__file__).parent


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def pdfs_dir(fixtures_dir) -> Path:
    """Return the PDF fixtures directory."""
    return fixtures_dir / "pdfs"


@pytest.fixture
def classeurs_dir(fixtures_dir) -> Path:
    """Return the classeurs fixtures directory."""
    return fixtures_dir / "classeurs"


# =============================================================================
# FIXTURES: Configuration files
# =============================================================================

@pytest.fixture
def simple_classeur_config(classeurs_dir) -> Path:
    """Create a simple classeur configuration file."""
    config_path = classeurs_dir / "simple" / "-classeur.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config_content = """{
        "description": "Classeur de test simple",
        "module": "simple",
        "pages": 1,
        "images": false,
        "identification": [
            "Facture",
            "TEST"
        ],
        "patterns": {
            "type": "(Facture\\s*(?:n°|numéro|N°)?\\s*(\\w+))",
            "reference": "(TEST-\\d{4})",
            "date": "(\\d{2}\\.\\d{2}\\.\\d{4})"
        },
        "transform": {
            "Facture": "FACT"
        },
        "nom_fichier": [
            ["values", "date"],
            ["values", "reference"],
            ["values", "type"]
        ]
    }"""
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)
    
    return config_path


@pytest.fixture
def facture_classeur_config(classeurs_dir) -> Path:
    """Create a facture-specific classeur configuration."""
    config_path = classeurs_dir / "factures" / "-classeur.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config_content = """{
        "description": "Factures clients",
        "module": "tolerant",
        "pages": 2,
        "images": false,
        "identification": [
            "FACTURE",
            "Client:",
            "Total TTC"
        ],
        "patterns": {
            "client": "Client:\\s*(\\w+)",
            "num_facture": "FACTURE\\s*(\\d{6})",
            "montant": "Total TTC:\\s*(\\d+\\.\\d{2})\\s*€",
            "timestamp": "Date:\\s*(\\d{2}/\\d{2}/\\d{4})"
        },
        "transform": {
            "Total TTC": "MONTANT"
        },
        "nom_fichier": [
            ["values", "timestamp"],
            ["values", "num_facture"],
            ["values", "client?"]
        ]
    }"""
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)
    
    return config_path


@pytest.fixture
def base_classeurs(classeurs_dir, simple_classeur_config, facture_classeur_config) -> Path:
    """Return the base classeurs directory with test configurations."""
    return classeurs_dir


# =============================================================================
# FIXTURES: Test PDF files
# =============================================================================

@pytest.fixture
def simple_pdf(pdfs_dir) -> Path:
    """Create a simple test PDF with text content."""
    from fpdf import FPDF
    
    pdf_path = pdfs_dir / "simple_test.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Content that matches simple_classeur_config patterns
    pdf.cell(200, 10, txt="Facture n° INV-2024", ln=1)
    pdf.cell(200, 10, txt="TEST-1234", ln=1)
    pdf.cell(200, 10, txt="Date: 15.05.2024", ln=1)
    pdf.cell(200, 10, txt="Montant: 100.00 €", ln=1)
    
    pdf.output(str(pdf_path))
    return pdf_path


@pytest.fixture
def facture_pdf(pdfs_dir) -> Path:
    """Create a facture test PDF with structured content."""
    from fpdf import FPDF
    
    pdf_path = pdfs_dir / "facture_test.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Content that matches facture_classeur_config patterns
    pdf.cell(200, 10, txt="FACTURE", ln=1)
    pdf.cell(200, 10, txt="Client: DUPONT", ln=1)
    pdf.cell(200, 10, txt="FACTURE 123456", ln=1)
    pdf.cell(200, 10, txt="Date: 20/05/2024", ln=1)
    pdf.cell(200, 10, txt="Total TTC: 250.50 €", ln=1)
    
    pdf.output(str(pdf_path))
    return pdf_path


@pytest.fixture
def unmatched_pdf(pdfs_dir) -> Path:
    """Create a PDF that won't match any classeur."""
    from fpdf import FPDF
    
    pdf_path = pdfs_dir / "unmatched.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Random document content", ln=1)
    pdf.cell(200, 10, txt="No matching patterns here", ln=1)
    
    pdf.output(str(pdf_path))
    return pdf_path


# =============================================================================
# FIXTURES: Mock modules
# =============================================================================

@pytest.fixture
def mock_swiftocr_path(tmp_path, monkeypatch):
    """Mock the SWIFTOCR path for testing."""
    mock_script = tmp_path / "mock_swiftocr"
    mock_script.write_text("""#!/bin/bash
echo "Extracted text from SwiftOCR"
exit 0
""")
    mock_script.chmod(0o755)
    
    monkeypatch.setenv("SWIFTOCR_PATH", str(mock_script))
    return str(mock_script)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, tmp_path):
    """Setup test environment variables."""
    # Mock SWIFTOCR path
    mock_swift = tmp_path / "swiftocr"
    mock_swift.write_text("""#!/bin/bash
echo "$@" | grep -o "[^ ]*\.pdf" | xargs -I {} echo "Extracted text from {}"
exit 0
""")
    mock_swift.chmod(0o755)
    monkeypatch.setattr("document.Document.SWIFTOCR", str(mock_swift))
    
    # Disable logging during tests
    monkeypatch.setattr("classeur.logger.disabled", True)
    monkeypatch.setattr("document.logger.disabled", True)


# =============================================================================
# FIXTURES: Import modules
# =============================================================================

@pytest.fixture
def classeur_module():
    """Import the classeur module."""
    from classeur import Classeur
    return Classeur


@pytest.fixture
def document_module():
    """Import the document module."""
    from document import Document
    return Document
