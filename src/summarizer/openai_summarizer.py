from __future__ import annotations

import json
import os

from openai import OpenAI

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# 要件定義 docs/requirements.md の 3.2.1 重要度判定基準に対応したプロンプト。
# 読者（社内でマーケティングと技術リードを兼務）の視点でスコアリングさせる。
SYSTEM_PROMPT = """\
あなたはAI業界の情報を収集し、社内向けに毎朝レポートを作成するアシスタントです。
レポートの読者は、社内でマーケティングと技術リードを兼務する担当者です。

与えられた記事一覧から、以下の基準でスコアリングし、重要度の高い記事を5〜10件選んでください。

- ビジネス・マーケティングインパクト: 新製品/サービスのローンチ、大型資金調達・M&A、
  大手企業でのAI導入事例、市場や競合構造への影響
- 技術的重要性: 新モデル・新技術のリリース、ベンチマークでの性能向上、OSS化、
  API/SDKの重要な変更、技術的ブレークスルー
- 競合・業界動向: NTTデータグループ、富士通、日立製作所、NEC、日本アイ・ビー・エム、
  アクセンチュアの生成AI関連発表は原則的に取り上げる（内容が薄い定型リリースは除外可）
- 情報源の一次性・信頼性: OpenAI、Anthropic、Google、Preferred Networks、Sakana AI等の
  公式発表を二次報道より優先する
- 同一トピックを扱う記事が複数ある場合は、最も情報量の多い1件に集約する
- ビジネス・技術いずれかの観点で特に高スコアな記事は、もう片方の観点が低くても採用する

出力は必ず次のJSON形式のみで返してください（前置き・説明文は不要）。
{
  "overview": "その日のAI業界のトピック傾向を2〜3文で要約したテキスト",
  "articles": [
    {
      "title": "記事タイトル（日本語に翻訳可）",
      "source": "出典名",
      "url": "記事URL",
      "summary": "日本語で3〜4文程度の要約",
      "business_score": 1から5の整数,
      "tech_score": 1から5の整数
    }
  ]
}
"""


def summarize(items: list[dict]) -> dict:
    client = OpenAI()

    articles_payload = [
        {
            "title": item["title"],
            "source": item["source"],
            "url": item["link"],
            "summary": item.get("summary", ""),
        }
        for item in items
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(articles_payload, ensure_ascii=False),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    return json.loads(response.choices[0].message.content)
