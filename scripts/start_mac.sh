#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install -r requirements.txt
if [[ ! -f models/fraud_model.joblib || ! -f data/synthetic_transactions.csv ]]; then
  python -m ml.generate_data
  python -m ml.train
fi
printf '\nFraudShield AI available at http://127.0.0.1:8000\nPress Ctrl+C to stop.\n\n'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
