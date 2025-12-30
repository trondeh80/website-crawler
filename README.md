# Crawler

## Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Auto-saves to crawls/{hostname}_{datetime}.json
python crawler.py https://example.com --pretty

# With progress output
python crawler.py https://example.com --verbose --pretty
```

### Output to stdout:

```bash
python crawler.py https://example.com --pretty --out -
```

### Write to a specific file:

```bash
python crawler.py https://example.com --pretty --out custom_output.json
```


### Notes / practical upgrades you may want next

Concurrency (faster crawling) via asyncio + aiohttp, or switch to Scrapy for built-in concurrency/throttling.

Canonicalization rules (e.g., treating trailing slash variants as same page, stripping some tracking query params).

Sitemaps (seed queue from /sitemap.xml when present).

Persisting state (resume crawling).