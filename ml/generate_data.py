"""Generate a reproducible, entirely fictional transaction dataset.

This generator intentionally uses a simulated risk process. It is NOT a dataset
of actual customer behavior and is not appropriate to validate banking accuracy.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from ml.features import CHANNELS, CATEGORIES


def generate_transactions(n: int = 7200, seed: int = 42) -> pd.DataFrame:
    if n < 100:
        raise ValueError("At least 100 rows required")
    rng = np.random.default_rng(seed)
    amount = np.clip(rng.lognormal(4.0, 1.08, n), 2, 6000).round(2)
    ratio = np.clip(rng.lognormal(.05, .78, n), .1, 15).round(2)
    velocity = np.clip(rng.poisson(1.3, n) + rng.binomial(1, .035, n) * rng.integers(3, 9, n), 0, 18)
    hours = rng.integers(0, 24, n)
    account_age = np.clip(rng.exponential(440, n).astype(int) + 1, 1, 3500)
    device_trust = np.clip(rng.beta(5, 2, n), .01, 1).round(3)
    merchant_risk = np.clip(rng.beta(2, 6, n), .01, 1).round(3)
    international = rng.binomial(1, .11, n)
    card_present = rng.binomial(1, .57, n)
    new_payee = rng.binomial(1, .19, n)
    channel = rng.choice(CHANNELS, n, p=[.57, .28, .15])
    category = rng.choice(CATEGORIES, n, p=[.28, .16, .17, .09, .17, .13])

    logits = (
        -5.65
        + .60 * np.log1p(amount / 190)
        + 1.55 * (ratio >= 3)
        + .33 * np.clip(ratio - 3, 0, 9)
        + 1.25 * (velocity >= 4)
        + 1.65 * (device_trust < .38)
        + 1.20 * international
        + 1.20 * new_payee
        + 2.00 * merchant_risk
        + .38 * ((hours <= 5) | (hours >= 23))
        + .63 * (account_age < 30)
        + .52 * (channel == "Bank transfer")
        + .47 * (category == "Digital goods")
        + .90 * (international & (card_present == 0))
        + .90 * ((ratio >= 3) & (velocity >= 4))
    )
    likelihood = 1 / (1 + np.exp(-logits))
    labels = rng.binomial(1, likelihood)
    # One stable UTC snapshot: reruns reproduce every feature except current dates.
    now = datetime.now(timezone.utc).replace(microsecond=0)
    offsets = rng.integers(0, 14 * 24 * 60, n)
    timestamps = [(now - timedelta(minutes=int(v))).isoformat() for v in offsets]
    frame = pd.DataFrame({
        "transaction_id": [f"TX-{120000+i:06d}" for i in range(n)],
        "timestamp": timestamps,
        "amount_usd": amount,
        "amount_ratio": ratio,
        "transactions_1h": velocity,
        "hour_of_day": hours,
        "account_age_days": account_age,
        "device_trust_score": device_trust,
        "merchant_risk_score": merchant_risk,
        "is_international": international,
        "card_present": card_present,
        "is_new_payee": new_payee,
        "payment_channel": channel,
        "merchant_category": category,
        "is_fraud": labels,
    })
    return frame.sort_values("timestamp", ascending=False).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fictional sample transactions")
    parser.add_argument("--rows", type=int, default=7200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/synthetic_transactions.csv")
    args = parser.parse_args()
    df = generate_transactions(args.rows, args.seed)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved {len(df):,} synthetic transactions to {path} | simulated fraud rate: {df.is_fraud.mean():.1%}")


if __name__ == "__main__":
    main()
