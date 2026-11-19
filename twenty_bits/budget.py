"""Reserve money before submitting work. Keep holds until costs are known.

This module uses only the Python standard library and never contacts Tinker.
All money is stored as decimal strings, rounded upward to a microdollar.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import fcntl
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import tempfile
from typing import TypeVar
import uuid

CAP = Decimal("50.000000")
MULTIPLIER = Decimal("1.5")
MICRODOLLAR = Decimal("0.000001")
ACTIVE_STATES = {"reserved", "dispatching", "submitted"}
STATES = ACTIVE_STATES | {"settled", "void"}
T = TypeVar("T")


class BudgetError(RuntimeError):
    """A missing, invalid, or exhausted budget must stop new calls."""


def money(value: str | Decimal) -> Decimal:
    """Reject floats and non-finite amounts instead of silently rounding them."""
    if not isinstance(value, (str, Decimal)):
        raise BudgetError("Use a decimal string for USD amounts, never a float.")
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount < 0:
            raise BudgetError("USD amounts must be finite and nonnegative.")
        return amount.quantize(MICRODOLLAR, rounding=ROUND_CEILING)
    except InvalidOperation as exc:
        raise BudgetError("Invalid USD amount.") from exc


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    """One local ledger, with atomic writes and a separate process lock file.

    Locks cover the budget transaction, never the network wait. Reservations
    survive crashes, exceptions, and restarts. A missing ledger is an error.
    """

    def __init__(self, path: str | Path = "ledger.json") -> None:
        self.path = Path(path).resolve()
        self._database = None
        # Legacy exports remain readable. Live ledgers opt in through migration.
        try:
            header = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return
        storage = header.get("storage")
        if storage is None and self.path.with_suffix(".sqlite3").exists():
            raise BudgetError(
                "An unfinished ledger migration exists. Stop and reconcile it."
            )
        if storage is not None:
            if storage.get("engine") != "sqlite-v1":
                raise BudgetError("Unsupported live ledger storage.")
            database = self.path.parent / storage["database"]
            if (
                database.parent != self.path.parent
                or database.name != storage["database"]
            ):
                raise BudgetError(
                    "Live ledger database must be beside its audit export."
                )
            from .ledger_store import SQLiteStore

            self._database = SQLiteStore(database, self.path, BudgetError)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        with self.path.with_suffix(self.path.suffix + ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _read(self) -> dict:
        return self.read_snapshot(self.path)

    @staticmethod
    def read_snapshot(path: str | Path) -> dict:
        """Read an audit export offline; never use it to admit live requests."""
        try:
            data = json.loads(Path(path).read_text())
            if data["schema_version"] != 1:
                raise BudgetError("Unsupported ledger schema.")
            if data["cap_usd"] != str(CAP) or data["reservation_multiplier"] != "1.5":
                raise BudgetError(
                    "The approved $50 cap and 1.5 multiplier cannot be changed."
                )
            if not isinstance(data["entries"], list) or not isinstance(
                data["blocks"], list
            ):
                raise BudgetError("Invalid ledger collections.")
            ids = set()
            for entry in data["entries"]:
                if not isinstance(entry["id"], str) or entry["id"] in ids:
                    raise BudgetError("Invalid or duplicate reservation ID.")
                ids.add(entry["id"])
                if entry["state"] not in STATES:
                    raise BudgetError("Unknown reservation state.")
                estimate = money(entry["estimate_usd"])
                maximum = money(entry["max_cost_usd"])
                reserved = money(entry["reserved_usd"])
                if maximum < estimate or reserved != max(
                    money(estimate * MULTIPLIER), maximum
                ):
                    raise BudgetError("Invalid reservation amount.")
                if entry["state"] == "submitted" and not entry["request_id"]:
                    raise BudgetError("Submitted work needs its original request ID.")
                if entry["state"] == "settled":
                    money(entry["actual_usd"])
                    if not entry["evidence"]:
                        raise BudgetError("Settled costs need billing evidence.")
                elif entry["actual_usd"] is not None:
                    raise BudgetError("Unsettled work cannot have a final cost.")
            return data
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise BudgetError(
                "Missing or corrupt ledger. Do not recreate it to resume spending."
            ) from exc

    def _write(self, data: dict) -> None:
        filename = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self.path.parent,
                prefix=self.path.name + ".",
                suffix=".tmp",
                delete=False,
            ) as handle:
                filename = handle.name
                json.dump(data, handle, indent=2, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(filename, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if filename is not None and os.path.exists(filename):
                os.unlink(filename)

    @staticmethod
    def _totals(data: dict) -> tuple[Decimal, Decimal]:
        spent = sum(
            (
                money(e["actual_usd"])
                for e in data["entries"]
                if e["state"] == "settled"
            ),
            Decimal(0),
        )
        held = sum(
            (
                money(e["reserved_usd"])
                for e in data["entries"]
                if e["state"] in ACTIVE_STATES
            ),
            Decimal(0),
        )
        return spent, held

    @staticmethod
    def snapshot_status(path: str | Path) -> dict:
        """Offline totals from a completed export, not a live admission check."""
        data = Ledger.read_snapshot(path)
        spent, held = Ledger._totals(data)
        breached = any(
            e["state"] == "settled"
            and money(e["actual_usd"]) > money(e["max_cost_usd"])
            for e in data["entries"]
        )
        return {
            "cap_usd": str(CAP),
            "spent_usd": str(money(spent)),
            "held_usd": str(money(held)),
            "available_usd": str(CAP - spent - held),
            "blocked": bool(data["blocks"] or breached or spent + held > CAP),
            "entries": data["entries"],
        }

    @staticmethod
    def _check_admission(data: dict, extra: Decimal) -> None:
        spent, held = Ledger._totals(data)
        breached = any(
            e["state"] == "settled"
            and money(e["actual_usd"]) > money(e["max_cost_usd"])
            for e in data["entries"]
        )
        if data["blocks"] or breached:
            raise BudgetError(
                "Ledger is blocked. Reconcile the cost discrepancy before any new work."
            )
        if spent + held + extra > CAP:
            raise BudgetError(
                f"Refused: ${spent} spent + ${held} held + ${extra} new exceeds $50."
            )

    def entries(
        self, *, operation=None, operation_prefix=None, states=None
    ) -> list[dict]:
        """Read only matching reservations; hot callers must not load the history."""
        with self._locked():
            if self._database:
                with self._database.transaction() as (connection, _):
                    return self._database.entries(
                        connection,
                        operation=operation,
                        operation_prefix=operation_prefix,
                        states=states,
                    )
            return [
                entry
                for entry in self._read()["entries"]
                if (operation is None or entry["operation"] == operation)
                and (
                    not operation_prefix
                    or entry["operation"].startswith(operation_prefix)
                )
                and (states is None or entry["state"] in states)
            ]

    def get(self, entry_id: str) -> dict:
        with self._locked():
            if self._database:
                with self._database.transaction() as (connection, _):
                    row = connection.execute(
                        "SELECT data FROM entries WHERE id=?", (entry_id,)
                    ).fetchone()
                    if row is None:
                        raise BudgetError("Unknown reservation ID.")
                    return json.loads(row[0])
            entry = next(
                (e for e in self._read()["entries"] if e["id"] == entry_id), None
            )
            if entry is None:
                raise BudgetError("Unknown reservation ID.")
            return entry

    def summary(self, *, operation_prefix=None) -> dict:
        """Totals without entry bodies; filters preserve run-prefix accounting."""
        with self._locked():
            if self._database:
                with self._database.transaction() as (connection, meta):
                    spent, held = self._database.summary(connection, operation_prefix)
                    total_spent, total_held, breached = self._database.totals(
                        connection
                    )
                    return {
                        "cap_usd": str(CAP),
                        "spent_usd": str(money(spent)),
                        "held_usd": str(money(held)),
                        "available_usd": str(CAP - spent - held),
                        "blocked": bool(
                            meta["blocks"] or breached or total_spent + total_held > CAP
                        ),
                    }
            data = self._read()
            entries = data["entries"]
            if operation_prefix:
                data = {
                    **data,
                    "entries": [
                        e
                        for e in entries
                        if e["operation"].startswith(operation_prefix)
                    ],
                }
            spent, held = self._totals(data)
            all_spent, all_held = self._totals({"entries": entries})
            breached = any(
                e["state"] == "settled"
                and money(e["actual_usd"]) > money(e["max_cost_usd"])
                for e in entries
            )
            return {
                "cap_usd": str(CAP),
                "spent_usd": str(money(spent)),
                "held_usd": str(money(held)),
                "available_usd": str(CAP - spent - held),
                "blocked": bool(
                    data["blocks"] or breached or all_spent + all_held > CAP
                ),
            }

    def status(self) -> dict:
        if self._database:
            with self._locked(), self._database.transaction() as (connection, meta):
                spent, held, breached = self._database.totals(connection)
                return {
                    "cap_usd": str(CAP),
                    "spent_usd": str(money(spent)),
                    "held_usd": str(money(held)),
                    "available_usd": str(CAP - spent - held),
                    "blocked": bool(meta["blocks"] or breached or spent + held > CAP),
                    "entries": self._database.entries(connection),
                }
        with self._locked():
            data = self._read()
            spent, held = self._totals(data)
            breached = any(
                e["state"] == "settled"
                and money(e["actual_usd"]) > money(e["max_cost_usd"])
                for e in data["entries"]
            )
            return {
                "cap_usd": str(CAP),
                "spent_usd": str(money(spent)),
                "held_usd": str(money(held)),
                "available_usd": str(CAP - spent - held),
                "blocked": bool(data["blocks"] or breached or spent + held > CAP),
                "entries": data["entries"],
            }

    def check_run(self, *, estimate_usd: str, max_cost_usd: str) -> str:
        """Refuse an unaffordable run before it starts; per-call holds still apply.

        This is a preflight, not a reservation. The single run coordinator must
        recheck after other work and reserve each operation through call().
        """
        estimate, maximum = money(estimate_usd), money(max_cost_usd)
        if maximum < estimate:
            raise BudgetError("The maximum cost cannot be below the estimate.")
        required = max(money(estimate * MULTIPLIER), maximum)
        with self._locked():
            if self._database:
                with self._database.transaction() as (connection, meta):
                    self._check_database_admission(connection, meta, required)
            else:
                self._check_admission(self._read(), required)
        return str(required)

    def reserve(
        self, *, phase: int, operation: str, estimate_usd: str, max_cost_usd: str
    ) -> str:
        """Hold at least estimate times 1.5 and the full token-limited maximum."""
        if type(phase) is not int or phase not in range(6) or not operation.strip():
            raise BudgetError("Supply a phase from 0 to 5 and an operation name.")
        estimate, maximum = money(estimate_usd), money(max_cost_usd)
        if maximum < estimate:
            raise BudgetError("The maximum cost cannot be below the estimate.")
        reserved = max(money(estimate * MULTIPLIER), maximum)
        with self._locked():
            entry_id = str(uuid.uuid4())
            entry = {
                "id": entry_id,
                "phase": phase,
                "operation": operation,
                "estimate_usd": str(estimate),
                "max_cost_usd": str(maximum),
                "reserved_usd": str(reserved),
                "state": "reserved",
                "request_id": None,
                "actual_usd": None,
                "evidence": None,
                "created_at": now(),
                "updated_at": now(),
            }
            if self._database:
                with self._database.transaction() as (connection, meta):
                    self._check_database_admission(connection, meta, reserved)
                    self._database.put(connection, entry, insert=True)
            else:
                data = self._read()
                self._check_admission(data, reserved)
                data["entries"].append(entry)
                self._write(data)
        return entry_id

    def migrate(self) -> bool:
        """Explicit, offline switch to SQLite; original entries and approvals stay intact."""
        from .ledger_store import SCHEMA, SQLiteStore

        with self._locked():
            if self._database:
                with self._database.transaction():
                    return False
            data = self._read()
            before = self._totals(data)
            destination = self.path.with_suffix(".sqlite3")
            if destination.exists():
                raise BudgetError(
                    "A database already exists; do not overwrite billing history."
                )
            data["storage"] = {
                "engine": "sqlite-v1",
                "database": destination.name,
                "source_json_sha256": hashlib.sha256(
                    self.path.read_bytes()
                ).hexdigest(),
                "note": "Live state is transactional SQLite; this JSON is an explicit audit export.",
            }
            encoded = (json.dumps(data, indent=2, allow_nan=False) + "\n").encode()
            handle = tempfile.NamedTemporaryFile(
                dir=self.path.parent, suffix=".sqlite3.tmp", delete=False
            )
            temporary = Path(handle.name)
            handle.close()
            try:
                with sqlite3.connect(temporary) as connection:
                    connection.executescript(SCHEMA)
                    meta = {k: v for k, v in data.items() if k != "entries"}
                    connection.execute(
                        "INSERT INTO metadata VALUES(1,?)", (json.dumps(meta),)
                    )
                    connection.execute(
                        "INSERT INTO totals VALUES(1,0,0,0,?)",
                        (hashlib.sha256(encoded).hexdigest(),),
                    )
                    for entry in data["entries"]:
                        SQLiteStore.put(connection, entry, insert=True)
                    assert SQLiteStore.totals(connection)[:2] == before
                    assert (
                        connection.execute("PRAGMA integrity_check").fetchone()[0]
                        == "ok"
                    )
                connection.close()
                with temporary.open("rb") as source:
                    os.fsync(source.fileno())
                os.replace(temporary, destination)
                # The same file lock excludes every old and new writer during the switch.
                # A crash between these files fails closed through the orphan-database check.
                self._write(data)
                self._database = SQLiteStore(destination, self.path, BudgetError)
            finally:
                temporary.unlink(missing_ok=True)
            return True

    def export_snapshot(self) -> dict:
        """Compact the audit export offline, never on the sampling request path."""
        if not self._database:
            return self._read()
        with self._locked(), self._database.transaction() as (connection, meta):
            data = {**meta, "entries": self._database.entries(connection)}
            self._write(data)
            digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
            connection.execute(
                "UPDATE totals SET snapshot_sha256=? WHERE id=1", (digest,)
            )
            self._database.snapshot_stat = None
            return data

    def _check_database_admission(self, connection, meta, extra):
        spent, held, breached = self._database.totals(connection)
        if meta["blocks"] or breached:
            raise BudgetError(
                "Ledger is blocked. Reconcile the cost discrepancy before any new work."
            )
        if spent + held + extra > CAP:
            raise BudgetError(
                f"Refused: ${spent} spent + ${held} held + ${extra} new exceeds $50."
            )

    def _update(
        self, entry_id: str, edit: Callable[[dict], None], *, admit: bool = False
    ) -> None:
        with self._locked():
            if self._database:
                with self._database.transaction() as (connection, meta):
                    if admit:
                        self._check_database_admission(connection, meta, Decimal(0))
                    row = connection.execute(
                        "SELECT data FROM entries WHERE id=?", (entry_id,)
                    ).fetchone()
                    if row is None:
                        raise BudgetError("Unknown reservation ID.")
                    entry = json.loads(row[0])
                    edit(entry)
                    entry["updated_at"] = now()
                    self._database.put(connection, entry)
                return
            data = self._read()
            if admit:
                self._check_admission(data, Decimal(0))
            entry = next((e for e in data["entries"] if e["id"] == entry_id), None)
            if entry is None:
                raise BudgetError("Unknown reservation ID.")
            edit(entry)
            entry["updated_at"] = now()
            self._write(data)

    def dispatch(self, entry_id: str, send: Callable[[], T]) -> T:
        """Persist the dispatch state before invoking send exactly once.

        An exception leaves the money held: the server may have accepted work.
        Never pass an async function here. Await its APIFuture after dispatch.
        """

        def mark(entry: dict) -> None:
            if entry["state"] != "reserved":
                raise BudgetError(
                    "This reservation was already dispatched. Recover its future; do not resubmit."
                )
            entry["state"] = "dispatching"

        self._update(entry_id, mark, admit=True)
        return send()

    def call(self, send: Callable[[], T], **reservation) -> tuple[str, T]:
        """The call boundary: ledger first, network second."""
        entry_id = self.reserve(**reservation)
        return entry_id, self.dispatch(entry_id, send)

    def attach_request_id(self, entry_id: str, request_id: str) -> None:
        if not isinstance(request_id, str) or not request_id.strip():
            raise BudgetError(
                "An empty request ID cannot be recovered after a restart."
            )

        def attach(entry: dict) -> None:
            if entry["state"] not in {"dispatching", "submitted"}:
                raise BudgetError("Only dispatched work can receive a request ID.")
            if entry["request_id"] not in (None, request_id):
                raise BudgetError(
                    "Keep the original request ID. Do not replace it on a 408."
                )
            entry["request_id"] = request_id
            entry["state"] = "submitted"

        self._update(entry_id, attach)

    def settle(self, entry_id: str, *, actual_usd: str, evidence: str) -> None:
        """Record a completed, reconciled cost. Unknown costs must remain held.

        Evidence names a saved usage or invoice record, not a predicted token
        count. If actual exceeds the declared maximum, future calls stop.
        """
        actual = money(actual_usd)
        if not isinstance(evidence, str) or not evidence.strip():
            raise BudgetError("Save billing evidence before settling a reservation.")

        def record(entry: dict) -> None:
            if entry["state"] == "void":
                raise BudgetError("Voided work cannot be settled.")
            if entry["state"] == "reserved":
                raise BudgetError(
                    "Work was never dispatched. Void the reservation instead."
                )
            if entry["state"] == "settled" and entry["actual_usd"] != str(actual):
                raise BudgetError(
                    "A settled cost changed. Stop and reconcile the billing evidence."
                )
            entry["state"] = "settled"
            entry["actual_usd"] = str(actual)
            entry["evidence"] = evidence

        self._update(entry_id, record)

    def void(self, entry_id: str, *, reason: str) -> None:
        """Release only work that was definitely never dispatched."""
        if not reason.strip():
            raise BudgetError(
                "Explain why the unsubmitted reservation is no longer needed."
            )

        def cancel(entry: dict) -> None:
            if entry["state"] != "reserved":
                raise BudgetError(
                    "Dispatched work may be billable. Keep its reservation."
                )
            entry["state"] = "void"
            entry["evidence"] = reason

        self._update(entry_id, cancel)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "check-run"])
    parser.add_argument("--ledger", default="ledger.json")
    parser.add_argument("--estimate-usd")
    parser.add_argument("--max-cost-usd")
    args = parser.parse_args()
    try:
        ledger = Ledger(args.ledger)
        if args.command == "status":
            print(json.dumps(ledger.status(), indent=2))
        else:
            if args.estimate_usd is None or args.max_cost_usd is None:
                parser.error("check-run needs --estimate-usd and --max-cost-usd")
            print(
                ledger.check_run(
                    estimate_usd=args.estimate_usd, max_cost_usd=args.max_cost_usd
                )
            )
    except BudgetError as exc:
        parser.exit(2, f"Budget error: {exc}\n")


if __name__ == "__main__":
    main()
