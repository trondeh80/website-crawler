#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, urldefrag

import requests
from bs4 import BeautifulSoup


@dataclass
class PageResult:
    url: str
    scanned_at: Optional[str] = None
    status_code: Optional[int] = None
    title: Optional[str] = None
    h1_present: Optional[bool] = None
    h1_contents: Optional[List[str]] = None
    linked_from: List[str] = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_url(url: str, base: str) -> Optional[str]:
    """
    - Join relative URLs against base
    - Drop fragments (#...)
    - Normalize scheme/host case
    - Remove default ports (:80, :443)
    - Keep querystrings (they matter for uniqueness)
    """
    if not url:
        return None

    joined = urljoin(base, url)
    joined, _frag = urldefrag(joined)

    p = urlparse(joined)

    if p.scheme not in ("http", "https"):
        return None

    # Basic "ignore" common non-page targets
    lowered_path = (p.path or "").lower()
    if any(lowered_path.endswith(ext) for ext in (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        ".pdf", ".zip", ".rar", ".7z",
        ".mp4", ".mp3", ".wav", ".webm",
        ".css", ".js", ".map", ".ico",
        ".woff", ".woff2", ".ttf", ".eot",
    )):
        return None

    netloc = p.netloc.lower()

    # Strip default ports
    hostname = p.hostname.lower() if p.hostname else ""
    port = p.port
    if (p.scheme == "http" and port == 80) or (p.scheme == "https" and port == 443):
        netloc = hostname
    elif port:
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    # Normalize empty path to "/"
    path = p.path or "/"

    normalized = urlunparse((p.scheme.lower(), netloc, path, p.params, p.query, ""))
    return normalized


def is_local(url: str, start_parsed: Tuple[str, str]) -> bool:
    """Local == same scheme and netloc as the start URL."""
    p = urlparse(url)
    return (p.scheme, p.netloc) == start_parsed


def extract_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if href:
            links.append(href)
    return links


def parse_title_and_h1(html: str) -> Tuple[Optional[str], bool, List[str]]:
    soup = BeautifulSoup(html, "lxml")

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip() or None

    h1_tags = soup.find_all("h1")
    h1_texts: List[str] = []
    for h in h1_tags:
        text = h.get_text(separator=" ", strip=True)
        if text:
            h1_texts.append(text)

    return title, len(h1_tags) > 0, h1_texts


def crawl(
    start_url: str,
    max_pages: int,
    timeout_s: float,
    user_agent: str,
    respect_robots: bool,
    verbose: bool,
) -> List[PageResult]:
    # Normalize start URL
    start_url_n = normalize_url(start_url, start_url)
    if not start_url_n:
        raise ValueError(f"Invalid start URL: {start_url}")

    start_parsed = urlparse(start_url_n)
    start_key = (start_parsed.scheme, start_parsed.netloc)

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    # Crawl state
    results: Dict[str, PageResult] = {}
    inlinks: Dict[str, Set[str]] = {}
    discovered: Set[str] = set()
    scanned: Set[str] = set()

    q: Deque[str] = deque()
    q.append(start_url_n)
    discovered.add(start_url_n)
    results[start_url_n] = PageResult(url=start_url_n, linked_from=[])

    # robots.txt support (optional, basic)
    robots_disallow: Set[str] = set()
    if respect_robots:
        try:
            robots_url = urlunparse((start_key[0], start_key[1], "/robots.txt", "", "", ""))
            r = session.get(robots_url, timeout=timeout_s, allow_redirects=True)
            if r.status_code == 200 and "text" in (r.headers.get("content-type", "").lower()):
                lines = r.text.splitlines()
                ua_star = False
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.lower().startswith("user-agent:"):
                        ua_star = line.split(":", 1)[1].strip() == "*"
                    elif ua_star and line.lower().startswith("disallow:"):
                        path = line.split(":", 1)[1].strip()
                        if path:
                            robots_disallow.add(path)
        except Exception:
            # If robots fetch fails, proceed anyway (since it's optional)
            pass

    def blocked_by_robots(url: str) -> bool:
        if not respect_robots:
            return False
        p = urlparse(url)
        for dis in robots_disallow:
            if p.path.startswith(dis):
                return True
        return False

    pages_scanned = 0

    while q and pages_scanned < max_pages:
        url = q.popleft()
        if url in scanned:
            continue
        if blocked_by_robots(url):
            if verbose:
                print(f"[robots] Skipping {url}", file=sys.stderr)
            scanned.add(url)
            # Still keep a result entry for completeness
            results.setdefault(url, PageResult(url=url, linked_from=[]))
            results[url].scanned_at = utc_now_iso()
            results[url].status_code = None
            results[url].title = None
            results[url].h1_present = None
            results[url].h1_contents = None
            pages_scanned += 1
            continue

        if verbose:
            print(f"[scan] {url}", file=sys.stderr)

        res = results.setdefault(url, PageResult(url=url, linked_from=[]))
        res.scanned_at = utc_now_iso()

        try:
            resp = session.get(url, timeout=timeout_s, allow_redirects=True)
            res.status_code = resp.status_code
            scanned.add(url)
            pages_scanned += 1

            ctype = (resp.headers.get("content-type") or "").lower()
            if "text/html" not in ctype:
                # Not HTML: keep status, but no title/h1 parsing
                res.title = None
                res.h1_present = False
                res.h1_contents = []
                continue

            html = resp.text
            title, h1_present, h1_texts = parse_title_and_h1(html)
            res.title = title
            res.h1_present = h1_present
            res.h1_contents = h1_texts

            # Discover outgoing links
            for raw_href in extract_links(html, base_url=url):
                target = normalize_url(raw_href, base=url)
                if not target:
                    continue
                if not is_local(target, start_key):
                    continue

                # Register inlink: url -> target
                inlinks.setdefault(target, set()).add(url)

                # Ensure result placeholder exists
                results.setdefault(target, PageResult(url=target, linked_from=[]))

                if target not in discovered:
                    discovered.add(target)
                    q.append(target)

        except requests.RequestException as e:
            if verbose:
                print(f"[error] {url}: {e}", file=sys.stderr)
            res.status_code = None
            res.title = None
            res.h1_present = None
            res.h1_contents = None
            scanned.add(url)
            pages_scanned += 1

    # Finalize linked_from lists (sorted for stable output)
    for url, pr in results.items():
        pr.linked_from = sorted(inlinks.get(url, set()))

    # Return as a JSON array (stable ordering)
    ordered_urls = sorted(results.keys())
    return [results[u] for u in ordered_urls]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crawl all local links starting from a URL and output JSON results."
    )
    parser.add_argument("start_url", help="Start URL (e.g. https://example.com)")
    parser.add_argument("--max-pages", type=int, default=500, help="Maximum pages to scan (default: 500)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout in seconds (default: 15)")
    parser.add_argument("--user-agent", default="LocalLinkCrawler/1.0", help="User-Agent header")
    parser.add_argument("--respect-robots", action="store_true", help="Try to respect robots.txt Disallow rules")
    parser.add_argument("--out", default="-", help="Output file path, or '-' for stdout (default: '-')")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--verbose", action="store_true", help="Log progress to stderr")
    args = parser.parse_args()

    results = crawl(
        start_url=args.start_url,
        max_pages=args.max_pages,
        timeout_s=args.timeout,
        user_agent=args.user_agent,
        respect_robots=args.respect_robots,
        verbose=args.verbose,
    )

    payload = [asdict(r) for r in results]
    json_text = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)

    if args.out == "-" or args.out.strip() == "":
        print(json_text)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(json_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
