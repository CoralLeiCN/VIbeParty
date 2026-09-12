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
            if any(not attempt["closed"] for attempt in attempts[:-1]):
                raise ValueError()
            if value["unresolved"] != bool(attempts and not attempts[-1]["closed"]):
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

    def consume(self) -> str:
        with self.locked():
            value = self._read()
            if value["unresolved"]:
                raise GuardError("Previous provider session needs operator closure verification.")
            if value["remaining"] <= 0:
                raise GuardError("The live campaign has no attempts remaining.")
            attempt = secrets.token_hex(16)
            value["remaining"] -= 1
            value["unresolved"] = True
            value["attempts"].append({"id": attempt, "session_id": None, "closed": False})
            self._write(value)
            return attempt

    def session(self, attempt: str, session_id: str):
        with self.locked():
            value = self._read()
            if not value["unresolved"] or value["attempts"][-1]["id"] != attempt:
                raise GuardError("Attempt changed")
            value["attempts"][-1]["session_id"] = session_id
            self._write(value)

    def confirm_closed(self, attempt: str, evidence: str):
        with self.locked():
            value = self._read()
            if value["attempts"][-1]["id"] != attempt or not evidence:
                raise GuardError("Attempt changed or closure evidence missing")
            value["attempts"][-1].update(closed=True, closure=evidence)
            value["unresolved"] = False
            self._write(value)
