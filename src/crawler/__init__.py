"""
Web crawler that performs BFS traversal of local links from a start URL.
Outputs JSON results with page metadata (title, H1 tags, status codes, backlinks).
"""
from crawler.core import crawl, CrawlStats, PageResult

__version__ = "1.0.0"
__all__ = ["crawl", "CrawlStats", "PageResult"]
