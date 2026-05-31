"""TEST FILE — contains intentional performance issues for AI detection demo.
This file is NOT part of the production system. Used only for evaluation testing."""

import sqlite3
import time


# PERF: N+1 query — query inside loop
def get_users_with_posts(user_ids: list[int]) -> list[dict]:
    conn = sqlite3.connect("app.db")
    results = []
    for uid in user_ids:
        user = conn.execute(f"SELECT * FROM users WHERE id = {uid}").fetchone()  # BUG: N+1
        posts = conn.execute(f"SELECT * FROM posts WHERE user_id = {uid}").fetchall()  # BUG: N+1
        results.append({"user": user, "posts": posts})
    return results


# PERF: Unnecessary list copy in loop
def filter_valid(items: list[str]) -> list[str]:
    result = []
    for item in items:
        cleaned = [c for c in item if c.isalnum()]  # PERF: list comp per item
        if len(cleaned) > 0:
            result.append("".join(cleaned))
    return result


# PERF: O(n^2) duplicate check
def has_duplicates(items: list[int]) -> bool:
    for i in range(len(items)):
        for j in range(len(items)):  # PERF: O(n^2), should use set
            if i != j and items[i] == items[j]:
                return True
    return False


# PERF: Repeated computation in loop
def compute_stats(numbers: list[float]) -> dict:
    return {
        "sum": sum(numbers),
        "avg": sum(numbers) / len(numbers) if numbers else 0,  # PERF: sum() called twice
        "max": max(numbers),
        "min": min(numbers),
    }


# PERF: Memory leak — unbounded cache
_cache: dict[str, any] = {}
def cached_query(key: str) -> any:
    if key in _cache:
        return _cache[key]
    result = f"expensive_query_for_{key}"
    _cache[key] = result  # PERF: unbounded growth, no eviction
    return result


# PERF: Blocking I/O in sync function
def fetch_all_urls(urls: list[str]) -> list[str]:
    import urllib.request
    results = []
    for url in urls:
        resp = urllib.request.urlopen(url, timeout=30)  # PERF: sequential, should be parallel
        results.append(resp.read().decode())
    return results


# PERF: Large allocation in hot path
def build_report(items: list[dict]) -> str:
    lines = []
    for item in items:
        line = f"{item['id']}: {item['name']} — {item['description']}"
        lines.append(line)
    return "\n".join(lines)  # PERF: string join OK, but items could be large
