# Copilot Instructions for website-crawler

## Project Overview

Python web crawler that performs BFS traversal of local links from a start URL, outputting JSON results with page metadata (title, H1 tags, status codes, backlinks). Supports path prefix filtering to limit crawling to specific sections of a website.

## Project Structure

```
website-crawler/
├── src/
│   └── crawler/
│       ├── __init__.py      # Package exports (crawl, CrawlStats, PageResult)
│       ├── __main__.py      # Entry point for python -m crawler
│       ├── cli.py           # CLI argument parsing and output handling
│       └── core.py          # Core crawling logic and data structures
├── crawls/                  # Default output directory for results
├── pyproject.toml           # Project configuration and dependencies
└── README.md
```

## Architecture

- **Package layout**: `src/crawler/` with separated concerns
- **Data flow**: URL queue (BFS) → fetch → parse HTML → extract links → filter by path prefix → repeat
- **Output**: JSON array of `PageResult` objects with backlink tracking

### Key Components

| Module | Purpose |
|--------|---------|
| `core.py` | Main crawling logic, URL handling, HTML parsing |
| `cli.py` | CLI interface, output formatting, file handling |
| `__main__.py` | Module entry point for `python -m crawler` |

### Key Functions in `core.py`

| Function | Purpose |
|----------|---------|
| `crawl()` | Main orchestrator: queue management, state tracking, robots.txt |
| `normalize_url()` | URL canonicalization (fragments, ports, case, file extensions) |
| `matches_path_prefix()` | Path prefix filtering for `--path-prefix` option |
| `extract_links()` | BeautifulSoup link extraction from `<a href>` |
| `parse_metadata()` | HTML metadata extraction (title, H1 tags) |
| `is_local()` | Same-origin check (scheme + netloc) |

### Key Functions in `cli.py`

| Function | Purpose |
|----------|---------|
| `main()` | CLI entry point with argparse |
| `print_summary()` | Verbose mode summary output |
| `generate_output_path()` | Auto-generate output filename |

## Dependencies

Defined in `pyproject.toml`:

```toml
dependencies = [
    "requests>=2.28.0",
    "beautifulsoup4>=4.11.0",
    "lxml>=4.9.0",
]
```

## Installation

```bash
# Development install
pip install -e .

# With dev dependencies
pip install -e ".[dev]"
```

## Usage Patterns

```bash
# Basic crawl (auto-saves to crawls/{hostname}_{datetime}.json)
crawler https://example.com --pretty

# Limit to specific path prefix
crawler https://example.com/docs --path-prefix /docs --pretty

# With real-time progress and summary
crawler https://example.com --verbose --pretty

# Output to stdout
crawler https://example.com --pretty --out -

# Full options
crawler https://example.com \
  --max-pages 500 \
  --timeout 15 \
  --user-agent "MyBot/1.0" \
  --respect-robots \
  --path-prefix /blog \
  --out custom.json \
  --verbose \
  --pretty

# Run as module
python -m crawler https://example.com --pretty
```

## Path Prefix Filtering

The `--path-prefix` option limits crawling to URLs whose path starts with the given prefix:

```bash
# Only crawl pages under /rettskilder
crawler https://lovdata.no/rettskilder --path-prefix /rettskilder

# Only crawl documentation
crawler https://docs.example.com/api --path-prefix /api
```

The start URL must match the path prefix, otherwise an error is raised.

## Verbose Output

When `--verbose` is enabled:
- Real-time progress: `[scanned/max] Visited: X | Discovered: Y | Queue: Z`
- Per-page details: status code, URL, new links found
- Path prefix filter displayed (if set)
- Final summary with statistics

## Code Conventions

- **Type hints**: All functions use type annotations (`List`, `Optional`, `Tuple` from typing)
- **Dataclasses with slots**: `PageResult` and `CrawlStats` use `@dataclass(slots=True)` for memory efficiency
- **URL handling**: Always normalize via `normalize_url()` before comparison/storage
- **Error handling**: `requests.RequestException` caught; failures recorded with `status_code=None`
- **Performance**: `SoupStrainer` for link extraction, `frozenset` for O(1) extension lookups, `defaultdict` for inlinks

## Output Schema

```json
{
  "url": "https://example.com/page",
  "scanned_at": "2025-01-01T12:00:00+00:00",
  "status_code": 200,
  "title": "Page Title",
  "h1_present": true,
  "h1_contents": ["Main Heading"],
  "linked_from": ["https://example.com/"]
}
```

## Extension Points

When adding features, follow existing patterns:
- Add CLI args via `argparse` in `cli.py`'s `main()`
- Pass new options through to `crawl()` function in `core.py`
- Filter URLs in `normalize_url()` or add new filter functions like `matches_path_prefix()`
- robots.txt logic uses simple prefix matching on paths

## Testing

```bash
pytest                    # Run tests
mypy src/crawler          # Type checking
ruff check src/crawler    # Linting
```
