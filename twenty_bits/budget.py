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
import json
import os
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

    @contextmanager
    def _locked(self) -> Iterator[None]:
        with self.path.with_suffix(self.path.suffix + ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text())
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

    def status(self) -> dict:
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
            data = self._read()
            self._check_admission(data, reserved)
            entry_id = str(uuid.uuid4())
            data["entries"].append(
                {
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
            )
            self._write(data)
        return entry_id

    def _update(
        self, entry_id: str, edit: Callable[[dict], None], *, admit: bool = False
    ) -> None:
        with self._locked():
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
