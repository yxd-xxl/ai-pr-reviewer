"""Tests for notification system."""

from unittest.mock import patch, MagicMock
from src.delivery.notify import (
    SlackNotifier, DiscordNotifier, FeishuNotifier, CompositeNotifier,
    create_notifier, create_risk_alert, create_weekly_digest,
)


class TestSlackNotifier:
    def test_sends_when_url_set(self):
        with patch("src.delivery.notify._post_json", return_value=True) as mock_post:
            notifier = SlackNotifier("https://hooks.slack.com/test")
            assert notifier.send("Alert", "Test body") is True
            mock_post.assert_called_once()

    def test_skips_when_url_empty(self):
        notifier = SlackNotifier("")
        assert notifier.send("Alert", "Body") is False


class TestDiscordNotifier:
    def test_sends_when_url_set(self):
        with patch("src.delivery.notify._post_json", return_value=True) as mock_post:
            notifier = DiscordNotifier("https://discord.com/api/webhooks/test")
            assert notifier.send("Alert", "Test") is True


class TestCompositeNotifier:
    def test_broadcasts_to_all(self):
        with patch("src.delivery.notify._post_json", return_value=True):
            c = CompositeNotifier([
                SlackNotifier("https://hooks.slack.com/a"),
                DiscordNotifier("https://discord.com/api/webhooks/b"),
            ])
            assert c.send("Alert", "Body") is True


class TestCreateNotifier:
    def test_empty_config(self):
        n = create_notifier({})
        assert isinstance(n, CompositeNotifier)
        assert len(n._channels) == 0

    def test_with_slack(self):
        n = create_notifier({"slack_webhook": "https://hooks.slack.com/x"})
        assert len(n._channels) == 1


class TestRiskAlert:
    def test_format(self):
        title, body = create_risk_alert("Fix auth", "https://github.com/o/r/pull/1", 85, 12)
        assert "85" in title
        assert "Fix auth" in body


class TestWeeklyDigest:
    def test_format(self):
        title, body = create_weekly_digest(20, 45, 32.5, ["Null check", "SQL injection"])
        assert "20" in body
        assert "Null check" in body
