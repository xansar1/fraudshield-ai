"""Read-only HTTP smoke test for deployed FraudShield AI (demo data only)."""
import json
import sys
from urllib.parse import urljoin
from urllib.request import Request, urlopen

base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/") + "/"

def req(method, path, data=None):
    raw = json.dumps(data).encode() if data else None
    q = Request(urljoin(base, path.lstrip("/")), data=raw, method=method)
    if raw:
        q.add_header("Content-Type", "application/json")
    with urlopen(q, timeout=50) as res:
        return json.load(res)

health = req("GET", "/api/health")
assert health["status"] == "ok" and health["model_ready"], health
overview = req("GET", "/api/overview")
assert overview["demo"] is True and overview["total"] == 7200, overview
model = req("GET", "/api/model")
assert model, model
result = req("POST", "/api/score", {
    "amount_usd": 2850, "amount_ratio": 8.2, "transactions_1h": 8,
    "hour_of_day": 2, "account_age_days": 12,
    "device_trust_score": .13, "merchant_risk_score": .84,
    "is_international": True, "card_present": False,
    "is_new_payee": True, "payment_channel": "Bank transfer",
    "merchant_category": "Digital goods",
})
assert result["demo"] is True and result["review_recommended"]
assert result["drivers"], result
print("PASS: health, overview (7,200), model info, prediction and explanation")
