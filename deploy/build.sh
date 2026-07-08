#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# WSL等でプロジェクトがWindows側ファイルシステム(/mnt/c/...)にある場合、
# pipの一時ディレクトリ(/tmp、Linux側)からそこへの移動でクロスデバイスエラーが
# 発生することがあるため、ビルド自体はLinux側の一時ディレクトリで行う。
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

rm -rf "$PROJECT_ROOT/build" "$PROJECT_ROOT/function.zip"

# Lambda(Amazon Linux 2023, x86_64)向けにビルド済みwheelを取得する。
# jiter/pydantic-coreともmanylinux_2_17(=manylinux2014)タグで配布されているため
# このタグを指定する（manylinux_2_28等の新しいタグを指定すると、pipが--platformで
# 明示指定した単一タグにのみ一致させ、古いタグの実wheelを見つけられず解決に失敗する）。
# AL2023はglibc 2.34でmanylinux2014(glibc 2.17要求)を満たすため実行時の互換性は問題ない。
pip install -r "$PROJECT_ROOT/requirements-binary.txt" \
  --platform manylinux2014_x86_64 \
  --python-version 3.13 \
  --implementation cp \
  --abi cp313 \
  --only-binary=:all: \
  --target "$BUILD_DIR"

# feedparserは依存のsgmllib3kがwheel未提供のため、上の--only-binary制約から外し、
# 通常インストールする（純粋なPythonのみで構成されるため、動作プラットフォームを問わない）。
pip install -r "$PROJECT_ROOT/requirements-pure.txt" --target "$BUILD_DIR"

# ビルド環境向けのバイナリが誤って混入していないか検証する。
# 混入した状態でzip化するとLambda上で "No module named 'xxx._xxx'" のような
# ImportModuleErrorが発生するため、ここで検出して失敗させる。
if find "$BUILD_DIR" -name "*.pyd" | grep -q .; then
  echo "ERROR: Windows向けバイナリ(.pyd)が混入しています。" >&2
  find "$BUILD_DIR" -name "*.pyd" >&2
  exit 1
fi

if ! find "$BUILD_DIR" -name "_pydantic_core*.so" | grep -q .; then
  echo "ERROR: pydantic_core のLinux向けバイナリ(.so)が見つかりません。" >&2
  echo "pip installがLambda(manylinux2014_x86_64)向けのwheelを取得できていない可能性があります。" >&2
  exit 1
fi

cp -r "$PROJECT_ROOT"/src/* "$BUILD_DIR"/

(cd "$BUILD_DIR" && zip -rq function.zip . -x "*.pyc" -x "*/__pycache__/*")
cp "$BUILD_DIR/function.zip" "$PROJECT_ROOT/function.zip"

echo "function.zip を作成しました: $PROJECT_ROOT/function.zip"
