# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A Discord bot that runs on AWS Lambda (Python) every morning at 9:00 JST. It collects AI-related news/articles from RSS feeds and scraped sites, has OpenAI score and summarize the top items, and posts the report to a Discord channel via webhook. Full requirements/design decisions are in [docs/requirements.md](docs/requirements.md).

There is no IaC (no SAM/CDK/Terraform) by design — this is a personal-use project deployed manually via the AWS Console or the scripts in `deploy/`.

## Commands

Build the Lambda deployment package (installs dependencies + zips `src/`):
```bash
cd deploy
./build.sh
```
Produces `function.zip` in the project root. Must be run from a bash shell (WSL/Git Bash on Windows).

Update an already-created Lambda function's code via AWS CLI (builds first, then `aws lambda update-function-code`):
```bash
export FUNCTION_NAME=aiinfobot
export AWS_REGION=ap-northeast-1
./deploy/deploy.sh
```

First-time AWS resource setup (IAM role, Lambda function, EventBridge schedule) is documented step-by-step in [deploy/setup_aws_resources.md](deploy/setup_aws_resources.md).

There is no test suite and no lint config in this repo currently.

## Architecture

Entry point is `src/handler.lambda_handler`, which orchestrates the whole pipeline and is the only place that talks to all the other modules:

1. `config_loader.py` loads `src/config/sources.yaml` (the list of news sources).
2. `collectors/rss_collector.py` and `collectors/scraper_collector.py` each fetch items from their sources and return `(items, failed_source_names)` — collection failures are logged and skipped, not fatal (a partial report still gets sent).
3. `summarizer/openai_summarizer.py` sends all collected items to the OpenAI API in one call and gets back a scored/curated JSON report (top 5–10 items). The scoring prompt encodes the importance criteria from docs/requirements.md §3.2.1 (weighs both business/marketing impact and technical significance, since the target reader is both a marketing and technical lead).
4. `notifier/discord_notifier.py` posts the report to the Discord webhook, chunking messages to stay under Discord's 2000-char limit. Both the report and any handler-level exception are sent through this module (`send_report` / `send_error`).

`src/config/sources.yaml` has two lists:
- `rss_sources`: name + URL, parsed with `feedparser`.
- `scrape_sources`: name + URL + CSS selectors (`list_selector`/`title_selector`/`link_selector`) for sites without RSS, parsed with `requests` + `BeautifulSoup`. Many of these selectors are unverified initial guesses (see README "既知の制限事項") and may need adjusting per-site if scraping silently returns 0 items.

No deduplication/persistence layer exists (no DynamoDB) — this is intentional per requirements, not an oversight. Each run is stateless.

## Packaging gotchas (learned the hard way — read before touching `deploy/build.sh`)

Dependencies are split into two files because they're installed differently:
- `requirements-binary.txt`: packages that may ship compiled extensions (openai, PyYAML, requests, beautifulsoup4). Installed with `pip install --platform manylinux2014_x86_64 --python-version 3.13 --implementation cp --abi cp313 --only-binary=:all:` to cross-build Linux/Lambda-compatible wheels regardless of the host OS.
- `requirements-pure.txt`: `feedparser` only. Its dependency `sgmllib3k` ships no wheel at all (sdist only), so it must be installed *without* the `--only-binary` cross-platform constraint (fine since it's pure Python and platform-independent).

Lambda runtime is pinned to **Python 3.13**, not the newest available (3.14), because `jiter` (a transitive dependency of the `openai` SDK, required `<1.0`) currently has no `cp314` wheels at all — this is a hard blocker independent of any version pin on `openai` itself. The local machine's Python version does not need to match the Lambda runtime version; `pip install --python-version/--abi/--platform` cross-builds for a different target.

`jiter` and `pydantic-core` (openai's compiled deps) are only published under the `manylinux_2_17`/`manylinux2014` tag, not newer tags like `manylinux_2_28` — if you ever "upgrade" the `--platform` flag to a newer manylinux baseline thinking it's safer, pip will fail to resolve them (`--platform` matches the exact tag given, not a compatibility-expanded set of older tags).

`build.sh` builds inside a `mktemp -d` Linux-native temp directory, not directly under the project folder. This matters under WSL: if the project lives on the Windows-mounted filesystem (`/mnt/c/...`), `pip install --target` inside that path fails with `OSError: [Errno 18] Invalid cross-device link` because pip's internal move from its own `/tmp` staging dir crosses filesystems. Only the final `function.zip` gets copied back into the project root.

`build.sh` verifies after install that no `.pyd` (Windows binary) files are present and that a `_pydantic_core*.so` (Linux binary) is present, failing loudly before zipping — this guards against silently deploying a broken zip, which previously manifested at Lambda runtime as `Runtime.ImportModuleError: No module named 'pydantic_core._pydantic_core'`.

When creating/updating the Lambda function itself, remember: runtime must be `python3.13`, handler must be `handler.lambda_handler`, and the default 3-second timeout must be raised (300s used in setup docs) or every real invocation will hit `Sandbox.Timedout`.

## Secrets

`OPENAI_API_KEY` and `DISCORD_WEBHOOK_URL` are set as plain Lambda environment variables — no Secrets Manager/Parameter Store. This is a deliberate accepted-risk choice for a personal-use bot (see docs/requirements.md §4), not something to "fix" by adding secret-store integration unless asked.
