# Copilot Instructions for crawler-tool

## Project Overview

Single-file Python web crawler that performs BFS traversal of local links from a start URL, outputting JSON results with page metadata (title, H1 tags, status codes, backlinks).

## Architecture

- **Single module**: All logic in `crawler.py` (~300 lines)
- **Data flow**: URL queue (BFS) → fetch → parse HTML → extract links → repeat
- **Output**: JSON array of `PageResult` objects with backlink tracking

### Key Components

| Function | Purpose |
|----------|---------|
| `crawl()` | Main orchestrator: queue management, state tracking, robots.txt |
| `normalize_url()` | URL canonicalization (fragments, ports, case, file extensions) |
| `extract_links()` | BeautifulSoup link extraction from `<a href>` |
| `parse_title_and_h1()` | HTML metadata extraction |
| `is_local()` | Same-origin check (scheme + netloc) |

## Dependencies

```bash
pip install requests beautifulsoup4 lxml
```

- `requests` - HTTP client with session management
- `beautifulsoup4` + `lxml` - HTML parsing (lxml parser for speed)

## Usage Patterns

```bash
# Basic crawl
python crawler.py https://example.com --pretty

# Full options
python crawler.py https://example.com \
  --max-pages 500 \
  --timeout 15 \
  --user-agent "MyBot/1.0" \
  --respect-robots \
  --out results.json \
  --verbose
```

## Code Conventions

- **Type hints**: All functions use type annotations (`List`, `Optional`, `Tuple` from typing)
- **Dataclasses**: `PageResult` for structured output with `asdict()` serialization
- **URL handling**: Always normalize via `normalize_url()` before comparison/storage
- **Error handling**: `requests.RequestException` caught; failures recorded with `status_code=None`

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
- Add CLI args via `argparse` in `main()`
- Pass new options through to `crawl()` function
- Filter URLs in `normalize_url()` (e.g., new file extensions to skip)
- robots.txt logic uses simple prefix matching on paths
