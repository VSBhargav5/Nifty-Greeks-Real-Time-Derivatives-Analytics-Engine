import pandas as pd

from compare import diff_summaries, strike_movers


def test_diff_summaries_deltas():
    prev = {
        "timestamp": "t0",
        "spot": 100.0,
        "net_gex": 10.0,
        "pcr": 1.0,
        "call_wall": 110.0,
        "put_wall": 90.0,
        "regime": "LONG",
        "total_oi": 100,
    }
    curr = {
        "timestamp": "t1",
        "spot": 102.0,
        "net_gex": -5.0,
        "pcr": 1.2,
        "call_wall": 120.0,
        "put_wall": 90.0,
        "regime": "SHORT",
        "total_oi": 130,
    }
    d = diff_summaries(curr, prev)
    assert d["d_spot"] == 2.0
    assert d["d_net_gex"] == -15.0
    assert d["d_call_wall"] == 10.0
    assert d["regime_changed"] is True


def test_diff_empty():
    assert diff_summaries({}, {"spot": 1}) == {}


def test_strike_movers_top_oi():
    prev = pd.DataFrame(
        [
            {"strike": 100, "type": "CE", "oi": 10, "gex": 5},
            {"strike": 110, "type": "CE", "oi": 20, "gex": 8},
        ]
    )
    curr = pd.DataFrame(
        [
            {"strike": 100, "type": "CE", "oi": 40, "gex": 15},
            {"strike": 110, "type": "CE", "oi": 18, "gex": 7},
        ]
    )
    movers = strike_movers(curr, prev, n=2)
    assert not movers.empty
    assert movers.iloc[0]["strike"] == 100
    assert movers.iloc[0]["d_oi"] == 30
