"""FastAPI service for a transparent, synthetic-data-only fraud ML demo."""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict

from ml.features import FEATURES, FEATURE_LABELS, CHANNELS, CATEGORIES

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models/fraud_model.joblib"
DATA_PATH = ROOT / "data/synthetic_transactions.csv"
app = FastAPI(title="FraudShield AI | ML Risk Analytics", version="1.0.0",
              description="Demonstration only. Uses exclusively fictional transaction data.")
app.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")


class TransactionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_usd: float = Field(185, ge=1, le=100000)
    amount_ratio: float = Field(1.4, ge=.1, le=30)
    transactions_1h: int = Field(2, ge=0, le=50)
    hour_of_day: int = Field(13, ge=0, le=23)
    account_age_days: int = Field(420, ge=0, le=15000)
    device_trust_score: float = Field(.84, ge=0, le=1)
    merchant_risk_score: float = Field(.19, ge=0, le=1)
    is_international: bool = False
    card_present: bool = True
    is_new_payee: bool = False
    payment_channel: Literal["Card", "Wallet", "Bank transfer"] = "Card"
    merchant_category: Literal["Retail", "Electronics", "Digital goods", "Travel", "Grocery", "Services"] = "Retail"


@lru_cache(maxsize=1)
def resource_bundle():
    if not MODEL_PATH.exists():
        raise RuntimeError("Trained model missing. Run: python -m ml.generate_data && python -m ml.train")
    if not DATA_PATH.exists():
        raise RuntimeError("Demo dataset missing. Run: python -m ml.generate_data")
    bundle = joblib.load(MODEL_PATH)  # Only load artifacts bundled by this project, never untrusted uploads.
    data = pd.read_csv(DATA_PATH)
    probs = bundle["pipeline"].predict_proba(data[FEATURES])[:, 1]
    data["risk_score"] = np.round(probs, 5)
    threshold = float(bundle["threshold"])
    data["risk_level"] = [risk_tier(float(p), threshold) for p in probs]
    data["date_iso"] = pd.to_datetime(data["timestamp"], utc=True).dt.strftime("%Y-%m-%d")
    return bundle, data


def risk_tier(prob: float, threshold: float) -> str:
    if prob >= threshold:
        return "High"
    if prob >= threshold * .55:
        return "Elevated"
    return "Low"


def row_payload(row) -> dict:
    return {
        "id": str(row.transaction_id),
        "timestamp": str(row.timestamp),
        "amount": round(float(row.amount_usd), 2),
        "channel": str(row.payment_channel),
        "category": str(row.merchant_category),
        "risk": round(float(row.risk_score), 4),
        "tier": str(row.risk_level),
        "simulated_label": bool(row.is_fraud),
    }


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "app/static/index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "model_ready": MODEL_PATH.exists(), "demo": True}


@app.get("/api/overview")
def overview():
    bundle, data = resource_bundle()
    metadata = bundle["metadata"]
    counts = data.risk_level.value_counts()
    by_day = data.groupby("date_iso", sort=True).agg(
        transactions=("transaction_id", "count"),
        high_risk=("risk_level", lambda a: int((a == "High").sum()))
    ).reset_index()
    by_day["date"] = pd.to_datetime(by_day["date_iso"]).dt.strftime("%b %d")
    by_channel = data.groupby("payment_channel").agg(count=("transaction_id", "count"),
        high=("risk_level", lambda a: int((a == "High").sum()))).reset_index()
    avg_risk = float(data.risk_score.mean())
    return {
        "demo": True,
        "total": len(data),
        "total_volume": round(float(data.amount_usd.sum()), 2),
        "high_risk": int(counts.get("High", 0)),
        "elevated": int(counts.get("Elevated", 0)),
        "low_risk": int(counts.get("Low", 0)),
        "avg_risk": round(avg_risk, 4),
        "flagged_volume": round(float(data.loc[data.risk_level == "High", "amount_usd"].sum()), 2),
        "simulated_fraud_count": int(data.is_fraud.sum()),
        "timeline": by_day[["date", "transactions", "high_risk"]].to_dict(orient="records"),
        "channels": by_channel.to_dict(orient="records"),
        "top_alerts": [row_payload(row) for row in data.nlargest(7, "risk_score").itertuples()],
        "recent": [row_payload(row) for row in data.head(9).itertuples()],
        "model": {"name": metadata["model_name"], "threshold": metadata["threshold"],
                  "test_pr_auc": metadata["test"]["pr_auc"]},
    }


@app.get("/api/transactions")
def transactions(tier: Literal["All", "High", "Elevated", "Low"] = "All",
                 limit: int = Query(30, ge=1, le=200)):
    _, df = resource_bundle()
    subset = df if tier == "All" else df[df.risk_level == tier]
    return {"demo": True, "items": [row_payload(row) for row in subset.head(limit).itertuples()],
            "matching": len(subset)}


@app.get("/api/model")
def model_info():
    bundle, _ = resource_bundle()
    return bundle["metadata"]


@app.post("/api/score")
def score_transaction(item: TransactionInput):
    bundle, _ = resource_bundle()
    record = item.model_dump()
    model = bundle["pipeline"]
    row = pd.DataFrame([record], columns=FEATURES)
    probability = float(model.predict_proba(row)[0, 1])
    threshold = float(bundle["threshold"])
    ref = bundle["reference_profile"]
    # Comparing raw decision scores avoids probability saturation (e.g. 100.0%).
    # For Logistic Regression these raw scores are additive log-odds.
    # This is counterfactual model sensitivity, NOT causality or SHAP.
    def model_log_odds(frame: pd.DataFrame) -> float:
        if hasattr(model, "decision_function"):
            return float(model.decision_function(frame)[0])
        p = float(model.predict_proba(frame)[0, 1])
        p = float(np.clip(p, 1e-12, 1 - 1e-12))
        return float(np.log(p / (1 - p)))

    actual_log_odds = model_log_odds(row)
    shifts = []
    for feature in FEATURES:
        reference_row = row.copy()
        reference_row[feature] = [ref[feature]]
        raw_shift = actual_log_odds - model_log_odds(reference_row)
        if abs(raw_shift) < 0.035:
            continue
        shifts.append({
            "feature": feature,
            "label": FEATURE_LABELS[feature],
            "log_odds_shift": round(raw_shift, 3),
        })

    risk_increasing = sorted(
        (entry for entry in shifts if entry["log_odds_shift"] > 0),
        key=lambda entry: entry["log_odds_shift"], reverse=True
    )[:5]
    risk_reducing = sorted(
        (entry for entry in shifts if entry["log_odds_shift"] < 0),
        key=lambda entry: entry["log_odds_shift"]
    )[:3]
    tier = risk_tier(probability, threshold)
    return {
        "demo": True,
        "risk": round(probability, 6),
        "risk_percent": round(probability * 100, 1),
        "tier": tier,
        "review_recommended": probability >= threshold,
        "threshold": threshold,
        "drivers": risk_increasing,
        "mitigating_signals": risk_reducing,
        "explanation_units": "log-odds shift versus training reference",
        "explanation_note": (
            "One-feature-at-a-time change in model log-odds versus training "
            "medians/modes. This is model sensitivity, not causal explanation, "
            "and individual contributions are not probabilities."
        ),
        "model": bundle["metadata"]["model_name"],
        "disclaimer": (
            "Scores and explanations come from a synthetic-data model. "
            "Not a measured real-world fraud probability or a payment decision."
        ),
    }
