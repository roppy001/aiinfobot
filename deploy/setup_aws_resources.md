# AWSリソースの初回セットアップ手順

IaCツールは使わず、AWS CLIで手動セットアップする前提の手順です。
一度だけ実行すればよい作業なので、内容を確認しながら1つずつ実行してください。
（`FUNCTION_NAME`, `AWS_REGION`, `AWS_ACCOUNT_ID` は自分の環境に合わせて置き換えてください）

## 0. 事前準備
```bash
export FUNCTION_NAME=aiinfobot
export AWS_REGION=ap-northeast-1
export AWS_ACCOUNT_ID=123456789012   # aws sts get-caller-identity で確認できます
```

## 1. IAM実行ロールの作成
環境変数にシークレットを直接設定する運用のため、ロールに必要な権限は
CloudWatch Logsへの書き込みのみです（Secrets Manager/Parameter Storeへのアクセスは不要）。

```bash
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name aiinfobot-lambda-role \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name aiinfobot-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

## 2. 関数パッケージの作成
```bash
cd deploy
./build.sh
cd ..
```

## 3. Lambda関数の作成
```bash
aws lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --runtime python3.13 \
  --handler handler.lambda_handler \
  --role "arn:aws:iam::${AWS_ACCOUNT_ID}:role/aiinfobot-lambda-role" \
  --timeout 300 \
  --memory-size 512 \
  --zip-file fileb://function.zip
```

## 4. 環境変数の設定
`OPENAI_API_KEY` と `DISCORD_WEBHOOK_URL` を取得済みであれば設定します。
（未取得の場合は取得後にこのコマンドを実行してください）

```bash
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --environment "Variables={OPENAI_API_KEY=sk-xxxx,DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxx/yyyy}"
```

## 5. 毎朝9:00(JST)実行のEventBridgeルール作成
cronはUTC基準のため `cron(0 0 * * ? *)` が JST 9:00 に相当します。
二重投稿防止のため、リトライ回数は0に設定します。

```bash
aws events put-rule \
  --name aiinfobot-daily-trigger \
  --region "$AWS_REGION" \
  --schedule-expression "cron(0 0 * * ? *)" \
  --state ENABLED

aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --statement-id aiinfobot-eventbridge-invoke \
  --action "lambda:InvokeFunction" \
  --principal events.amazonaws.com \
  --source-arn "arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/aiinfobot-daily-trigger"

aws events put-targets \
  --rule aiinfobot-daily-trigger \
  --region "$AWS_REGION" \
  --targets "Id"="1","Arn"="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${FUNCTION_NAME}","RetryPolicy"="{MaximumRetryAttempts=0}"
```

## 6. 動作確認（手動実行）
```bash
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --cli-binary-format raw-in-base64-out \
  --payload '{}' \
  response.json

cat response.json
```
Discordに投稿されるか、CloudWatch Logs（`/aws/lambda/$FUNCTION_NAME`）でエラーがないか確認してください。

## 以降のコード更新
初回セットアップ後は `deploy/deploy.sh` でコード更新のみ行えます。
```bash
export FUNCTION_NAME=aiinfobot
export AWS_REGION=ap-northeast-1
./deploy/deploy.sh
```
