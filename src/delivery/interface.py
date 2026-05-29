from abc import ABC, abstractmethod

from src.core.types import ReviewResult, PullRequest


class Delivery(ABC):
    """Interface for delivering review results to a target (GitHub, Markdown, etc.)."""

    @abstractmethod
    def deliver(self, result: ReviewResult, pr: PullRequest) -> list[str]:
        """Deliver review findings. Returns list of actions taken."""
        ...
