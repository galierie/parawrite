# pip install requests beautifulsoup4 lxml

import json
import os
import random
import re
import time
import html
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Callable, Literal

# Types
Site = Literal['Rappler', 'ABSCBN', 'GMA']

# Site Configuration

@dataclass
class ApiSectionConfig:
    base_url: str
    fixed_params: dict
    section_id: str
    article_filter: Callable[[dict], bool]
    url_field: str
    url_prefix: str
    limit: int = 100
    title_field: str | None = "title"
    body_field: str | None = None

@dataclass
class SiteConfig:
    name: str
    url_source: Literal["sitemap", "rss", "id_range", "category_pages", "api"]
    title_selector: str
    body_selector: str
    urls_file: str
    articles_file: str
    scraped_urls_file: str

    # Used when url_source == "sitemap"
    sitemap_urls: list[str] | None = None
    url_filter: Callable[[str], bool] | None = None

    # Used when url_source == "rss"
    rss_feeds: list[str] | None = None

    # Used when url_source == "id_range"
    # GMA article URLs follow: /news/{category}/{id}/{slug}/story/
    id_range_base_url: str | None = None
    id_range_start: int | None = None
    id_range_end: int | None = None

    # Used when url_source == "category_pages"
    category_page_configs: list["CategoryPageConfig"] | None = None
    
    # Used when url_source == "api"
    # For sites that expose a JSON REST API for article listings
    api_configs: list["ApiSectionConfig"] | None = None

@dataclass
class CategoryPageConfig:
    page_url_template: str
    article_link_selector: str
    start_page: int = 1
    max_pages: int = 300

def _rappler_filter(url: str) -> bool:
    return (
        "rappler-prod-01" not in url
        and url[-4] != "."
        and ".jpg" not in url.lower()
        and ".png" not in url.lower()
        and ".gif" not in url.lower()
        and "go.rappler" not in url
        and "r3-assets" not in url
        and "r5-assets" not in url
        and "static.rappler.com" not in url
        and url != "https://www.rappler.com/latest/"
    )

def _abscbn_filter(url: str) -> bool:
    return (
        "www.abs-cbn.com" in url
        and ".jpg" not in url.lower()
        and ".png" not in url.lower()
        and ".gif" not in url.lower()
        and "/video" not in url
        and "/photo" not in url
        and "/schedule" not in url
        and url.count("/") >= 5  # real articles have at least 5 slashes in path
    )

# Sitemaps
def _rappler_sitemaps() -> list[str]:
    # Rappler's sitemaps are numbered post-sitemap.xml through post-sitemap380.xml
    urls = ["https://www.rappler.com/post-sitemap.xml"]
    for i in range(2, 381):
        urls.append(f"https://www.rappler.com/post-sitemap{i}.xml")
    return urls

# Excluded money, sports, lifestyle, entertainment
GMA_RSS_FEEDS = [
    "https://data.gmanetwork.com/gno/rss/news/feed.xml",
    "https://data.gmanetwork.com/gno/rss/news/nation/feed.xml",
    "https://data.gmanetwork.com/gno/rss/news/world/feed.xml",
    "https://data.gmanetwork.com/gno/rss/news/specialreports/feed.xml",
]

# Site configs
SITE_CONFIGS: dict[str, SiteConfig] = {
    "Rappler": SiteConfig(
        name="Rappler",
        url_source="sitemap",
        sitemap_urls=_rappler_sitemaps(),
        url_filter=_rappler_filter,
        title_selector=".post-single__title",
        body_selector=".post-single__content p",
        urls_file="rappler_urls.txt",
        articles_file="rappler_articles.jsonl",
        scraped_urls_file="rappler_scraped_urls.txt",
    ),
    "ABSCBN": SiteConfig(
        name="ABSCBN",
        url_source="api",
        api_configs=[
            ApiSectionConfig(
                base_url="https://od2-content-api.abs-cbn.com/prod/latest",
                fixed_params={"brand": "OD", "partner": "imp-01"},
                section_id="nation",
                article_filter=lambda item: item.get("profile") == "Article",
                url_field="slugline_url",
                url_prefix="https://www.abs-cbn.com/",
                limit=100,
            ),
            ApiSectionConfig(
                base_url="https://od2-content-api.abs-cbn.com/prod/latest",
                fixed_params={"brand": "OD", "partner": "imp-01"},
                section_id="world",
                article_filter=lambda item: item.get("profile") == "Article",
                url_field="slugline_url",
                url_prefix="https://www.abs-cbn.com/",
                limit=100,
            ),
        ],
        title_selector="h1.MuiTypography-root, h1.news-title",
        body_selector="#bodyTopPart p, .article-content p, .story-body p",
        urls_file="abscbn_urls.txt",
        articles_file="abscbn_articles.jsonl",
        scraped_urls_file="abscbn_scraped_urls.txt",
    ),
    "GMA": SiteConfig(
        name="GMA",
        url_source="id_range",
        rss_feeds=GMA_RSS_FEEDS,
        id_range_base_url="https://www.gmanetwork.com/news/story/{id}",
        id_range_start=700_000,
        id_range_end=951_500,           # TODO: update as new articles are published
        title_selector="h1.story_links",
        body_selector=".story_main p, .article-body p",
        urls_file="gma_urls.txt",
        articles_file="gma_articles.jsonl",
        scraped_urls_file="gma_scraped_urls.txt",
    ),
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/117.0"
    )
}

# Common boilerplate strings to filter out of article bodies
UI_BLACKLIST = [
    "ABS-CBN Corporation", 
    "All Rights Reserved", 
    "NPC Seal of Registration",
    "News Entertainment Lifestyle",
    "Word of the Day Lotto",
    "Corporate Investors Governance",
    "Advertise with Us",
    "Privacy Policy AI Policy",
    "Terms of Service"
]

# TODO: For now, this is focused on Rappler only
def _fetch_urls_from_sitemap(sitemap_url: str, url_filter: Callable[[str], bool], retries: int = 4, base_delay: float = 5.0) -> list[str]:
    # Download one sitemap XML and return all article URLs that pass the filter
    print(f"Fetching sitemap: {sitemap_url}")
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(sitemap_url, headers=DEFAULT_HEADERS, timeout=30)
            response.raise_for_status()
            break
        except requests.exceptions.Timeout:
            wait = base_delay * (2 ** (attempt - 1))  # 5s, 10s, 20s, 40s
            print(f"  Timeout (attempt {attempt}/{retries}) — retrying in {wait:.0f}s ...")
            time.sleep(wait)
        except requests.RequestException as e:
            print(f"WARNING: Could not fetch sitemap — {e}")
            return []
    else:
        print(f"WARNING: Gave up after {retries} attempts — skipping")
        return []

    soup = BeautifulSoup(response.content, "lxml-xml")
    urls = [loc.text.strip() for loc in soup.find_all("loc") if url_filter(loc.text.strip())]
    print(f"{len(urls)} article URLs found")
    return urls

def _fetch_urls_from_rss(rss_feeds: list[str]) -> list[str]:
    # Pull article URLs from a list of RSS feeds.
    # Only gets most recent articles per sectioni, so must use alongside id_range for historical articles
    all_urls: list[str] = []
    for feed_url in rss_feeds:
        print(f"Fetching RSS feed: {feed_url}")
        try:
            response = requests.get(feed_url, headers=DEFAULT_HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"WARNING: Could not fetch feed — {e}")
            continue

        soup = BeautifulSoup(response.content, "lxml-xml")
        links = [item.find("link") for item in soup.find_all("item")]
        urls = [link.text.strip() for link in links if link and link.text.strip()]
        print(f"{len(urls)} article URLs found")
        all_urls.extend(urls)

    return all_urls

def _fetch_urls_from_category_pages(config: SiteConfig) -> list[str]:
    # Crawl paginated section/category listing pages and collect article links
    assert config.category_page_configs and config.url_filter

    all_urls: list[str] = []
    seen: set[str] = set()

    for cat in config.category_page_configs:
        print(f"Category: {cat.page_url_template.format(page='N')}")
        consecutive_empty = 0

        for page_num in range(cat.start_page, cat.start_page + cat.max_pages):
            url = cat.page_url_template.format(page=page_num)
            try:
                resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"WARNING: page {page_num} failed — {e}")
                break

            soup = BeautifulSoup(resp.content, "lxml")
            anchors = soup.select(cat.article_link_selector)

            new_urls = []
            for a in anchors:
                href = a.get("href", "").strip()
                # Make relative URLs absolute
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                if href and config.url_filter(href) and href not in seen:
                    seen.add(href)
                    new_urls.append(href)

            if not new_urls:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    # Two pages in a row with nothing new — assume end of archive
                    print(f"No new links on page {page_num} — stopping this category")
                    break
            else:
                consecutive_empty = 0
                print(f"Page {page_num}: {len(new_urls)} new URLs (total so far: {len(seen):,})")
                all_urls.extend(new_urls)

            time.sleep(0.5)  # polite pause between listing-page requests

    return all_urls

def _generate_gma_id_range_urls(config: SiteConfig) -> list[str]:
    # Build full list of candidate GMA short URLs from the configured ID range.
    assert config.id_range_base_url and config.id_range_start and config.id_range_end
    return [
        config.id_range_base_url.format(id=i)
        for i in range(config.id_range_start, config.id_range_end + 1)
    ]

def _fetch_urls_from_api(config: SiteConfig, max_pages: int | None = None) -> list[str | dict]:
    # Collect article URLs by paging through a JSON REST API.
    assert config.api_configs
    all_items: list[str | dict] = []
    seen: set[str] = set()

    for api_cfg in config.api_configs:
        print(f"Section: {api_cfg.section_id}")
        offset = 0
        while True:
            params = {
                **api_cfg.fixed_params,
                "sectionId": api_cfg.section_id,
                "limit": api_cfg.limit,
                "offset": offset,
            }
            try:
                resp = requests.get(api_cfg.base_url, params=params, headers=DEFAULT_HEADERS, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except (requests.RequestException, ValueError) as e:
                print(f"WARNING: API request failed (offset={offset}) — {e}")
                break

            items = data.get("listItem", [])
            if not items:
                print(f"No more items at offset={offset} — section complete")
                break

            new_items = []
            for item in items:
                if not api_cfg.article_filter(item):
                    continue
                path = item.get(api_cfg.url_field, "").strip()
                if not path:
                    continue
                full_url = api_cfg.url_prefix.rstrip("/") + "/" + path.lstrip("/")

                if full_url not in seen:
                    seen.add(full_url)
                    
                    # If body_field is set, skip the HTML fetch entirely and assemble the dict here
                    if api_cfg.body_field:
                        raw_title = item.get(api_cfg.title_field or "title", "")
                        raw_body = item.get(api_cfg.body_field, "")
                        
                        # Use BeautifulSoup to strip any potential HTML tags returned in the API string
                        clean_title = BeautifulSoup(raw_title, "lxml").get_text(separator=" ", strip=True) if raw_title else ""
                        clean_body = BeautifulSoup(raw_body, "lxml").get_text(separator=" ", strip=True) if raw_body else ""

                        # Fix encoding issues for API responses
                        clean_title = html.unescape(clean_title)
                        clean_body = html.unescape(clean_body)
                        
                        new_items.append({
                            "url": full_url,
                            "title": clean_title,
                            "body": clean_body
                        })
                    else:
                        new_items.append(full_url)

            all_items.extend(new_items)
            print(f"offset={offset:>6}: {len(new_items)} new articles (section total: {len(all_items):,})")

            if len(items) < api_cfg.limit:
                print(f"Received {len(items)} < {api_cfg.limit} — end of section")
                break

            offset += api_cfg.limit
            if max_pages is not None and (offset // api_cfg.limit) >= max_pages:
                print(f"Reached max_pages={max_pages} — stopping early")
                break
            time.sleep(0.3)  # polite pause between API pages

    return all_items


def collect_all_urls(config: SiteConfig, max_discovery: int | None = None) -> list[str | dict]:
    # Return every candidate article URL for this site.
    if max_discovery is None and os.path.exists(config.urls_file):
        print(f"[{config.name}] Loading cached URLs from '{config.urls_file}'")
        cached_items = []
        with open(config.urls_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Load pre-scraped API dicts if they exist, otherwise load URL strings
                if line.startswith("{"):
                    cached_items.append(json.loads(line))
                else:
                    cached_items.append(line)
                    
        print(f"[{config.name}] {len(cached_items):,} URLs loaded from cache")
        return cached_items

    raw: list[str | dict] = []
    if max_discovery is not None:
        print(f"[{config.name}] Discovery capped at {max_discovery} (test mode — results will NOT be cached)")

    if config.url_source == "sitemap":
        assert config.sitemap_urls and config.url_filter
        sitemaps = config.sitemap_urls[:max_discovery] if max_discovery else config.sitemap_urls
        print(f"[{config.name}] Crawling {len(sitemaps)} of {len(config.sitemap_urls)} sitemap(s) ...")
        for i, sitemap_url in enumerate(sitemaps):
            raw.extend(_fetch_urls_from_sitemap(sitemap_url, config.url_filter))
            if i < len(sitemaps) - 1:
                time.sleep(2.0)  # pause between sitemaps to avoid throttling

    elif config.url_source == "rss":
        assert config.rss_feeds
        print(f"[{config.name}] Fetching {len(config.rss_feeds)} RSS feed(s) ...")
        raw = _fetch_urls_from_rss(config.rss_feeds)

    elif config.url_source == "category_pages":
        assert config.category_page_configs
        print(f"[{config.name}] Crawling {len(config.category_page_configs)} category section(s) ...")
        raw = _fetch_urls_from_category_pages(config)

    elif config.url_source == "api":
        assert config.api_configs
        print(f"[{config.name}] Fetching URLs from {len(config.api_configs)} API section(s) ...")
        raw = _fetch_urls_from_api(config, max_pages=max_discovery)

    elif config.url_source == "id_range":
        print(f"[{config.name}] Generating ID-range URLs ({config.id_range_start:,} → {config.id_range_end:,}) ...")
        raw = _generate_gma_id_range_urls(config)
        if max_discovery:
            raw = random.sample(raw, min(max_discovery, len(raw)))
        print(f"{len(raw):,} candidate URLs generated")

    else:
        raise ValueError(f"Unknown url_source: {config.url_source!r}")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str | dict] = []
    for u in raw:
        url_str = u["url"] if isinstance(u, dict) else u
        if url_str not in seen:
            seen.add(url_str)
            unique.append(u)

    print(f"[{config.name}] {len(unique):,} unique URLs ready")

    if max_discovery is None:
        with open(config.urls_file, "w", encoding="utf-8") as f:
            for item in unique:
                if isinstance(item, dict):
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                else:
                    f.write(item + "\n")
        print(f"[{config.name}] URLs cached to '{config.urls_file}'")

    return unique


# Helpers
def load_scraped_urls(config: SiteConfig) -> set[str]:
    # Return the set of URLs already visited in previous runs
    if not os.path.exists(config.scraped_urls_file):
        return set()
    with open(config.scraped_urls_file, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def mark_url_as_scraped(config: SiteConfig, url: str) -> None:
    # Append a URL to the per-site scrape log so it is skipped next run
    with open(config.scraped_urls_file, "a", encoding="utf-8") as f:
        f.write(url + "\n")


# Article scraping
def scrape_article(url: str, config: SiteConfig) -> dict | None:
    # Fetch and parse a single article page.
    print(f"Scraping: {url}")
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=15, allow_redirects=True)
    except requests.RequestException as e:
        print(f"ERROR (request): {e}")
        return None

    if response.status_code != 200:
        print(f"ERROR (HTTP {response.status_code}) — skipping")
        return None

    soup = BeautifulSoup(response.content, "lxml")

    title_el = soup.select_one(config.title_selector)
    # Ensure HTML entities in the title (like &quot;) are unescaped
    title = html.unescape(title_el.get_text(strip=True)) if title_el else ""

    # Restore missing first paragraph
    lead_tag = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    lead_text = html.unescape(lead_tag["content"].strip()) if lead_tag and lead_tag.get("content") else ""

    body_paragraphs = soup.select(config.body_selector)
    valid_texts = []
    for p in body_paragraphs:
        text = p.get_text(separator=" ").replace("\xa0", " ").strip()
        text = html.unescape(text) # Decode HTML entities
        
        # Aggressive scrubber: Remove the ADVERTISEMENT strings that ABS-CBN injects
        text = text.replace("ADVERTISEMENT", "").replace("Advertisement", "").strip()
        text = " ".join(text.split())
        # Check against blacklist to avoid footer/nav text
        if text and not any(b in text for b in UI_BLACKLIST):
            valid_texts.append(text)

    body = " ".join(valid_texts)

    # Fallback for dynamic sites (like ABS-CBN) where the body isn't in the HTML shell
    if len(body) < 50:
        raw_html = response.text
        
        raw_html = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), raw_html)
        raw_html = raw_html.replace('\\"', '"').replace('\\/', '/')
        
        p_matches = re.findall(r'<p[^>]*>(.*?)</p>', raw_html, flags=re.IGNORECASE | re.DOTALL)
        
        fallback_texts = []
        seen_ps = set() # Deduplication Set
        
        for p in p_matches:
            clean_p = BeautifulSoup(p, "lxml").get_text(separator=" ").replace("\xa0", " ").strip()
            
            # Translate any leftover HTML entities (e.g., &#x27; -> ')
            clean_p = html.unescape(clean_p)
            clean_p = clean_p.replace("ADVERTISEMENT", "").replace("Advertisement", "").strip()
            clean_p = " ".join(clean_p.split())
            
            # Filter out UI boilerplate 
            if any(b in clean_p for b in UI_BLACKLIST):
                continue
            
            if len(clean_p) > 40 and "{" not in clean_p and "}" not in clean_p:
                if clean_p not in seen_ps:
                    seen_ps.add(clean_p)
                    fallback_texts.append(clean_p)
                
        if fallback_texts:
            body = " ".join(fallback_texts)
    if len(body) < 50:
        def extract_schema_body(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ("articleBody", "text", "content", "body") and isinstance(v, str) and len(v) > 100:
                        return v
                    res = extract_schema_body(v)
                    if res: return res
            elif isinstance(obj, list):
                for item in obj:
                    res = extract_schema_body(item)
                    if res: return res
            return None

        for script in soup.find_all("script", type="application/ld+json"):
            if script.string:
                try:
                    schema_data = json.loads(script.string)
                    found_body = extract_schema_body(schema_data)
                    if found_body:
                        body = BeautifulSoup(found_body, "lxml").get_text(separator=" ").replace("\xa0", " ").strip()
                        body = html.unescape(body)
                        break
                except Exception:
                    pass

    # Restore first paragraph
    if lead_text:
        lead_start = " ".join(lead_text.split()[:5]) # Grab the first 5 words
        if lead_start and lead_start not in body:
            body = lead_text + " " + body

    if not title and not body:
        print("WARNING: Empty article (selector mismatch?) — skipping")
        return None

    # JSON cleanup
    title = title.replace('"', "'")
    body = body.replace('"', "'")
    body = body.replace('\u201c', "'").replace('\u201d', "'")  # Catch smart/curly quotes
    body = body.replace('\\', "")  # Catch any stray slashes

    canonical_url = response.url
    print(f"DONE {title[:70]!r}")
    return {"url": canonical_url, "title": title, "body": body.strip()}


def _append_to_jsonl(filepath: str, articles: list[dict]) -> None:
    # Append articles to a JSON-Lines file (one JSON object per line).
    with open(filepath, "a", encoding="utf-8") as f:
        for article in articles:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")

# Main scraping
def scrape_site(config: SiteConfig, n: int, request_delay: float = 0.75, max_discovery: int | None = None) -> int:
    # Scrape up to n new articles from the given site.
    all_items = collect_all_urls(config, max_discovery=max_discovery)
    already_scraped = load_scraped_urls(config)

    remaining = []
    for item in all_items:
        url_str = item["url"] if isinstance(item, dict) else item
        if url_str not in already_scraped:
            remaining.append(item)

    print(
        f"[{config.name}] {len(already_scraped):,} already visited | "
        f"{len(remaining):,} candidates left | target: {n:,} new articles"
    )

    if not remaining:
        print(f"[{config.name}] Nothing left to scrape.")
        return 0

    # For sitemap/rss sources, random sample
    # For id_range, shuffle so we don't always start from the same IDs
    sample = random.sample(remaining, min(n * 3, len(remaining))) \
        if config.url_source == "id_range" \
        else random.sample(remaining, min(n, len(remaining)))
    # For id_range we over-sample by 3× to account for 404s, stop once we hit n successes

    print(f"[{config.name}] Starting scrape ...\n")
    success_count = 0

    for item in sample:
        if success_count >= n:
            break
            
        url_str = item["url"] if isinstance(item, dict) else item
        
        if isinstance(item, dict):
            article = item
            print(f"Scraping: {url_str} (Bypassed page fetch via API)")
            print(f"DONE {article['title'][:70]!r}")
        else:
            article = scrape_article(url_str, config)
            
        if article:
            _append_to_jsonl(config.articles_file, [article])
            success_count += 1
            
        mark_url_as_scraped(config, url_str)
        
        # Only pause if we actually made a network request
        if not isinstance(item, dict):
            time.sleep(request_delay)

    print(
        f"\n[{config.name}] Run complete — "
        f"{success_count:,} articles written to '{config.articles_file}'"
    )
    return success_count

if __name__ == "__main__":
    # TODO: Change to True or False depending on if you want to only get a few articles
    TEST_MODE = True

    TARGET_PER_SITE = 10 if TEST_MODE else 5_000
    MAX_DISCOVERY = 2 if TEST_MODE else None

    SITES_TO_SCRAPE: list[Site] = [
        "Rappler",
        "ABSCBN",
        "GMA",
    ]

    # Pause between HTTP requests. Raise to ~2.0 if 429 rate-limited
    REQUEST_DELAY = 0.75

    total = 0
    for site in SITES_TO_SCRAPE:
        config = SITE_CONFIGS[site]
        print(f"\n{'═' * 20}")
        print(f"  {config.name}  (target: {TARGET_PER_SITE:,} articles)")
        print(f"{'═' * 20}")
        total += scrape_site(config, n=TARGET_PER_SITE, request_delay=REQUEST_DELAY, max_discovery=MAX_DISCOVERY)

    print(f"\n{'═' * 20}")
    print(f"All done.  Total articles scraped this run: {total:,}")
    print(f"{'═' * 20}")
