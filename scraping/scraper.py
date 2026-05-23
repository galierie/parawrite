# pip install requests beautifulsoup4 lxml

import json
import random
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
    id_range_base_url: str | None = None  # e.g. "https://www.gmanetwork.com/news/story/{id}"
    id_range_start: int | None = None
    id_range_end: int | None = None

    # Used when url_source == "category_pages"
    # For sites whose sitemaps are rolling (only show recent articles).
    # We instead crawl paginated section/category listing pages and extract
    # article links from each page until we run out of pages or hit max_pages.
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
    # TODO: Inspect ABS-CBN sitemap output and refine these filters if needed.
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
        title_selector="h1.MuiTypography-root",
        body_selector="#bodyTopPart",
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
        body_selector=".story_main",
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

# TODO: For now, this is focused on Rappler only
def get_article_urls(site: Site,
                     sitemap_url: str,
                     max_urls=10000) -> list[str]:
    print(f"Fetching sitemap: {sitemap_url}")

    # this is to disguise the bot
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    response = requests.get(sitemap_url, headers=headers)
    soup = BeautifulSoup(response.content, "lxml-xml")
    loc_tags = soup.find_all("loc")
    urls: list[str] = []
    for loc in loc_tags:
        if len(urls) >= max_urls:
            break
        url = loc.text
        if ("rappler-prod-01" not in url and
            '.' != url[-4] and  # the 4th to last character shouldn't be dot, because then this isn't a news article
            ".jpg" not in url.lower() and
            ".png" not in url.lower() and
            ".gif" not in url.lower() and
            "go.rappler" not in url and
            "r3-assets" not in url and
            "r5-assets" not in url and
            "static.rappler.com" not in url and
            url != "https://www.rappler.com/latest/"):
            print(f"Found url: {url}")
            urls.append(url)

    print(f"Found {len(urls)} urls")
    return urls

def scrape_article_text(article_url: str) -> dict | None:
    print(f"Scraping: {article_url}")
    
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"}

    response = requests.get(article_url, headers=headers)

    if response.status_code != 200:
        print(f"ERROR with url: status code is {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.content, "lxml")
    title_element = soup.find(class_="post-single__title")
    title = title_element.get_text(strip=True) if title_element else ''
    body_paragraphs = soup.select(".post-single__content p")

    # Have to add the replace because some \xa0 characters are left out
    body = " ".join([p.text.replace(u'\xa0', u' ').strip() for p in body_paragraphs])

    print(f"Done scraping: {article_url}")
    output = {"title": title, "body": body}
    return output

def scrape_rappler_urls():
    urls = []
    urls.extend(get_article_urls("https://www.rappler.com/post-sitemap.xml"))
    # In Rappler, the sitemap goes up to post-sitemap380
    for i in range(2, 381):
        urls.extend(get_article_urls(f"https://www.rappler.com/post-sitemap{i}.xml"))

    # Write all articles into a text file
    with open("rappler_urls.txt", 'w', encoding="utf8") as rappler_urls:
        rappler_urls.write('\n'.join(urls))

def scrape_rappler_articles(n=1000):
    # TODO: Ideally we would take the first 30 words then determine their language
    urls = []
    with open("rappler_urls.txt", 'r', encoding="utf-8") as rappler_urls:
        while True:
            url = rappler_urls.readline()
            if not url:
                break
            urls.append(url)
    
    # Get n random URLs
    random_urls = random.sample(urls, n)
    scraped = []
    for url in random_urls:
        output = scrape_article_text(url.strip())
        if output is not None:
            scraped.append(output)
    
    return scraped

if __name__ == '__main__':
    # TODO: For now, only Rappler articles here

    # Uncomment to get all available Rappler URLs
    # scrape_rappler_urls()

    # Change the value in the function to control how many randomly chosen articles will be scraped
    scraped = scrape_rappler_articles(1000)
    with open("rappler_articles.json", 'w', encoding='utf8') as output_file:
        output_file.write(json.dumps({"scraped": scraped}))
    print("Wrote output into rappler_articles.json")