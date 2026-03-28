"""
QYNE v1 — Website Crawler Pipeline.

Deep crawls an entire website and converts every page to clean markdown.
Output is structured for AI consumption (RAG, agents) and human reading.

Use cases:
- Crawl competitor documentation → knowledge base
- Crawl your own site → verify content, find gaps
- Crawl reference material → index for agents to cite
- Crawl news/blog → extract articles for content research

Pipeline:
  Discover pages (BFS) → Fetch each → Convert to markdown → Chunk → Store in Directus → Index in LanceDB

Output per page:
{
    "url": "https://example.com/page",
    "title": "Page Title",
    "content_markdown": "# Title\n\nClean markdown content...",
    "content_chunks": [
        {"text": "chunk 1...", "tokens": 450, "index": 0},
        {"text": "chunk 2...", "tokens": 380, "index": 1}
    ],
    "metadata": {
        "word_count": 1200,
        "links_found": 15,
        "images_found": 3,
        "crawl_depth": 2,
        "source_site": "example.com"
    },
    "status": "indexed"
}
"""

import hashlib
import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Stage 1: DISCOVER (BFS crawl to find all pages)
# ---------------------------------------------------------------------------


@task(retries=2, retry_delay_seconds=30)
async def discover_pages(
    start_url: str,
    max_pages: int = 50,
    max_depth: int = 3,
    include_paths: list[str] | None = None,
    exclude_paths: list[str] | None = None,
) -> list[dict]:
    """Deep crawl a site using BFS to discover all pages."""
    logger = get_run_logger()
    logger.info(f"Discovering pages from {start_url} (max={max_pages}, depth={max_depth})")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
        )

        async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
            result = await crawler.arun(url=start_url, config=config)

        if not result.success:
            logger.warning(f"Initial crawl failed: {start_url}")
            return [{"url": start_url, "depth": 0}]

        # Extract internal links from the page
        domain = urlparse(start_url).netloc
        discovered = [{"url": start_url, "depth": 0}]
        seen_urls = {start_url}

        # Parse links from the result
        if result.links:
            for link_group in [result.links.get("internal", []), result.links.get("external", [])]:
                for link in link_group:
                    href = link.get("href", "") if isinstance(link, dict) else str(link)
                    if not href or not href.startswith("http"):
                        continue
                    if urlparse(href).netloc != domain:
                        continue
                    # Clean URL (remove fragments and query params)
                    clean_url = href.split("#")[0].split("?")[0].rstrip("/")
                    if clean_url in seen_urls:
                        continue
                    # Apply path filters
                    path = urlparse(clean_url).path
                    if include_paths and not any(p in path for p in include_paths):
                        continue
                    if exclude_paths and any(p in path for p in exclude_paths):
                        continue
                    seen_urls.add(clean_url)
                    discovered.append({"url": clean_url, "depth": 1})

                    if len(discovered) >= max_pages:
                        break

        logger.info(f"Discovered {len(discovered)} pages on {domain}")
        return discovered[:max_pages]

    except Exception as e:
        logger.error(f"Discovery error: {e}")
        return [{"url": start_url, "depth": 0}]


# ---------------------------------------------------------------------------
# Stage 2: FETCH + CONVERT TO MARKDOWN
# ---------------------------------------------------------------------------


@task(retries=2, retry_delay_seconds=15)
async def fetch_as_markdown(url: str) -> dict | None:
    """Fetch a page and convert to clean markdown."""
    logger = get_run_logger()

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
        )

        async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
            result = await crawler.arun(url=url, config=config)

        if not result.success:
            return None

        # Use fit_markdown if available (filtered content), fallback to markdown
        markdown = getattr(result, "fit_markdown", None) or result.markdown or ""

        if not markdown or len(markdown) < 50:
            return None

        # Extract title from markdown or metadata
        title = ""
        if result.metadata and result.metadata.get("title"):
            title = result.metadata["title"]
        elif markdown.startswith("# "):
            title = markdown.split("\n")[0].lstrip("# ").strip()

        # Count content metrics
        word_count = len(markdown.split())
        links_found = len(result.links.get("internal", [])) + len(result.links.get("external", [])) if result.links else 0
        images_found = len(result.media.get("images", [])) if result.media else 0

        logger.info(f"Fetched: {url} ({word_count} words)")

        return {
            "url": url,
            "title": title or urlparse(url).path.strip("/").replace("/", " > ") or "Home",
            "content_markdown": markdown,
            "word_count": word_count,
            "links_found": links_found,
            "images_found": images_found,
        }

    except Exception as e:
        logger.warning(f"Fetch failed: {url} → {e}")
        return None


# ---------------------------------------------------------------------------
# Stage 3: CHUNK (split for RAG / token limits)
# ---------------------------------------------------------------------------


@task
def chunk_markdown(page: dict, max_chunk_tokens: int = 500) -> dict:
    """Split markdown into chunks optimized for RAG retrieval."""
    markdown = page["content_markdown"]

    # Split by headers first, then by paragraphs
    sections = re.split(r"\n(?=#{1,3} )", markdown)

    chunks = []
    current_chunk = ""
    current_tokens = 0

    for section in sections:
        section_tokens = len(section.split()) * 1.3  # Rough token estimate

        if current_tokens + section_tokens > max_chunk_tokens and current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "tokens": int(current_tokens),
                "index": len(chunks),
                "source_url": page["url"],
            })
            current_chunk = ""
            current_tokens = 0

        current_chunk += section + "\n\n"
        current_tokens += section_tokens

    # Last chunk
    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "tokens": int(current_tokens),
            "index": len(chunks),
            "source_url": page["url"],
        })

    page["content_chunks"] = chunks
    return page


# ---------------------------------------------------------------------------
# Stage 4: DEDUP
# ---------------------------------------------------------------------------


@task(retries=1)
def is_page_duplicate(url: str) -> bool:
    """Check if URL already exists in documents collection."""
    if not DIRECTUS_TOKEN:
        return False
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/documents?filter[source_file][_eq]={url}&fields=id&limit=1",
        headers=HEADERS,
        timeout=10,
    )
    return len(resp.json().get("data", [])) > 0 if resp.is_success else False


# ---------------------------------------------------------------------------
# Stage 5: STORE IN DIRECTUS
# ---------------------------------------------------------------------------


@task(retries=2, retry_delay_seconds=10)
def store_page(page: dict, site_name: str) -> int | None:
    """Store crawled page in Directus documents collection."""
    if not DIRECTUS_TOKEN:
        return None

    resp = httpx.post(
        f"{DIRECTUS_URL}/items/documents",
        json={
            "title": page["title"][:500],
            "content": page["content_markdown"][:50000],
            "source_file": page["url"],
            "status": "crawled",
        },
        headers=HEADERS,
        timeout=10,
    )
    if resp.is_success:
        return resp.json()["data"]["id"]
    return None


# ---------------------------------------------------------------------------
# Stage 6: INDEX IN LANCEDB (for RAG)
# ---------------------------------------------------------------------------


@task(retries=1)
def index_chunks(page: dict) -> int:
    """Index markdown chunks in LanceDB for agent retrieval."""
    logger = get_run_logger()
    indexed = 0

    try:
        from agno.knowledge.knowledge import Knowledge
        from agno.knowledge.embedder.voyageai import VoyageAIEmbedder
        from agno.vectordb.lancedb import LanceDb, SearchType

        embedder = VoyageAIEmbedder(id="voyage-3-lite", dimensions=512)
        vector_db = LanceDb(
            uri="/app/data/lancedb",
            table_name="nexus_knowledge",
            search_type=SearchType.hybrid,
            embedder=embedder,
        )
        kb = Knowledge(vector_db=vector_db)

        for chunk in page.get("content_chunks", []):
            kb.insert(
                content=chunk["text"],
                metadata={
                    "title": page["title"],
                    "source": page["url"],
                    "chunk_index": chunk["index"],
                },
            )
            indexed += 1

        logger.info(f"Indexed {indexed} chunks from {page['url']}")
    except Exception as e:
        logger.error(f"Indexing error: {e}")

    return indexed


# ---------------------------------------------------------------------------
# MAIN FLOW
# ---------------------------------------------------------------------------


@flow(name="Website Crawler", log_prints=True)
async def website_crawler(
    url: str,
    max_pages: int = 50,
    max_depth: int = 3,
    include_paths: list[str] | None = None,
    exclude_paths: list[str] | None = None,
    index_in_knowledge: bool = True,
    max_chunk_tokens: int = 500,
) -> dict:
    """Crawl an entire website, convert to markdown, store and index for AI.

    Args:
        url: Starting URL to crawl.
        max_pages: Maximum pages to crawl.
        max_depth: Maximum link depth from start URL.
        include_paths: Only crawl URLs containing these path segments.
        exclude_paths: Skip URLs containing these path segments.
        index_in_knowledge: Whether to index chunks in LanceDB for RAG.
        max_chunk_tokens: Maximum tokens per chunk for RAG.

    Example:
        website_crawler(
            url="https://docs.example.com",
            max_pages=100,
            include_paths=["/docs/", "/guide/"],
            exclude_paths=["/blog/", "/changelog/"],
        )
    """
    domain = urlparse(url).netloc
    stats = {
        "site": domain,
        "pages_discovered": 0,
        "pages_fetched": 0,
        "pages_stored": 0,
        "chunks_indexed": 0,
        "duplicates": 0,
        "errors": 0,
        "total_words": 0,
    }

    # Stage 1: Discover pages
    pages = await discover_pages(url, max_pages, max_depth, include_paths, exclude_paths)
    stats["pages_discovered"] = len(pages)

    for page_info in pages:
        page_url = page_info["url"]

        # Stage 4: Dedup
        if is_page_duplicate(page_url):
            stats["duplicates"] += 1
            continue

        # Stage 2: Fetch + convert to markdown
        page = await fetch_as_markdown(page_url)
        if not page:
            stats["errors"] += 1
            continue
        stats["pages_fetched"] += 1
        stats["total_words"] += page["word_count"]

        # Stage 3: Chunk for RAG
        page = chunk_markdown(page, max_chunk_tokens)

        # Stage 5: Store in Directus
        doc_id = store_page(page, domain)
        if doc_id:
            stats["pages_stored"] += 1

        # Stage 6: Index in LanceDB
        if index_in_knowledge:
            indexed = index_chunks(page)
            stats["chunks_indexed"] += indexed

    # Log run summary
    if DIRECTUS_TOKEN:
        httpx.post(
            f"{DIRECTUS_URL}/items/events",
            json={"type": "website_crawl", "payload": stats},
            headers=HEADERS,
            timeout=10,
        )

    return stats


if __name__ == "__main__":
    import asyncio
    asyncio.run(website_crawler(url="https://docs.agno.com", max_pages=20))
