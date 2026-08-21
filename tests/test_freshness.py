from datetime import datetime, timedelta

from freshness import freshness


def test_fresh_warm_stale():
    now = datetime(2026, 8, 21, 10, 0, 0)
    assert freshness(now - timedelta(seconds=30), as_of=now)["label"] == "fresh"
    assert freshness(now - timedelta(minutes=10), as_of=now)["label"] == "warm"
    assert freshness(now - timedelta(minutes=45), as_of=now)["stale"] is True


def test_missing():
    out = freshness(None)
    assert out["stale"] is True
    assert out["age_seconds"] is None
