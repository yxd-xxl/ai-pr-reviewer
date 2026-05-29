from dataclasses import dataclass
import re


@dataclass
class PRUrl:
    owner: str
    repo: str
    number: int


def parse_pr_url(url: str) -> PRUrl:
    m = re.search(
        r"github\.com/([^/]+)/([^/]+)/pull/(\d+)",
        url.rstrip("/").split("?")[0].split("#")[0],
    )
    if not m:
        raise ValueError(f"Invalid GitHub PR URL: {url}")
    return PRUrl(owner=m.group(1), repo=m.group(2), number=int(m.group(3)))
