# FraudShield AI
### Explainable transaction fraud-risk intelligence — full-stack ML portfolio project

**Real machine learning. A working dashboard. Completely synthetic data.**

FraudShield AI demonstrates an end-to-end applied data-science workflow: generate a fictional payments dataset, compare two classification pipelines, tune a review threshold on validation data, report untouched-test metrics, serve live predictions through FastAPI, and explore results in a responsive interactive dashboard.

> **Research/demo use only.** All 7,200 records are simulated; the generator also creates the simulated fraud labels. This project does **not** demonstrate real-world predictive accuracy, regulatory compliance, financial security, or production-ready payment protection. Never use its scores to accept, reject, or block real payments.

## Quick start (macOS / Linux)

```bash
cd FraudShield_AI_Project
bash scripts/start_mac.sh
```

Or double-click `run.command` on macOS (if macOS allows executing it).

The launcher creates `.venv`, installs dependencies, and runs the included trained model. Then open **http://127.0.0.1:8000**. You need Python 3.10+ and internet access the first time dependencies are installed. Fonts are optional; the UI works without them.

On Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## Four interactive experiences

- **Overview:** 14-day synthetic activity trend, risk distribution, sample volume, and recently scored transactions.
- **Transactions:** searchable risk-level filtering, score bars, batch exploration, and downloadable fictional CSV.
- **Risk Lab:** construct a fictional transaction and get a live risk estimate with model-perturbation sensitivity drivers.
- **Model Insights:** honest held-out PR-AUC/precision/recall/ROC-AUC, feature permutation sensitivity, split sizes, and confusion matrix.

## Training / reproducibility

```bash
python -m ml.generate_data --rows 7200 --seed 42
python -m ml.train
```

The dataset is generated with deterministic feature/label RNG; timestamps are relative to generation time. Both `data/synthetic_transactions.csv` and `models/fraud_model.joblib` are **bundled**, so the initial demo does not require retraining. Only load the provided `.joblib` model or models you created yourself: pickle-based model artifacts are unsafe when sourced from untrusted files.

`ml/train.py` makes stratified train/validation/test partitions. It trains Logistic Regression and Random Forest pipelines with numeric imputation and categorical one-hot encoding, picks the model by **validation average precision (PR-AUC)**, selects the review cutoff using **validation F2** to favor recall, then evaluates once on a held-out test partition. It reports PR-AUC, ROC-AUC, precision, recall, F1, Brier score and confusion counts. More positive alerts can mean many false alarms; that tradeoff is shown explicitly.

Because this is a simulated generator, test results are *illustrative only*. Real-world validation would require permissioned, representative transaction labels, time-based holdouts, leakage audits, fairness analysis, alert cost evaluation, monitoring, calibration checks, human review workflows and security hardening.

### V2 interpretation improvements

V2 replaces rounded-probability sensitivity with **one-feature-at-a-time model log-odds comparisons** to the training reference profile. This avoids all-empty driver panels for near-100% examples with Logistic Regression. The signal bars indicate relative model changes, **not fraud-risk percentage points**, SHAP scores, or causal factors. Model training and held-out metrics are unchanged from V1. The dashboard also shows the confusion-matrix trade-off and avoids a decorative “99%” effectiveness claim.

### Explainability notes

- The model-insights feature rankings use **permutation importance** measured as test PR-AUC reduction.
- The Risk Lab drivers show *one-feature-at-a-time log-odds sensitivity* against training medians/modes. They are **not SHAP values, direct probability contributions, or causal explanations**.
- The review score is a *statistical output from a synthetic-data-trained model*, not a real fraud probability.

## API

FastAPI automatically provides **http://127.0.0.1:8000/docs**.

| Route | Method | Purpose |
| --- | --- | --- |
| `/api/health` | GET | Health and model availability |
| `/api/overview` | GET | Aggregated synthetic metrics and chart data |
| `/api/transactions?tier=High&limit=30` | GET | Model-scored transaction samples |
| `/api/model` | GET | Exact evaluation metadata |
| `/api/score` | POST | Score one fictional transaction |

Example:

```bash
curl -s http://127.0.0.1:8000/api/score \
  -H 'Content-Type: application/json' \
  -d '{"amount_usd":2850,"amount_ratio":8.2,"transactions_1h":8,"device_trust_score":0.13,"is_international":true}'
```

## Docker / deployment

```bash
docker build -t fraudshield-ai .
docker run --rm -p 8000:8000 fraudshield-ai
```

A GitHub Actions workflow runs tests on Python 3.11 and 3.12. The FastAPI service must be secured, reviewed, calibrated on representative real data and monitored before any production application; the bundled model is only for a local portfolio demonstration.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Project tree

```text
app/main.py                   FastAPI API + typed schema + inference
app/static/index.html         Accessible UI layout + native SVG icons
app/static/styles.css         Responsive dark design system
app/static/app.js             API-connected charts, filters, Risk Lab
ml/features.py                Shared model feature contract
ml/generate_data.py           Simulated-only payments data generator
ml/train.py                   ML training, selection, validation, reports
models/fraud_model.joblib     Bundled trained pipeline
models/metrics.json           Evaluation transparency
scripts/start_mac.sh          Local launcher
tests/                        Data, API and validation tests
```

**Author:** Muhammed Ansar · [GitHub](https://github.com/xansar1) · Prepared as a standalone project for a portfolio. It does not require changing an existing portfolio website.

## Publish on GitHub (separate repository)
1. Sign in to GitHub and create a **new empty public repository** under `xansar1` named `fraudshield-ai`. Do not add a starter README or `.gitignore`.
2. From the extracted project directory run `bash scripts/publish_github.sh`. This safely initializes Git if needed, checks the remote, commits the V2 source, then pushes `main`. **It never force-pushes.**
3. Source URL after the successful push: `https://github.com/xansar1/fraudshield-ai`.

## Deploy on Vercel (connected GitHub repository)
This package includes `app.py` and `vercel.json` for FastAPI auto-detection, plus `.python-version` selecting CPython 3.12.
Create a new Vercel project from `xansar1/fraudshield-ai`, keeping the **repository root** as the root directory and the **FastAPI** framework. Select free/Hobby resources when available; preview deployment protection may require changing settings for public demo access.
After deployment, open `/api/health`, `/api/overview`, `/api/model`, and the homepage. Test using `python scripts/smoke_deployment.py https://YOUR-DEPLOYMENT.vercel.app`.
Depending on the Vercel account, Python/scikit-learn function memory and cold starts can affect deployment.

## Alternative deployment: Render
`render.yaml` configures a Python web service (`plan: free`, when available) and health endpoint. New → Blueprint → connect `xansar1/fraudshield-ai`. Free Render apps spin down while idle, with a startup delay. Never mistake a spinning-up app for a permanent failure.
Use `python scripts/smoke_deployment.py https://YOUR-APP.onrender.com`.

**Deployment is not complete until a real public URL is verified.**
