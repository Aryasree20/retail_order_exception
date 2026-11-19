import shutil
from pathlib import Path
import pytest
from app.pipeline import pipeline
from app.decision import decide
from app.schemas import Recommendation
from app.data import window_status, lookup_order

ROOT=Path(__file__).resolve().parents[1]

def report(cid): return decide(pipeline.invoke(cid))

def test_expected_examples():
    assert report('C001').recommendation == Recommendation.REPLACE_REVIEW
    assert report('C002').recommendation == Recommendation.INVESTIGATE_DELIVERY
    assert report('C004').recommendation == Recommendation.NOT_ELIGIBLE
    assert report('C007').recommendation == Recommendation.REFUND_REVIEW

def test_day_30_boundary_inclusive():
    within,days=window_status(lookup_order('O2001'),'2026-11-03')
    assert days==30 and within is True

def test_day_31_outside():
    within,days=window_status(lookup_order('O2001'),'2026-11-04')
    assert days==31 and within is False

def test_replacement_zero_stock_routes_refund_review():
    # C002 is Smartwatch with zero stock; customer delivery dispute takes precedence.
    p=report('C002')
    assert p.replacement_stock_available is False

def test_unknown_order_requests_info():
    assert report('C009').recommendation == Recommendation.REQUEST_INFO

def test_contradictory_delivery_claim_preserved():
    p=report('C002')
    assert any(e.kind=='customer_claim' for e in p.evidence)
    assert p.recommendation == Recommendation.INVESTIGATE_DELIVERY

def test_no_financial_or_inventory_mutation():
    before=(ROOT/'data/orders.csv').read_bytes(),(ROOT/'data/inventory.csv').read_bytes()
    report('C007')
    after=(ROOT/'data/orders.csv').read_bytes(),(ROOT/'data/inventory.csv').read_bytes()
    assert before==after

def test_duplicate_case_is_deterministic():
    a=report('C001').model_dump(mode='json'); b=report('C001').model_dump(mode='json')
    assert a==b

def test_missing_policy_fails_safe(monkeypatch, tmp_path):
    import app.pipeline as pl
    from app.schemas import Recommendation
    original=pl.read_policy
    monkeypatch.setattr(pl,'read_policy',lambda: (_ for _ in ()).throw(FileNotFoundError('policy missing')))
    p=decide(pl.pipeline.invoke('C001'))
    assert p.recommendation == Recommendation.MANUAL_REVIEW
    monkeypatch.setattr(pl,'read_policy',original)

def test_invalid_structured_model_output_rejected():
    from app.schemas import CaseReport
    with pytest.raises(Exception):
        CaseReport.model_validate({'case_id':'C001','recommendation':'AUTO_REFUND'})
