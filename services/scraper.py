import trafilatura


async def scrape_page(url: str) -> str | None:
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        return None
    return trafilatura.extract(downloaded, include_comments=False, include_tables=False) or None
