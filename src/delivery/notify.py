"""Notification system — Slack, Discord, Feishu webhook integration."""

import json
import urllib.request
from abc import ABC, abstractmethod


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, title: str, body: str, metadata: dict | None = None) -> bool:
        ...


class SlackNotifier(NotificationChannel):
    def __init__(self, webhook_url: str):
        self._url = webhook_url

    def send(self, title: str, body: str, metadata: dict | None = None) -> bool:
        if not self._url:
            return False
        payload = {
            "text": f"*{title}*\n{body}",
            "mrkdwn": True,
        }
        return _post_json(self._url, payload)


class DiscordNotifier(NotificationChannel):
    def __init__(self, webhook_url: str):
        self._url = webhook_url

    def send(self, title: str, body: str, metadata: dict | None = None) -> bool:
        if not self._url:
            return False
        payload = {
            "content": f"**{title}**\n{body}",
        }
        return _post_json(self._url, payload)


class FeishuNotifier(NotificationChannel):
    def __init__(self, webhook_url: str):
        self._url = webhook_url

    def send(self, title: str, body: str, metadata: dict | None = None) -> bool:
        if not self._url:
            return False
        payload = {
            "msg_type": "text",
            "content": {"text": f"{title}\n{body}"},
        }
        return _post_json(self._url, payload)


class CompositeNotifier(NotificationChannel):
    def __init__(self, channels: list[NotificationChannel] | None = None):
        self._channels = channels or []

    def add(self, channel: NotificationChannel):
        self._channels.append(channel)

    def send(self, title: str, body: str, metadata: dict | None = None) -> bool:
        results = [ch.send(title, body, metadata) for ch in self._channels]
        return any(results)


def create_notifier(config: dict | None = None) -> CompositeNotifier:
    """Create notifier from configuration dict."""
    notifier = CompositeNotifier()
    if config is None:
        return notifier

    slack_url = config.get("slack_webhook", "")
    if slack_url:
        notifier.add(SlackNotifier(slack_url))

    discord_url = config.get("discord_webhook", "")
    if discord_url:
        notifier.add(DiscordNotifier(discord_url))

    feishu_url = config.get("feishu_webhook", "")
    if feishu_url:
        notifier.add(FeishuNotifier(feishu_url))

    return notifier


def create_risk_alert(pr_title: str, pr_url: str, risk_score: int,
                      findings_count: int) -> tuple[str, str]:
    """Generate high-risk notification title and body."""
    title = f"AI PR Review — HIGH RISK ({risk_score}/100)"
    body = (
        f"PR: {pr_title}\n"
        f"URL: {pr_url}\n"
        f"Risk Score: {risk_score}/100\n"
        f"Findings: {findings_count}\n"
        f"Action: Review before merging."
    )
    return title, body


def create_weekly_digest(total_reviews: int, total_findings: int,
                         avg_risk: float, top_issues: list[str]) -> tuple[str, str]:
    """Generate weekly digest notification."""
    title = "AI PR Review — Weekly Digest"
    body = (
        f"Reviews this week: {total_reviews}\n"
        f"Total findings: {total_findings}\n"
        f"Average risk score: {avg_risk:.0f}/100\n"
    )
    if top_issues:
        body += "\nTop repeated issues:\n"
        for issue in top_issues[:5]:
            body += f"  - {issue}\n"
    return title, body


def _post_json(url: str, payload: dict) -> bool:
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
        }, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False
