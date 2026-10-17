import numpy as np
from ml.features import FEATURES
from ml.generate_data import generate_transactions
from ml.train import threshold_for_f2


def test_data_is_reproducible_and_schema_complete():
    a = generate_transactions(650, seed=12)
    b = generate_transactions(650, seed=12)
    assert len(a) == 650
    assert all(f in a.columns for f in FEATURES)
    assert a[FEATURES + ["is_fraud"]].equals(b[FEATURES + ["is_fraud"]])
    assert a["is_fraud"].isin([0, 1]).all()
    assert a["amount_usd"].gt(0).all()
    assert a["device_trust_score"].between(0, 1).all()


def test_threshold_is_selected_from_validation_grid():
    truth = np.array([0, 1, 1, 0, 0, 1, 0, 1])
    probabilities = np.array([.04, .31, .72, .13, .09, .35, .08, .81])
    t = threshold_for_f2(truth, probabilities)
    assert 0.01 <= t <= 0.75
