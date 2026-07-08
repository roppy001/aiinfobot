from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TIMEOUT_SECONDS = 15
MAX_ITEMS_PER_SOURCE = 10


def collect(scrape_sources: list[dict]) -> tuple[list[dict], list[str]]:
    """RSSがないサイトをHTMLスクレイピングで取得する。

    セレクタが実際のページ構造と合わない場合は0件になったり例外になったりするため、
    失敗したソースは failed に集めて呼び出し元でログ・通知に利用する。
    """
    items = []
    failed = []

    for source in scrape_sources:
        try:
            items.extend(_collect_one(source))
        except Exception:
            logger.warning("スクレイピングに失敗しました: %s", source["name"], exc_info=True)
            failed.append(source["name"])

    return items, failed


def _collect_one(source: dict) -> list[dict]:
    response = requests.get(source["url"], headers=HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    base_url = source.get("base_url", "").rstrip("/")

    results = []
    for row in soup.select(source["list_selector"])[:MAX_ITEMS_PER_SOURCE]:
        title_tag = row.select_one(source["title_selector"])
        link_tag = row.select_one(source["link_selector"])
        if not title_tag or not link_tag:
            continue

        href = link_tag.get("href", "")
        if href.startswith("/"):
            href = f"{base_url}{href}"

        title = title_tag.get_text(strip=True)
        if not title or not href:
            continue

        results.append(
            {
                "title": title,
                "link": href,
                "summary": "",
                "source": source["name"],
                "published": None,
            }
        )

    return results
