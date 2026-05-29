from dataclasses import dataclass
import re


@dataclass
class PRUrl:
    owner: str
    repo: str
    number: int
    platform: str = "github"


def parse_pr_url(url: str) -> PRUrl:
    url_clean = url.rstrip("/").split("?")[0].split("#")[0]
    m = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", url_clean)
    if m:
        return PRUrl(owner=m.group(1), repo=m.group(2),
                     number=int(m.group(3)), platform="github")
    m = re.search(r"gitlab\.com/([^/]+)/([^/]+)/-/merge_requests/(\d+)", url_clean)
    if m:
        return PRUrl(owner=m.group(1), repo=m.group(2),
                     number=int(m.group(3)), platform="gitlab")
    raise ValueError(f"Invalid PR/MR URL: {url}")
