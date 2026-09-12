"""An explicitly allocated campaign; atomic updates survive reset and restart."""

import fcntl
import json
import os
import secrets
import tempfile
from contextlib import contextmanager
from pathlib import Path


class GuardError(RuntimeError):
    pass


class Quota:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def locked(self):
        if not self.path.parent.is_dir():
            raise GuardError("The live campaign has not been allocated.")
        try:
            with self.path.with_suffix(".lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)
        except OSError as exc:
            raise GuardError(
                "Live quota storage is unavailable. Ask the operator to check it."
            ) from exc

    def _read(self):
        try:
            value = json.loads(self.path.read_text())
            if (
                value["version"] != 1
                or value["limit"] != 9
                or type(value["remaining"]) is not int
                or not 0 <= value["remaining"] <= 9
                or type(value["unresolved"]) is not bool
                or len(value["attempts"]) != 9 - value["remaining"]
            ):
                raise ValueError()
            attempts = value["attempts"]
            if not isinstance(attempts, list):
                raise ValueError()
            for attempt in attempts:
                if (
                    not isinstance(attempt["id"], str)
                    or not attempt["id"]
                    or type(attempt["closed"]) is not bool
                    or (
                        attempt["session_id"] is not None
                        and not isinstance(attempt["session_id"], str)
                    )
                ):
                    raise ValueError()
            if len({attempt["id"] for attempt in attempts}) != len(attempts):
                raise ValueError()
            groups = {}
            previous_group = None
            for attempt in attempts:
                group = attempt.get("session_attempt", attempt["id"])
                if group not in groups:
                    if group != attempt["id"]:
                        raise ValueError()
                    groups[group] = []
                elif group != previous_group:
                    raise ValueError()
                groups[group].append(attempt)
                previous_group = group
            for group in groups.values():
                if len(group) > 3 or any(
                    item["session_id"] != group[0]["session_id"]
                    or item["closed"] != group[0]["closed"]
                    for item in group
                ):
                    raise ValueError()
                if len(group) > 1 and not group[0]["session_id"]:
                    raise ValueError()
            open_groups = [group for group in groups.values() if not group[0]["closed"]]
            if len(open_groups) > 1 or (open_groups and open_groups[0][-1] is not attempts[-1]):
                raise ValueError()
            if value["unresolved"] != bool(open_groups):
                raise ValueError()
            return value
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise GuardError(
                "Live quota is missing or invalid. Ask the operator to check it."
            ) from exc

    def read(self):
        with self.locked():
            return self._read()

    def _write(self, value):
        descriptor, name = tempfile.mkstemp(prefix="quota-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w") as handle:
                json.dump(value, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.path)
            parent = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        finally:
            Path(name).unlink(missing_ok=True)

    def initialize(self):
        """Operator-only, never called by app startup. Refuses to replenish a campaign."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.locked():
            if self.path.exists():
                raise GuardError("Campaign already exists; initialization cannot replenish it.")
            self._write(
                {"version": 1, "limit": 9, "remaining": 9, "unresolved": False, "attempts": []}
            )

    def consume(self, session_attempt: str | None = None) -> str:
        with self.locked():
            value = self._read()
            group = None
            if session_attempt is not None:
                group = self._active_group(value, session_attempt)
                if not group[0]["session_id"] or len(group) >= 3:
                    raise GuardError("The current session cannot accept another clip.")
            elif value["unresolved"]:
                raise GuardError("Previous provider session needs operator closure verification.")
            if value["remaining"] <= 0:
                raise GuardError("The live campaign has no attempts remaining.")
            attempt = secrets.token_hex(16)
            value["remaining"] -= 1
            value["unresolved"] = True
            value["attempts"].append(
                {
                    "id": attempt,
                    "session_attempt": group[0]["id"] if group else attempt,
                    "session_id": group[0]["session_id"] if group else None,
                    "closed": False,
                }
            )
            self._write(value)
            return attempt

    def session(self, attempt: str, session_id: str):
        with self.locked():
            value = self._read()
            group = self._active_group(value, attempt)
            if not session_id or any(
                item["session_id"] not in {None, session_id} for item in group
            ):
                raise GuardError("Provider session identity changed")
            for item in group:
                item["session_id"] = session_id
            self._write(value)

    def confirm_closed(self, attempt: str, evidence: str):
        with self.locked():
            value = self._read()
            if not evidence:
                raise GuardError("Attempt changed or closure evidence missing")
            group = self._active_group(value, attempt)
            for item in group:
                item.update(closed=True, closure=evidence)
                if "evidence" in item:
                    item["evidence"]["closed"] = True
            value["unresolved"] = False
            self._write(value)

    def record_outcome(self, attempt: str, evidence: dict):
        """Persist sanitized diagnostics without changing allowance or closure state."""
        with self.locked():
            value = self._read()
            item = next((item for item in value["attempts"] if item["id"] == attempt), None)
            if item is None:
                raise GuardError("Attempt changed")
            item["evidence"] = {**evidence, "closed": item["closed"]}
            self._write(value)

    @staticmethod
    def _active_group(value, attempt):
        if not value["unresolved"] or not value["attempts"]:
            raise GuardError("No active provider session")
        latest = value["attempts"][-1]
        root = latest.get("session_attempt", latest["id"])
        group = [
            item for item in value["attempts"] if item.get("session_attempt", item["id"]) == root
        ]
        if attempt not in {item["id"] for item in group}:
            raise GuardError("Attempt changed")
        return group
