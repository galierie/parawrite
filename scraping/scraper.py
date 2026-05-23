# pip install requests beautifulsoup4 lxml

import json
import random
import requests
from bs4 import BeautifulSoup
from pprint import pprint
from dataclasses import dataclass
from typing import Callable, Literal

# Types
Site = Literal['Rappler', 'ABSCBN', 'GMA']

@dataclass
class SiteConfig:
    name: str
    sitemap_urls: list[str]
    url_filter: Callable[[str], bool]
    title_selector: str
    body_selector: str
    urls_file: str
    articles_file: str
    scraped_urls_file: str

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