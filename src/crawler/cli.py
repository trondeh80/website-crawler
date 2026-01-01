"""
Command-line interface for the crawler.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from crawler.core import crawl, CrawlStats


def print_summary(stats: CrawlStats) -> None:
    """Print crawl summary to stderr."""
    sys.stderr.write("=" * 50 + "\n")
    sys.stderr.write("CRAWL SUMMARY\n")
    sys.stderr.write("=" * 50 + "\n\n")
    
    sys.stderr.write(f"Total pages crawled:    {stats.pages_crawled}\n")
    sys.stderr.write(f"Pages without title:    {stats.pages_without_title}\n")
    sys.stderr.write(f"Pages without H1:       {stats.pages_without_h1}\n\n")
    
    if stats.error_counts:
        sys.stderr.write("Errors by type:\n")
        for error_type, count in sorted(stats.error_counts.items()):
            label = "Connection errors" if error_type == "connection_error" else f"HTTP {error_type}"
            sys.stderr.write(f"  {label}: {count}\n")
    else:
        sys.stderr.write("No errors encountered.\n")
    
    sys.stderr.write("\n")


def generate_output_path(start_url: str) -> Path:
    """Generate output path: crawls/{hostname}_{datetime}.json"""
    parsed = urlparse(start_url)
    hostname = parsed.hostname or "unknown"
    # Sanitize hostname for filename (replace dots with underscores)
    hostname_safe = hostname.replace(".", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    crawls_dir = Path("crawls")
    crawls_dir.mkdir(exist_ok=True)
    
    return crawls_dir / f"{hostname_safe}_{timestamp}.json"


def main() -> int:
    """Main entry point for the crawler CLI."""
    parser = argparse.ArgumentParser(
        description="Crawl all local links starting from a URL and output JSON results."
    )
    parser.add_argument("start_url", help="Start URL (e.g. https://example.com)")
    parser.add_argument("--max-pages", type=int, default=500, help="Maximum pages to scan (default: 500)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout in seconds (default: 15)")
    parser.add_argument("--user-agent", default="LocalLinkCrawler/1.0", help="User-Agent header")
    parser.add_argument("--respect-robots", action="store_true", help="Try to respect robots.txt Disallow rules")
    parser.add_argument(
        "--path-prefix",
        help="Limit crawling to URLs whose path starts with this prefix (e.g., '/products')"
    )
    parser.add_argument("--out", help="Output file path, or '-' for stdout (default: auto-generated in crawls/)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--verbose", action="store_true", help="Show progress and summary")
    args = parser.parse_args()

    results, stats = crawl(
        start_url=args.start_url,
        max_pages=args.max_pages,
        timeout_s=args.timeout,
        user_agent=args.user_agent,
        respect_robots=args.respect_robots,
        verbose=args.verbose,
        path_prefix=args.path_prefix,
    )

    # Print summary if verbose
    if args.verbose:
        print_summary(stats)

    # Output JSON
    payload = [asdict(r) for r in results]
    json_text = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)

    if args.out == "-":
        print(json_text)
    else:
        # Auto-generate path if not specified
        output_path = Path(args.out) if args.out else generate_output_path(args.start_url)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_text, encoding="utf-8")
        if args.verbose:
            sys.stderr.write(f"Results written to: {output_path}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
