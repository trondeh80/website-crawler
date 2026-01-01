"""
Core crawling logic and data structures.
"""
from __future__ import annotations

import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, urldefrag

import requests
from bs4 import BeautifulSoup, SoupStrainer

# Pre-defined file extensions to skip (frozen set for O(1) lookup)
SKIP_EXTENSIONS: frozenset[str] = frozenset((
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".pdf", ".zip", ".rar", ".7z",
    ".mp4", ".mp3", ".wav", ".webm",
    ".css", ".js", ".map", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
))

# SoupStrainer to parse only <a> tags (faster link extraction)
LINK_STRAINER = SoupStrainer("a", href=True)


@dataclass(slots=True)
class PageResult:
    """Result data for a single crawled page."""
    url: str
    scanned_at: Optional[str] = None
    status_code: Optional[int] = None
    title: Optional[str] = None
    h1_present: Optional[bool] = None
    h1_contents: Optional[List[str]] = None
    linked_from: List[str] = field(default_factory=list)


@dataclass(slots=True)
class CrawlStats:
    """Statistics collected during crawl for summary output."""
    pages_crawled: int = 0
    pages_without_title: int = 0
    pages_without_h1: int = 0
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def record_error(self, status_code: Optional[int]) -> None:
        """Record an error by status code category."""
        if status_code is None:
            self.error_counts["connection_error"] += 1
        elif status_code >= 400:
            self.error_counts[str(status_code)] += 1
    
    def record_page(self, title: Optional[str], h1_present: Optional[bool]) -> None:
        """Record page metadata statistics."""
        if not title:
            self.pages_without_title += 1
        if not h1_present:
            self.pages_without_h1 += 1


def utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_url(url: str, base: str) -> Optional[str]:
    """
    Normalize URL for deduplication and comparison.
    
    - Joins relative URLs against base
    - Drops fragments (#...)
    - Normalizes scheme/host case
    - Removes default ports (:80, :443)
    - Keeps querystrings (they matter for uniqueness)
    """
    if not url:
        return None

    joined, _ = urldefrag(urljoin(base, url))
    parsed = urlparse(joined)

    if parsed.scheme not in ("http", "https"):
        return None

    # Skip non-page file extensions (O(1) lookup with frozenset)
    path_lower = (parsed.path or "").lower()
    if any(path_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
        return None

    # Normalize hostname and port
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    
    if (parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443):
        netloc = hostname
    elif port:
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    return urlunparse((
        parsed.scheme.lower(),
        netloc,
        parsed.path or "/",
        parsed.params,
        parsed.query,
        ""  # No fragment
    ))


def is_local(url: str, start_origin: Tuple[str, str]) -> bool:
    """Check if URL has same scheme and netloc as start URL."""
    parsed = urlparse(url)
    return (parsed.scheme, parsed.netloc) == start_origin


def matches_path_prefix(url: str, path_prefix: Optional[str]) -> bool:
    """Check if URL path starts with the given prefix."""
    if path_prefix is None:
        return True
    parsed = urlparse(url)
    return parsed.path.startswith(path_prefix)


def extract_links(html: str) -> List[str]:
    """Extract all href values from <a> tags using optimized parsing."""
    soup = BeautifulSoup(html, "lxml", parse_only=LINK_STRAINER)
    return [a["href"] for a in soup if a.get("href")]


def parse_metadata(html: str) -> Tuple[Optional[str], bool, List[str]]:
    """Extract title and H1 tags from HTML."""
    soup = BeautifulSoup(html, "lxml")

    # Extract title
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip() or None

    # Extract H1 contents
    h1_tags = soup.find_all("h1")
    h1_texts = [
        text for h in h1_tags 
        if (text := h.get_text(separator=" ", strip=True))
    ]

    return title, bool(h1_tags), h1_texts


def print_progress(
    scanned: int,
    discovered: int,
    queue_size: int,
    current_url: str,
    max_pages: int,
) -> None:
    """Print real-time progress to stderr."""
    # Clear line and print progress
    progress = f"\r\033[K[{scanned}/{max_pages}] Visited: {scanned} | Discovered: {discovered} | Queue: {queue_size}"
    sys.stderr.write(progress)
    sys.stderr.flush()


def print_scan_line(url: str, status: Optional[int], new_links: int) -> None:
    """Print single scan result line."""
    status_str = str(status) if status else "ERR"
    sys.stderr.write(f"\n  → {status_str} {url} (+{new_links} links)")
    sys.stderr.flush()


def crawl(
    start_url: str,
    max_pages: int,
    timeout_s: float,
    user_agent: str,
    respect_robots: bool,
    verbose: bool,
    path_prefix: Optional[str] = None,
) -> Tuple[List[PageResult], CrawlStats]:
    """
    Crawl all local links starting from a URL using BFS traversal.
    
    Args:
        start_url: The URL to start crawling from.
        max_pages: Maximum number of pages to crawl.
        timeout_s: HTTP request timeout in seconds.
        user_agent: User-Agent header to use for requests.
        respect_robots: Whether to respect robots.txt rules.
        verbose: Whether to print progress information.
        path_prefix: Optional path prefix to limit crawling (e.g., "/rettskilder").
                     Only URLs whose path starts with this prefix will be crawled.
    
    Returns:
        Tuple of (results list, crawl statistics).
    """
    # Normalize and validate start URL
    start_url_normalized = normalize_url(start_url, start_url)
    if not start_url_normalized:
        raise ValueError(f"Invalid start URL: {start_url}")

    # Validate that start URL matches path prefix if specified
    if path_prefix and not matches_path_prefix(start_url_normalized, path_prefix):
        raise ValueError(
            f"Start URL path does not match --path-prefix '{path_prefix}'. "
            f"Start URL should begin with the path prefix."
        )

    start_parsed = urlparse(start_url_normalized)
    start_origin = (start_parsed.scheme, start_parsed.netloc)

    # Initialize HTTP session
    session = requests.Session()
    session.headers["User-Agent"] = user_agent

    # Crawl state
    results: Dict[str, PageResult] = {}
    inlinks: Dict[str, Set[str]] = defaultdict(set)
    discovered: Set[str] = {start_url_normalized}
    scanned: Set[str] = set()
    queue: Deque[str] = deque([start_url_normalized])
    stats = CrawlStats()

    # Initialize start URL result
    results[start_url_normalized] = PageResult(url=start_url_normalized)

    # Load robots.txt rules if requested
    robots_disallow = _load_robots_rules(session, start_origin, timeout_s) if respect_robots else set()

    if verbose:
        sys.stderr.write(f"Starting crawl from: {start_url_normalized}\n")
        sys.stderr.write(f"Max pages: {max_pages}\n")
        if path_prefix:
            sys.stderr.write(f"Path prefix filter: {path_prefix}\n")
        sys.stderr.write("\n")

    while queue and stats.pages_crawled < max_pages:
        url = queue.popleft()
        
        if url in scanned:
            continue

        # Check robots.txt
        if _is_blocked_by_robots(url, robots_disallow):
            if verbose:
                sys.stderr.write(f"\n  ⊘ ROBOTS {url}")
            scanned.add(url)
            _mark_skipped(results, url)
            stats.pages_crawled += 1
            continue

        if verbose:
            print_progress(stats.pages_crawled, len(discovered), len(queue), url, max_pages)

        # Fetch and process page
        result = results.setdefault(url, PageResult(url=url))
        result.scanned_at = utc_now_iso()
        new_links_count = 0

        try:
            resp = session.get(url, timeout=timeout_s, allow_redirects=True)
            result.status_code = resp.status_code
            scanned.add(url)
            stats.pages_crawled += 1

            # Track errors
            if resp.status_code >= 400:
                stats.record_error(resp.status_code)

            # Only parse HTML content
            content_type = (resp.headers.get("content-type") or "").lower()
            if "text/html" not in content_type:
                result.title = None
                result.h1_present = False
                result.h1_contents = []
                stats.record_page(None, False)
                if verbose:
                    print_scan_line(url, resp.status_code, 0)
                continue

            html = resp.text
            title, h1_present, h1_texts = parse_metadata(html)
            result.title = title
            result.h1_present = h1_present
            result.h1_contents = h1_texts
            stats.record_page(title, h1_present)

            # Discover and queue new links
            for href in extract_links(html):
                target = normalize_url(href, base=url)
                if not target or not is_local(target, start_origin):
                    continue
                
                # Apply path prefix filter
                if not matches_path_prefix(target, path_prefix):
                    continue

                inlinks[target].add(url)
                results.setdefault(target, PageResult(url=target))

                if target not in discovered:
                    discovered.add(target)
                    queue.append(target)
                    new_links_count += 1

            if verbose:
                print_scan_line(url, resp.status_code, new_links_count)

        except requests.RequestException as e:
            if verbose:
                sys.stderr.write(f"\n  ✗ ERROR {url}: {e}")
            result.status_code = None
            result.title = None
            result.h1_present = None
            result.h1_contents = None
            stats.record_error(None)
            scanned.add(url)
            stats.pages_crawled += 1

    if verbose:
        sys.stderr.write("\n\n")

    # Finalize backlinks
    for url, page_result in results.items():
        page_result.linked_from = sorted(inlinks.get(url, set()))

    # Return sorted results
    return [results[u] for u in sorted(results.keys())], stats


def _load_robots_rules(
    session: requests.Session,
    origin: Tuple[str, str],
    timeout: float,
) -> Set[str]:
    """Load disallow rules from robots.txt."""
    disallow_rules: Set[str] = set()
    try:
        robots_url = urlunparse((origin[0], origin[1], "/robots.txt", "", "", ""))
        resp = session.get(robots_url, timeout=timeout, allow_redirects=True)
        
        if resp.status_code != 200:
            return disallow_rules
        if "text" not in (resp.headers.get("content-type") or "").lower():
            return disallow_rules

        ua_star = False
        for line in resp.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            lower_line = line.lower()
            if lower_line.startswith("user-agent:"):
                ua_star = line.split(":", 1)[1].strip() == "*"
            elif ua_star and lower_line.startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    disallow_rules.add(path)
    except requests.RequestException:
        pass  # Proceed without robots.txt on error
    
    return disallow_rules


def _is_blocked_by_robots(url: str, disallow_rules: Set[str]) -> bool:
    """Check if URL path matches any disallow rule."""
    if not disallow_rules:
        return False
    path = urlparse(url).path
    return any(path.startswith(rule) for rule in disallow_rules)


def _mark_skipped(results: Dict[str, PageResult], url: str) -> None:
    """Mark a URL as skipped (robots.txt blocked)."""
    result = results.setdefault(url, PageResult(url=url))
    result.scanned_at = utc_now_iso()
    result.status_code = None
    result.title = None
    result.h1_present = None
    result.h1_contents = None
