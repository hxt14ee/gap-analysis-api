"""
Scraper service: extracts main text content from a URL using trafilatura.
"""
import trafilatura


async def scrape_page(url: str) -> str | None:
    """
    Download and extract the main article text from *url*.

    Returns the plain-text content, or None if extraction fails.
    """
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        return None

    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )
    return text or None
