# aiinfobot

毎朝9:00(JST)にAI関連ニュース・指定サイトの更新情報を収集し、OpenAI APIで要約・重要度選定した上でDiscordにレポート投稿するAWS Lambda（Python）Bot。

要件定義は [docs/requirements.md](docs/requirements.md) を参照してください。

## 構成
```
src/
  handler.py                   # Lambdaエントリポイント
  config_loader.py             # sources.yaml読み込み
  config/sources.yaml          # 収集対象サイト定義
  collectors/
    rss_collector.py           # RSSフィード収集
    scraper_collector.py       # RSSがないサイトのHTMLスクレイピング
  summarizer/
    openai_summarizer.py       # OpenAI APIで重要度選定・要約
  notifier/
    discord_notifier.py        # Discord Webhookへの投稿・エラー通知
deploy/
  build.sh                     # 依存パッケージ込みでfunction.zipを作成
  deploy.sh                    # 既存Lambda関数へのコード更新
  setup_aws_resources.md       # 初回のAWSリソース作成手順（IAMロール/Lambda/EventBridge）
```

## 事前準備

### 1. OpenAI APIキーの取得
1. https://platform.openai.com/ にサインイン（未登録ならアカウント作成）
2. 「Billing」から支払い方法を登録（従量課金のため）
3. 「API keys」から新規キーを発行し、`sk-...` の値を控える

### 2. Discord Webhook URLの取得
1. 投稿先にしたいDiscordチャンネルの「チャンネルの編集」→「連携サービス」→「ウェブフック」を開く
2. 「新しいウェブフック」を作成し、Webhook URLをコピーする

### 3. AWS CLIの設定
`aws configure` で認証情報・デフォルトリージョンを設定済みであること。

## 初回セットアップ
[deploy/setup_aws_resources.md](deploy/setup_aws_resources.md) の手順に従って、IAMロール・Lambda関数・EventBridgeルールを作成してください。

## コード更新（2回目以降）
```bash
export FUNCTION_NAME=aiinfobot
export AWS_REGION=ap-northeast-1
./deploy/deploy.sh
```

## 収集対象サイトの追加・変更
`src/config/sources.yaml` を編集し、`deploy/deploy.sh` で再デプロイしてください。
- `rss_sources`: RSSフィードのURLを追加するだけで収集対象になります
- `scrape_sources`: RSSがないサイト用。`list_selector` / `title_selector` / `link_selector` はCSSセレクタで、対象サイトのHTML構造に合わせて調整が必要です

## 既知の制限事項
- **スクレイピング対象サイトのセレクタは未検証のものを含みます。** Anthropic、Sakana AI、各SIerのプレスリリースページはRSSが存在しないためHTMLスクレイピングで収集しますが、`sources.yaml`内のセレクタは初期値であり、実際のページ構造に合わせて調整が必要です。
- **NECのプレスリリースページは自動アクセスがブロックされる可能性があります。** 調査時に403 Forbiddenが返るケースを確認しており、Bot対策（Cloudflare等）が入っている可能性があります。スクレイピングが継続的に失敗する場合、対象から外すことも検討してください。
- **アクセンチュアのニュースルームはJavaScriptで描画されるページの可能性があります。** `requests`による静的HTML取得では記事一覧が取得できず0件になる場合があります。
- **重複排除は行いません。** 同じ記事が複数日にわたって再掲される可能性があります（要件として許容）。
- **シークレットは環境変数に平文で設定します。** 個人利用前提でSecrets Manager/Parameter Storeは使用していません（要件として許容）。

## 動作確認
`deploy/setup_aws_resources.md` の手順6（`aws lambda invoke`）で手動実行し、Discordに投稿されることを確認してください。
