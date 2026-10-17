# Portfolio-ready project summary (after you review and publish the source)

**Project:** FraudShield AI — Explainable Transaction Risk Intelligence

**Tagline:** From raw transactional signals to transparent, actionable ML insights.

**Description:** Built a responsive full-stack fraud-risk analytics demo with a reproducible Python data-science pipeline, Logistic Regression vs. Random Forest model selection, stratified train/validation/test evaluation, F2-based review-threshold tuning, and live FastAPI inference. An interactive dashboard visualizes simulated payments, risk segments, alert history and per-transaction feature sensitivity. The project emphasizes imbalanced-learning metrics, reproducibility, safe API validation and honest explainability.

**Stack:** Python · pandas · NumPy · scikit-learn · FastAPI · Pydantic · JavaScript · CSS · Docker · GitHub Actions

**Highlights:**
- Synthetic dataset of 7,200 transactions with 12 engineered numerical/categorical predictors.
- Real trained model, not rule-based fake scoring; locally available with a bundled model artifact.
- Held-out test PR-AUC, precision, recall, ROC-AUC, Brier score and confusion matrix; no test-set tuning.
- Feature-sensitivity readouts explicitly labeled as model perturbations, not causal or SHAP explanations.
- Mobile-responsive risk lab, real API endpoints, simulated monitoring dashboards and CSV export.

**Disclosure:** Every transaction and label is synthetic. Model outputs are for demonstrations only and cannot establish real-world fraud-detection accuracy.

**Live demo / GitHub:** Add only once deployed and verified. Do not use unverified URLs.
