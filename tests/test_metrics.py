from datetime import datetime

import pandas as pd

from metrics import dealer_gex, max_pain, time_to_expiry_years


def test_time_to_expiry_known_window():
    as_of = datetime(2026, 8, 14)
    # 7 calendar days later
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
    df = pd.DataFrame(
        {
            "type": ["CE", "PE"],
            "gamma": [0.01, 0.01],
            "oi": [100, 100],
        }
    )
    gex = dealer_gex(df["gamma"], df["oi"], df["type"])
    assert gex[0] > 0
    assert gex[1] < 0
