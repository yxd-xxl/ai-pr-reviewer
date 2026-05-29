import tempfile
from pathlib import Path
import pytest
from src.core.config import ReviewConfig, DeliveryConfig, load_config, DEFAULT_CONFIG


class TestReviewConfig:
    def test_defaults(self):
        cfg = ReviewConfig()
        assert cfg.min_confidence == 0.65
        assert cfg.max_inline_comments == 10
        assert "bug" in cfg.categories
        assert "security" in cfg.categories

    def test_validation_rejects_invalid_confidence(self):
        with pytest.raises(ValueError):
            ReviewConfig(min_confidence=1.5)

    def test_validation_rejects_negative_max_comments(self):
        with pytest.raises(ValueError):
            ReviewConfig(max_inline_comments=-1)


class TestLoadConfig:
    def test_loads_valid_yaml(self):
        yaml = """
review:
  min_confidence: 0.8
  max_inline_comments: 5
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml)
        try:
            cfg = load_config(f.name)
            assert cfg.min_confidence == 0.8
            assert cfg.max_inline_comments == 5
        finally:
            Path(f.name).unlink()

    def test_missing_file_returns_default(self):
        cfg = load_config("/nonexistent/path.yml")
        assert cfg.min_confidence == DEFAULT_CONFIG.min_confidence

    def test_invalid_yaml_returns_default(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(":: not yaml ::")
        try:
            cfg = load_config(f.name)
            assert cfg == DEFAULT_CONFIG
        finally:
            Path(f.name).unlink()

    def test_loads_conventions(self):
        yaml = """
conventions:
  - .claude/CLAUDE.md
  - CONTRIBUTING.md
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml)
        try:
            cfg = load_config(f.name)
            assert ".claude/CLAUDE.md" in cfg.conventions
            assert "CONTRIBUTING.md" in cfg.conventions
        finally:
            Path(f.name).unlink()

    def test_delivery_defaults(self):
        cfg = ReviewConfig()
        assert cfg.delivery.mode == "dry-run"
        assert cfg.delivery.inline_comments is True
        assert cfg.delivery.summary_comment is True
