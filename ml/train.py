"""Train, select and evaluate a fraud screening demo with held-out test data.

The data are synthetic, generated from a simulated statistical process; test
numbers only describe that simulator, not performance on real-world payments.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             confusion_matrix, fbeta_score, precision_score,
                             recall_score, f1_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from ml.features import FEATURES, NUMERIC_FEATURES, CATEGORICAL_FEATURES, FEATURE_LABELS


def build_pipeline(kind: str) -> Pipeline:
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler() if kind == "logistic" else "passthrough")])
    categorical = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    prep = ColumnTransformer([("num", numeric, NUMERIC_FEATURES),
                              ("cat", categorical, CATEGORICAL_FEATURES)])
    if kind == "logistic":
        model = LogisticRegression(max_iter=850, random_state=42)
    else:
        model = RandomForestClassifier(n_estimators=140, max_depth=13,
                                       min_samples_leaf=4, max_features="sqrt",
                                       class_weight=None,
                                       n_jobs=-1, random_state=42)
    return Pipeline([("preprocess", prep), ("classifier", model)])


def threshold_for_f2(y_true: np.ndarray, proba: np.ndarray) -> float:
    # Threshold is chosen only on the validation partition, not the test set.
    scores = []
    for t in np.linspace(.01, .75, 75):
        pred = (proba >= t).astype(int)
        scores.append((fbeta_score(y_true, pred, beta=2, zero_division=0), float(t)))
    # For identical F2, choose the more conservative (higher) cutoff.
    return round(max(scores)[1], 3)


def train(input_path: Path, output_dir: Path) -> dict:
    df = pd.read_csv(input_path)
    absent = set(FEATURES + ["is_fraud"]) - set(df.columns)
    if absent:
        raise ValueError(f"Required columns missing: {sorted(absent)}")
    df = df.copy()
    df["is_fraud"] = df["is_fraud"].astype(int)
    if df["is_fraud"].nunique() != 2 or len(df) < 300:
        raise ValueError("Training requires >=300 rows containing both target classes")
    x = df[FEATURES]
    y = df["is_fraud"]
    trainval_x, test_x, trainval_y, test_y = train_test_split(
        x, y, test_size=.20, stratify=y, random_state=42)
    train_x, val_x, train_y, val_y = train_test_split(
        trainval_x, trainval_y, test_size=.20, stratify=trainval_y, random_state=42)

    candidates = {}
    for kind in ("logistic", "forest"):
        candidate = build_pipeline(kind)
        candidate.fit(train_x, train_y)
        p = candidate.predict_proba(val_x)[:, 1]
        candidates[kind] = (candidate, p, average_precision_score(val_y, p))
    winner = max(candidates, key=lambda k: candidates[k][2])
    model, p_val, val_ap = candidates[winner]
    threshold = threshold_for_f2(val_y.to_numpy(), p_val)
    p_test = model.predict_proba(test_x)[:, 1]
    verdict = (p_test >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(test_y, verdict, labels=[0, 1]).ravel()

    # Use feature-level held-out permutation sensitivity (not causal SHAP).
    explain_x = test_x.sample(n=min(350, len(test_x)), random_state=42)
    explain_y = test_y.loc[explain_x.index]
    importance = permutation_importance(
        model, explain_x, explain_y, scoring="average_precision", n_repeats=3,
        random_state=42, n_jobs=1)
    ranked = sorted([
        {"feature": f, "label": FEATURE_LABELS[f],
         "importance": round(max(0., float(importance.importances_mean[i])), 5)}
        for i, f in enumerate(FEATURES)
    ], key=lambda item: item["importance"], reverse=True)
    refs = {}
    for feature in FEATURES:
        if feature in CATEGORICAL_FEATURES:
            refs[feature] = str(train_x[feature].mode().iloc[0])
        else:
            refs[feature] = float(train_x[feature].median())

    metadata = {
        "app": "FraudShield AI",
        "demo_notice": "SIMULATED DATA — test metrics cannot predict real-world performance",
        "model_name": "Random Forest" if winner == "forest" else "Logistic Regression",
        "selection_metric": "validation average precision (PR-AUC)",
        "validation_pr_auc": round(float(val_ap), 4),
        "threshold": threshold,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": len(df),
        "synthetic_fraud_rate": round(float(y.mean()), 4),
        "split": {"train": len(train_x), "validation": len(val_x), "test": len(test_x)},
        "test": {
            "pr_auc": round(float(average_precision_score(test_y, p_test)), 4),
            "roc_auc": round(float(roc_auc_score(test_y, p_test)), 4),
            "precision": round(float(precision_score(test_y, verdict, zero_division=0)), 4),
            "recall": round(float(recall_score(test_y, verdict, zero_division=0)), 4),
            "f1": round(float(f1_score(test_y, verdict, zero_division=0)), 4),
            "brier": round(float(brier_score_loss(test_y, p_test)), 4),
            "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        },
        "feature_importance": ranked,
        "candidates": {k: {"validation_pr_auc": round(float(v[2]), 4)} for k, v in candidates.items()},
    }
    output_dir.mkdir(exist_ok=True, parents=True)
    joblib.dump({"pipeline": model, "threshold": threshold, "reference_profile": refs,
                 "features": FEATURES, "metadata": metadata}, output_dir / "fraud_model.joblib", compress=3)
    (output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"model": metadata["model_name"], "rows": len(df),
                      "held_out_test": metadata["test"], "cutoff": threshold}, indent=2))
    return metadata


def main():
    parser = argparse.ArgumentParser(description="Train FraudShield AI on fictional transactions")
    parser.add_argument("--input", default="data/synthetic_transactions.csv")
    parser.add_argument("--output", default="models")
    args = parser.parse_args()
    train(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
