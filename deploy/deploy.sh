#!/usr/bin/env bash
set -euo pipefail

: "${FUNCTION_NAME:?FUNCTION_NAME を環境変数で指定してください（例: export FUNCTION_NAME=aiinfobot）}"
: "${AWS_REGION:?AWS_REGION を環境変数で指定してください（例: export AWS_REGION=ap-northeast-1）}"

cd "$(dirname "$0")"
./build.sh
cd ..

aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --zip-file fileb://function.zip

echo "Lambda関数 $FUNCTION_NAME を更新しました"
