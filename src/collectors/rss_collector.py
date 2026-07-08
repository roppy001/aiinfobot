from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import feedparser

logger = logging.getLogger(__name__)

LOOKBACK_HOURS = 36


def collect(rss_sources: list[dict]) -> tuple[list[dict], list[str]]:
    """RSSソース群から前回実行以降の記事を取得する。

    戻り値は (取得できた記事のリスト, 取得に失敗したソース名のリスト)。
    """
    items = []
    failed = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    for source in rss_sources:
        try:
            feed = feedparser.parse(source["url"])
            if feed.bozo and not feed.entries:
                raise RuntimeError(str(feed.bozo_exception))

            for entry in feed.entries:
                published = _parse_published(entry)
                if published is not None and published < cutoff:
                    continue
                items.append(
                    {
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", ""),
                        "source": source["name"],
                        "published": published.isoformat() if published else None,
                    }
                )
        except Exception:
            logger.warning("RSS取得に失敗しました: %s", source["name"], exc_info=True)
            failed.append(source["name"])

    return items, failed


def _parse_published(entry):
    for key in ("published_parsed", "updated_parsed"):
        value = getattr(entry, key, None)
        if value:
            return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc)
    return None
