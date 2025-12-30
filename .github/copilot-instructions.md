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
# Auto-saves to crawls/{hostname}_{datetime}.json
python crawler.py https://example.com --pretty

# With real-time progress and summary
python crawler.py https://example.com --verbose --pretty

# Output to stdout
python crawler.py https://example.com --pretty --out -

# Full options
python crawler.py https://example.com \
  --max-pages 500 \
  --timeout 15 \
  --user-agent "MyBot/1.0" \
  --respect-robots \
  --out custom.json \
  --verbose \
  --pretty
```

## Verbose Output

When `--verbose` is enabled:
- Real-time progress: `[scanned/max] Visited: X | Discovered: Y | Queue: Z`
- Per-page details: status code, URL, new links found
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
- Add CLI args via `argparse` in `main()`
- Pass new options through to `crawl()` function
- Filter URLs in `normalize_url()` (e.g., new file extensions to skip)
- robots.txt logic uses simple prefix matching on paths
