from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DeliveryConfig:
    mode: str = "dry-run"           # dry-run | publish
    inline_comments: bool = True
    summary_comment: bool = True

    def __post_init__(self):
        if self.mode not in ("dry-run", "publish"):
            raise ValueError(f"delivery.mode must be 'dry-run' or 'publish', got '{self.mode}'")


@dataclass
class ReviewConfig:
    mode: str = "balanced"  # fast | balanced | deep
    permission: str = "review-only"  # review-only | selective-fix | auto-fix
    min_confidence: float = 0.65
    max_inline_comments: int = 10
    categories: list[str] = field(default_factory=lambda: [
        "security", "bug", "performance", "architecture", "style",
    ])
    auto_fix_categories: list[str] = field(default_factory=lambda: [
        "security", "bug",
    ])
    conventions: list[str] = field(default_factory=lambda: [
        ".claude/CLAUDE.md",
    ])
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)

    def __post_init__(self):
        if self.mode not in ("fast", "balanced", "deep"):
            raise ValueError(f"review.mode must be fast/balanced/deep, got '{self.mode}'")
        if getattr(self, 'permission', 'review-only') not in ('review-only', 'selective-fix', 'auto-fix'):
            raise ValueError(f"permission must be review-only/selective-fix/auto-fix, got '{self.permission}'")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError(
                f"min_confidence must be 0.0-1.0, got {self.min_confidence}"
            )
        if self.max_inline_comments < 0:
            raise ValueError(
                f"max_inline_comments must be >= 0, got {self.max_inline_comments}"
            )
        if isinstance(self.delivery, dict):
            self.delivery = DeliveryConfig(**self.delivery)


DEFAULT_CONFIG = ReviewConfig()


def load_config(path: str | None = None) -> ReviewConfig:
    """Load config from YAML file. Falls back to defaults if file not found."""
    if path is None:
        path = ".ai-pr-reviewer.yml"

    cfg_path = Path(path)
    if not cfg_path.exists():
        return DEFAULT_CONFIG

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return DEFAULT_CONFIG

    review_data = data.get("review", {})
    delivery_data = data.get("delivery", {})

    return ReviewConfig(
        mode=review_data.get("mode", DEFAULT_CONFIG.mode),
        permission=review_data.get("permission", DEFAULT_CONFIG.permission),
        min_confidence=review_data.get("min_confidence", DEFAULT_CONFIG.min_confidence),
        auto_fix_categories=review_data.get("auto_fix_categories", DEFAULT_CONFIG.auto_fix_categories),
        max_inline_comments=review_data.get("max_inline_comments", DEFAULT_CONFIG.max_inline_comments),
        categories=review_data.get("categories", DEFAULT_CONFIG.categories),
        conventions=data.get("conventions", DEFAULT_CONFIG.conventions),
        delivery=DeliveryConfig(
            mode=delivery_data.get("mode", DEFAULT_CONFIG.delivery.mode),
            inline_comments=delivery_data.get("inline_comments", DEFAULT_CONFIG.delivery.inline_comments),
            summary_comment=delivery_data.get("summary_comment", DEFAULT_CONFIG.delivery.summary_comment),
        ),
    )
