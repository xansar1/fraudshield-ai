import math
from fastapi.testclient import TestClient
from app.main import app, MODEL_PATH

client = TestClient(app)


def test_home_and_assets_load():
    assert client.get('/').status_code == 200
    for p in ['/static/styles.css', '/static/app.js']:
        response = client.get(p)
        assert response.status_code == 200
        assert len(response.content) > 1000


def test_model_artifact_exists():
    assert MODEL_PATH.exists()
    metrics = client.get('/api/model').json()
    assert metrics['dataset_rows'] > 1000
    assert sum(metrics['split'].values()) == metrics['dataset_rows']
    assert metrics['demo_notice'].startswith('SIMULATED DATA')
    assert 0 < metrics['test']['pr_auc'] < 1
    assert metrics['test']['confusion']['tp'] >= 0


def test_overview_count_invariants():
    response = client.get('/api/overview')
    assert response.status_code == 200
    data = response.json()
    assert data['demo'] is True
    assert data['total'] == data['low_risk'] + data['elevated'] + data['high_risk']
    assert len(data['timeline']) >= 7
    assert len(data['recent']) == 9
    assert 0 <= data['avg_risk'] <= 1


def test_filters_and_limits():
    all_data = client.get('/api/transactions?tier=All&limit=10').json()
    assert len(all_data['items']) == 10
    high = client.get('/api/transactions?tier=High&limit=20').json()
    assert all(row['tier'] == 'High' for row in high['items'])
    assert client.get('/api/transactions?limit=100000').status_code == 422
    assert client.get('/api/transactions?tier=unknown').status_code == 422


def test_scoring_and_validation():
    response = client.post('/api/score', json={})
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data['risk'] <= 1
    assert data['tier'] in ('Low', 'Elevated', 'High')
    assert data['model']
    assert 'not causal' in data['explanation_note']
    assert 'log-odds' in data['explanation_units']
    assert isinstance(data['drivers'], list)
    assert isinstance(data['mitigating_signals'], list)
    assert client.post('/api/score', json={'device_trust_score':-2}).status_code == 422
    assert client.post('/api/score', json={'account_age_days':-1}).status_code == 422
    assert client.post('/api/score', json={'payment_channel':'Crypto'}).status_code == 422
    assert client.post('/api/score', json={'secret_pin':1234}).status_code == 422


def test_riskier_example_is_scored_above_baseline():
    base = client.post('/api/score', json={}).json()
    risky = client.post('/api/score', json={
        'amount_usd':2850,'amount_ratio':8.2,'transactions_1h':8,
        'hour_of_day':2,'account_age_days':12,'device_trust_score':.13,
        'merchant_risk_score':.84,'is_international':True,
        'card_present':False,'is_new_payee':True,
        'payment_channel':'Bank transfer','merchant_category':'Digital goods',
    }).json()
    assert risky['risk'] > base['risk']


def test_extreme_risk_case_has_explanatory_signals():
    risky = client.post('/api/score', json={
        'amount_usd':3500,'amount_ratio':9.5,'transactions_1h':15,
        'hour_of_day':3,'account_age_days':2,'device_trust_score':.05,
        'merchant_risk_score':.95,'is_international':True,
        'card_present':False,'is_new_payee':True,
    })
    assert risky.status_code == 200
    data = risky.json()
    assert data['tier'] == 'High'
    assert data['risk_percent'] > 99.0
    assert len(data['drivers']) >= 3
    assert data['drivers'][0]['log_odds_shift'] > 0
    assert all(d['log_odds_shift'] > 0 for d in data['drivers'])
    assert all(d['log_odds_shift'] < 0 for d in data['mitigating_signals'])
    assert data['drivers'][0]['label'] in ('Amount vs. usual spend', 'Transaction amount')


def test_display_copy_does_not_claim_production_fraud_accuracy():
    html = client.get('/').text
    assert '99<span>%</span>' not in html
    assert 'WHAT THE TEST ACTUALLY SHOWS' in html
    assert 'SIGNALS INCREASING MODEL SCORE' in html
