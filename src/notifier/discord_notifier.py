import os
from datetime import datetime, timedelta, timezone

import requests

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
DISCORD_CHUNK_LIMIT = 1900  # Discordの1メッセージ2000文字制限に余裕を持たせる
JST = timezone(timedelta(hours=9))


def send_report(report: dict) -> None:
    lines = [f"**AIニュースレポート ({_today_str()})**", "", report.get("overview", ""), ""]

    for i, article in enumerate(report.get("articles", []), start=1):
        lines.append(
            f"**{i}. {article.get('title', '(タイトルなし)')}**"
            f"（出典: {article.get('source', '不明')}）\n"
            f"{article.get('summary', '')}\n"
            f"{article.get('url', '')}\n"
        )

    _post_chunked("\n".join(lines))


def send_error(message: str) -> None:
    _post_chunked(f":warning: **AIニュースBot エラー通知**\n```\n{message}\n```")


def _post_chunked(content: str) -> None:
    if not WEBHOOK_URL:
        raise RuntimeError("環境変数 DISCORD_WEBHOOK_URL が設定されていません")

    for chunk in _split(content, DISCORD_CHUNK_LIMIT):
        response = requests.post(WEBHOOK_URL, json={"content": chunk}, timeout=15)
        response.raise_for_status()


def _split(text: str, limit: int):
    for i in range(0, len(text), limit):
        yield text[i : i + limit]


def _today_str() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d")
