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


def test_shared_session_counts_each_clip_and_closes_the_group_atomically(tmp_path):
    quota = Quota(tmp_path / "quota.json")
    quota.initialize()
    root = quota.consume()
    quota.session(root, "one-session")
    second = quota.consume(root)
    restarted = Quota(quota.path)
    assert restarted.read()["remaining"] == 7 and restarted.read()["unresolved"]
    with pytest.raises(GuardError):
        restarted.consume()  # Restart cannot mistake an idle owned session for a closed one.
    with pytest.raises(GuardError):
        restarted.consume("wrong-owner")
    third = quota.consume(root)
    with pytest.raises(GuardError):
        quota.consume(root)
    with pytest.raises(GuardError):
        quota.session(root, "different-session")
    restarted.confirm_closed(third, "independent terminal GET")
    value = restarted.read()
    assert value["remaining"] == 6 and not value["unresolved"]
    assert [a["id"] for a in value["attempts"]] == [root, second, third]
    assert all(a["closed"] and a["session_id"] == "one-session" for a in value["attempts"])


def test_legacy_campaign_is_preserved_and_partial_group_closure_is_rejected(tmp_path):
    import json

    quota = Quota(tmp_path / "quota.json")
    quota.initialize()
    old = quota.consume()
    quota.confirm_closed(old, "legacy terminal GET")
    legacy = quota.read()
    del legacy["attempts"][0]["session_attempt"]
    quota.path.write_text(json.dumps(legacy))
    root = quota.consume()
    quota.session(root, "new-session")
    quota.consume(root)
    record = quota.read()
    assert record["attempts"][0] == legacy["attempts"][0]
    record["attempts"][-1]["closed"] = True
    quota.path.write_text(json.dumps(record))
    with pytest.raises(GuardError):
        quota.read()
