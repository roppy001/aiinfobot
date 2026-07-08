import logging

from collectors import rss_collector, scraper_collector
from config_loader import load_sources
from notifier import discord_notifier
from summarizer.openai_summarizer import summarize

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        sources = load_sources()

        rss_items, rss_failed = rss_collector.collect(sources.get("rss_sources", []))
        scrape_items, scrape_failed = scraper_collector.collect(
            sources.get("scrape_sources", [])
        )

        items = rss_items + scrape_items
        failed_sources = rss_failed + scrape_failed
        if failed_sources:
            logger.warning("取得に失敗したソース: %s", ", ".join(failed_sources))

        if not items:
            discord_notifier.send_error(
                "本日は収集できた記事が0件でした。sources.yamlの設定を確認してください。"
            )
            return {"statusCode": 200, "body": "no items collected"}

        report = summarize(items)
        discord_notifier.send_report(report)

        return {"statusCode": 200, "body": "ok"}

    except Exception as exc:
        logger.exception("Lambda実行中にエラーが発生しました")
        try:
            discord_notifier.send_error(f"{type(exc).__name__}: {exc}")
        except Exception:
            logger.exception("エラー通知のDiscord送信にも失敗しました")
        raise
