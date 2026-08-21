from alerts import alerts_from_diff


def test_regime_and_sign_and_wall():
    diff = {
        "regime_changed": True,
        "regime_from": "LONG",
        "regime_to": "SHORT",
        "d_net_gex": -20,
        "prev_net_gex": 10,
        "curr_net_gex": -10,
        "d_call_wall": 100,
        "d_put_wall": 0,
        "prev_pcr": 0.8,
        "curr_pcr": 1.1,
        "d_pcr": 0.3,
    }
    msgs = alerts_from_diff(diff, wall_pts=50)
    assert any("Regime flip" in m for m in msgs)
    assert any("sign" in m.lower() for m in msgs)
    assert any("Call wall" in m for m in msgs)
    assert any("PCR crossed above" in m for m in msgs)


def test_empty_diff():
    assert alerts_from_diff({}) == []
