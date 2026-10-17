"""Stable inference feature contract shared by training and the API."""

NUMERIC_FEATURES = [
    "amount_usd",
    "amount_ratio",
    "transactions_1h",
    "hour_of_day",
    "account_age_days",
    "device_trust_score",
    "merchant_risk_score",
    "is_international",
    "card_present",
    "is_new_payee",
]
CATEGORICAL_FEATURES = ["payment_channel", "merchant_category"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
CHANNELS = ["Card", "Wallet", "Bank transfer"]
CATEGORIES = ["Retail", "Electronics", "Digital goods", "Travel", "Grocery", "Services"]

FEATURE_LABELS = {
    "amount_usd": "Transaction amount",
    "amount_ratio": "Amount vs. usual spend",
    "transactions_1h": "Transactions in past hour",
    "hour_of_day": "Transaction time",
    "account_age_days": "Account age",
    "device_trust_score": "Device trust",
    "merchant_risk_score": "Merchant risk",
    "is_international": "Cross-border payment",
    "card_present": "Card physically present",
    "is_new_payee": "New recipient",
    "payment_channel": "Payment channel",
    "merchant_category": "Merchant category",
}
