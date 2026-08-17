from datetime import datetime

import pandas as pd

from metrics import (
    atm_iv,
    dealer_gex,
    gamma_flip_strike,
    gamma_regime,
    iv_skew,
    max_pain,
    oi_walls,
    put_call_ratio,
    time_to_expiry_years,
)


def test_time_to_expiry_known_window():
    as_of = datetime(2026, 8, 14)
    tte = time_to_expiry_years("21-Aug-2026", as_of=as_of)
    assert abs(tte - 7 / 365.0) < 1e-9


def test_time_to_expiry_floor_one_day():
    as_of = datetime(2026, 8, 21)
    tte = time_to_expiry_years("21-Aug-2026", as_of=as_of)
    assert abs(tte - 1 / 365.0) < 1e-9


def test_time_to_expiry_bad_format_fallback():
    tte = time_to_expiry_years("not-a-date")
    assert abs(tte - 1 / 52) < 1e-9


def test_max_pain_simple_chain():
    df = pd.DataFrame(
        [
            {"type": "CE", "strike": 100, "oi": 10},
            {"type": "CE", "strike": 110, "oi": 5},
            {"type": "PE", "strike": 100, "oi": 5},
            {"type": "PE", "strike": 110, "oi": 20},
        ]
    )
    pain = max_pain(df)
    assert pain in (100.0, 110.0)


def test_dealer_gex_signs():
    df = pd.DataFrame({"type": ["CE", "PE"], "gamma": [0.01, 0.01], "oi": [100, 100]})
    gex = dealer_gex(df["gamma"], df["oi"], df["type"])
    assert gex[0] > 0
    assert gex[1] < 0


def test_put_call_ratio():
    df = pd.DataFrame([{"type": "CE", "oi": 100}, {"type": "PE", "oi": 150}])
    assert abs(put_call_ratio(df) - 1.5) < 1e-9


def test_atm_iv():
    df = pd.DataFrame(
        [
            {"type": "CE", "strike": 100, "underlying": 101, "iv": 0.20},
            {"type": "PE", "strike": 100, "underlying": 101, "iv": 0.22},
            {"type": "CE", "strike": 110, "underlying": 101, "iv": 0.30},
        ]
    )
    iv = atm_iv(df, spot=101)
    assert iv is not None
    assert abs(iv - 0.21) < 1e-9


def test_oi_walls():
    df = pd.DataFrame(
        [
            {"type": "CE", "strike": 100, "oi": 10},
            {"type": "CE", "strike": 110, "oi": 50},
            {"type": "PE", "strike": 90, "oi": 80},
            {"type": "PE", "strike": 100, "oi": 20},
        ]
    )
    walls = oi_walls(df)
    assert walls["call_resistance"] == 110.0
    assert walls["put_support"] == 90.0


def test_gamma_flip_strike():
    df = pd.DataFrame(
        {
            "strike": [90, 100, 110, 90, 100, 110],
            "type": ["CE", "CE", "CE", "PE", "PE", "PE"],
            "gex": [50, 20, -10, -5, -40, -80],
        }
    )
    flip = gamma_flip_strike(df)
    assert flip is not None


def test_iv_skew():
    df = pd.DataFrame(
        [
            {"type": "PE", "strike": 80, "underlying": 100, "iv": 0.28},
            {"type": "CE", "strike": 120, "underlying": 100, "iv": 0.18},
            {"type": "CE", "strike": 100, "underlying": 100, "iv": 0.20},
        ]
    )
    skew = iv_skew(df, spot=100, wing=20)
    assert skew is not None
    assert abs(skew - 0.10) < 1e-9


def test_gamma_regime():
    assert "LONG" in gamma_regime(1.0)
    assert "SHORT" in gamma_regime(-1.0)
    assert gamma_regime(None) == "UNKNOWN"
