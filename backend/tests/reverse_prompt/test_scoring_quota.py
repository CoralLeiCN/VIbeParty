import math
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.games.reverse_prompt.quota import GuardError, Quota
from backend.games.reverse_prompt.scoring import normalize, points


def vector(x=1, y=0):
    return [x, y] + [0] * 382


def test_cosine_rule_exact_rounding_negative_ties_and_invalid_batch():
    assert normalize("  e\u0301!  ") == "é!"
    assert points(
        "a", ["a", "b"], [vector(), vector(), vector(0.824, math.sqrt(1 - 0.824**2))]
    ) == [100, 82]
    assert points("a", ["b", "c"], [vector(), vector(-1), vector(-1)]) == [0, 0]
    for invalid in ([0] * 384, [float("nan")] * 384, [1] * 383):
        with pytest.raises(ValueError):
            points("a", ["a", "c"], [vector(), vector(), invalid])


def test_persistent_quota_blocks_restart_and_does_not_refund(tmp_path):
    quota = Quota(tmp_path / "quota.json")
    with pytest.raises(GuardError):
        quota.consume()
    quota.initialize()
    with pytest.raises(GuardError):
        quota.initialize()
    attempt = quota.consume()
    quota.session(attempt, "session-example")
    restarted = Quota(quota.path)
    assert restarted.read()["remaining"] == 8
    with pytest.raises(GuardError):
        restarted.consume()
    restarted.confirm_closed(attempt, "test terminal state")
    for _ in range(8):
        attempt = restarted.consume()
        restarted.confirm_closed(attempt, "test terminal state")
    with pytest.raises(GuardError):
        restarted.consume()
    quota.path.write_text("corrupt")
    with pytest.raises(GuardError):
        restarted.read()


def test_concurrent_attempt_reservation_consumes_only_once(tmp_path):
    quota = Quota(tmp_path / "quota.json")
    quota.initialize()

    def attempt():
        try:
            return Quota(quota.path).consume()
        except GuardError:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda _: attempt(), range(4)))
    assert len([value for value in outcomes if value]) == 1
    assert quota.read()["remaining"] == 8


def test_corrupt_history_cannot_clear_an_unresolved_attempt(tmp_path):
    import json

    quota = Quota(tmp_path / "quota.json")
    quota.initialize()
    quota.consume()
    record = quota.read()
    record["unresolved"] = False
    quota.path.write_text(json.dumps(record))
    with pytest.raises(GuardError):
        quota.consume()
    record["unresolved"] = True
    del record["attempts"][0]["session_id"]
    quota.path.write_text(json.dumps(record))
    with pytest.raises(GuardError):
        quota.read()
