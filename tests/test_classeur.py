"""Tests for classeur.py module."""
import pytest
import json

# Import modules
from src.classeur import Classeur


class TestClasseurInit:
    """Tests for Classeur initialization."""

    def test_classeur_new_with_nonexistent_dir(self, tmp_path):
        """Test __new__ with a non-existent directory."""
        with pytest.raises(SystemExit) as exc_info:
            Classeur(str(tmp_path / "nonexistent"), False)
        assert exc_info.value.code == 1

    def test_classeur_new_with_file_instead_of_dir(self, tmp_path):
        """Test __new__ with a file instead of directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        with pytest.raises(SystemExit) as exc_info:
            Classeur(str(test_file), False)
        assert exc_info.value.code == 1

    def test_classeur_new_with_valid_dir_no_config(self, tmp_path):
        """Test __new__ with valid directory but no config file."""
        test_dir = tmp_path / "test_classeur"
        test_dir.mkdir()
        
        result = Classeur(str(test_dir), False)
        assert result is None

    def test_classeur_new_with_config_file(self, tmp_path):
        """Test __new__ with directory containing config file."""
        test_dir = tmp_path / "test_classeur"
        test_dir.mkdir()
        config_file = test_dir / "-classeur.json"
        
        config = {
            "description": "Test classeur",
            "pages": 1,
            "identification": ["Test"],
            "patterns": {},
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        result = Classeur(str(test_dir), False)
        assert isinstance(result, Classeur)
        assert result.chemin_classeur == test_dir
        assert result.chemin_config == config_file

    def test_classeur_new_with_base_option(self, tmp_path):
        """Test __new__ with base option to find multiple classeurs."""
        # Create multiple classeur directories
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        
        for i in range(3):
            classeur_dir = base_dir / f"classeur_{i}"
            classeur_dir.mkdir()
            config_file = classeur_dir / "-classeur.json"
            config = {
                "description": f"Classeur {i}",
                "pages": 1,
                "identification": [f"Pattern{i}"],
                "patterns": {},
                "nom_fichier": []
            }
            with open(config_file, "w") as f:
                json.dump(config, f)
        
        result = Classeur(str(base_dir), True)
        assert result is True
        assert len(Classeur.LISTE_CLASSEUR) == 3
        assert len(Classeur.LISTE_CONFIG) == 3


class TestClasseurLoadConfig:
    """Tests for configuration loading."""

    def test_load_config_valid(self, tmp_path):
        """Test loading a valid configuration file."""
        test_dir = tmp_path / "test_classeur"
        test_dir.mkdir()
        config_file = test_dir / "-classeur.json"
        
        config = {
            "description": "Test classeur",
            "pages": 2,
            "identification": ["Facture", "TEST"],
            "patterns": {"ref": "(TEST-\\d+)"},
            "nom_fichier": [["identification", 0]]
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        classeur = Classeur(str(test_dir), False)
        loaded_config = classeur.load_config()
        
        assert loaded_config == config
        assert classeur.config == config

    def test_load_config_missing_file(self, tmp_path):
        """Test loading config from missing file."""
        test_dir = tmp_path / "test_classeur"
        test_dir.mkdir()
        
        classeur = Classeur(str(test_dir), False)

        assert classeur is None

    def test_load_config_invalid_json(self, tmp_path):
        """Test loading invalid JSON config."""
        test_dir = tmp_path / "test_classeur"
        test_dir.mkdir()
        config_file = test_dir / "-classeur.json"
        config_file.write_text("{invalid json}")
        
        with pytest.raises(SystemExit) as exc_info:
            classeur = Classeur(str(test_dir), False)
            classeur.load_config()
        assert exc_info.value.code == 1


class TestClasseurProperties:
    """Tests for Classeur properties."""

    def test_classeur_description(self, tmp_path):
        """Test accessing description from config."""
        test_dir = tmp_path / "test_classeur"
        test_dir.mkdir()
        config_file = test_dir / "-classeur.json"
        
        config = {
            "description": "My Test Classeur",
            "pages": 1,
            "identification": ["Test"],
            "patterns": {},
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        classeur = Classeur(str(test_dir), False)
        assert classeur.config["description"] == "My Test Classeur"

    def test_classeur_chemin_court(self, tmp_path):
        """Test chemin_court property."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        
        classeur_dir = base_dir / "sub" / "classeur"
        classeur_dir.mkdir(parents=True)
        config_file = classeur_dir / "-classeur.json"
        
        config = {
            "description": "Test",
            "pages": 1,
            "identification": ["Test"],
            "patterns": {},
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Set base
        Classeur.NOM_BASE = base_dir
        
        classeur = Classeur(str(classeur_dir), False)
        # chemin_court should be relative to base
        assert "base" not in str(classeur.chemin_court) or str(classeur.chemin_court).startswith("sub")


class TestClasseurCaching:
    """Tests for configuration caching."""

    def test_config_caching(self, tmp_path):
        """Test that configuration is cached between instances."""
        test_dir = tmp_path / "test_classeur"
        test_dir.mkdir()
        config_file = test_dir / "-classeur.json"
        
        config = {
            "description": "Cached Config",
            "pages": 1,
            "identification": ["Test"],
            "patterns": {},
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Create first instance
        classeur1 = Classeur(str(test_dir), False)
        assert Classeur.SAUVE_CLASSEUR == test_dir
        assert Classeur.SAUVE_CONFIG == config
        
        # Create second instance - should use cache
        classeur2 = Classeur(str(test_dir), False)
        assert classeur2.config == config
        assert classeur2.config is Classeur.SAUVE_CONFIG


class TestClasseurAffiche:
    """Tests for affiche method."""

    def test_affiche_with_valid_config(self, tmp_path, capsys):
        """Test affiche method with valid config."""
        test_dir = tmp_path / "test_classeur"
        test_dir.mkdir()
        config_file = test_dir / "-classeur.json"
        
        config = {
            "description": "Test Display",
            "pages": 1,
            "identification": ["Facture", "TEST"],
            "patterns": {"ref": "(TEST-\\d+)"},
            "nom_fichier": [["identification", 0]]
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        classeur = Classeur(str(test_dir), False)
        classeur.affiche()
        
        captured = capsys.readouterr()
        # assert "Test Display" in captured.out
        assert "✅ Identification" in captured.out
        assert "✅ Patterns" in captured.out

    def test_affiche_with_missing_identification(self, tmp_path, capsys):
        """Test affiche method with missing identification."""
        test_dir = tmp_path / "test_classeur"
        test_dir.mkdir()
        config_file = test_dir / "-classeur.json"
        
        config = {
            "description": "Test Display",
            "pages": 1,
            "patterns": {"ref": "(TEST-\\d+)"},
            "nom_fichier": []
        }
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        classeur = Classeur(str(test_dir), False)
        classeur.affiche()
        
        captured = capsys.readouterr()
        assert "❌ Identification" in captured.out
