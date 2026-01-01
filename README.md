# Website Crawler

A Python web crawler that performs BFS traversal of local links from a start URL, outputting JSON results with page metadata (title, H1 tags, status codes, backlinks).

## Features

- **BFS traversal** of all local links starting from a seed URL
- **Path prefix filtering** to limit crawling to specific sections of a website
- **Robots.txt support** for respectful crawling
- **Rich metadata extraction**: title, H1 tags, status codes, backlinks
- **Real-time progress** with verbose mode
- **JSON output** with automatic file naming

## Installation

### Using pip (recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/website-crawler.git
cd website-crawler

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .
```

### For development

```bash
pip install -e ".[dev]"
```

## Usage

### Basic usage

```bash
# Using the installed command
crawler https://example.com --pretty

# Or run as a module
python -m crawler https://example.com --pretty
```

### Limit crawling to a specific path

Use `--path-prefix` to crawl only URLs whose path starts with a specific prefix:

```bash
# Only crawl pages under /products
crawler https://example.com/products --path-prefix /products --pretty

# Only crawl the blog section
crawler https://example.com/blog --path-prefix /blog --verbose
```

### With real-time progress and summary

```bash
crawler https://example.com --verbose --pretty
```

### Output to stdout

```bash
crawler https://example.com --pretty --out -
```

### Write to a specific file

```bash
crawler https://example.com --pretty --out custom_output.json
```

### Full options

```bash
crawler https://example.com \
  --max-pages 500 \
  --timeout 15 \
  --user-agent "MyBot/1.0" \
  --respect-robots \
  --path-prefix /docs \
  --out custom.json \
  --verbose \
  --pretty
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `start_url` | (required) | The URL to start crawling from |
| `--max-pages` | 500 | Maximum number of pages to scan |
| `--timeout` | 15.0 | Request timeout in seconds |
| `--user-agent` | LocalLinkCrawler/1.0 | User-Agent header for requests |
| `--respect-robots` | false | Respect robots.txt Disallow rules |
| `--path-prefix` | (none) | Only crawl URLs whose path starts with this prefix |
| `--out` | auto | Output file path, or `-` for stdout |
| `--pretty` | false | Pretty-print JSON output |
| `--verbose` | false | Show real-time progress and summary |

## Output Format

Results are saved as a JSON array of page objects:

```json
[
  {
    "url": "https://example.com/page",
    "scanned_at": "2025-01-01T12:00:00+00:00",
    "status_code": 200,
    "title": "Page Title",
    "h1_present": true,
    "h1_contents": ["Main Heading"],
    "linked_from": ["https://example.com/"]
  }
]
```

By default, results are saved to `crawls/{hostname}_{datetime}.json`.

## Project Structure

```
website-crawler/
├── src/
│   └── crawler/
│       ├── __init__.py      # Package exports
│       ├── __main__.py      # Entry point for python -m crawler
│       ├── cli.py           # Command-line interface
│       └── core.py          # Core crawling logic
├── crawls/                  # Default output directory
├── pyproject.toml           # Project configuration
└── README.md
```

## Development

### Running tests

```bash
pytest
```

### Type checking

```bash
mypy src/crawler
```

### Linting

```bash
ruff check src/crawler
```

## Notes / Practical Upgrades

- **Concurrency**: Use `asyncio` + `aiohttp` for faster crawling, or switch to Scrapy for built-in concurrency/throttling
- **Canonicalization**: Treat trailing slash variants as same page, strip tracking query params
- **Sitemaps**: Seed queue from `/sitemap.xml` when present
- **State persistence**: Resume interrupted crawls

## License

MIT