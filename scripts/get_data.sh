#!/usr/bin/env bash
# Downloads the free public datasets used by research/backtests into ./data_cache
# Sources (all public GitHub repos / PyPI, since Yahoo and Alpaca are blocked in the cloud sandbox):
#   skfolio wheel     : S&P 500 index + 20 large caps, daily closes 1990 to 2022
#   skfolio-datasets  : ~1455 Nasdaq stocks, daily closes 2018 to 2023
#   yennanliu/finance_data : QQQ, VTI and ~35 stocks, daily OHLCV 2016 to 2026
set -euo pipefail
OUT="${1:-data_cache}"
mkdir -p "$OUT" && cd "$OUT"
pip download skfolio --no-deps -d skpkg -q
unzip -q -o skpkg/*.whl 'skfolio/datasets/data/*' -d skx
cp skx/skfolio/datasets/data/sp500_dataset.csv.gz skx/skfolio/datasets/data/sp500_index.csv.gz .
[ -d skd ] || git clone --depth 1 https://github.com/skfolio/skfolio-datasets skd
cp skd/datasets/nasdaq_dataset.csv.gz .
if [ ! -d fd ]; then
  git clone --depth 1 --filter=blob:none --no-checkout https://github.com/yennanliu/finance_data fd
  (cd fd && git checkout HEAD -- data/prices)
fi
mkdir -p ohlcv && cp fd/data/prices/*.csv ohlcv/
echo "Data ready in $OUT"
