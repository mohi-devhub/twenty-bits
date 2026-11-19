"""Transactional live ledger; the JSON file is an explicit audit export."""

from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3

SCHEMA = """
CREATE TABLE metadata(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
CREATE TABLE totals(id INTEGER PRIMARY KEY CHECK(id=1), spent INTEGER NOT NULL,
    held INTEGER NOT NULL, breached INTEGER NOT NULL, snapshot_sha256 TEXT NOT NULL);
CREATE TABLE entries(ordinal INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
    operation TEXT NOT NULL, state TEXT NOT NULL, data TEXT NOT NULL,
    spent INTEGER NOT NULL CHECK(spent>=0), held INTEGER NOT NULL CHECK(held>=0),
    breached INTEGER NOT NULL CHECK(breached IN (0,1)));
CREATE INDEX entry_operation ON entries(operation);
CREATE INDEX entry_state ON entries(state);
CREATE TABLE events(sequence INTEGER PRIMARY KEY, entry_id TEXT NOT NULL, data TEXT NOT NULL);
"""


def micros(value):
    return int(Decimal(value) * 1_000_000)


def amounts(entry):
    spent = micros(entry["actual_usd"]) if entry["state"] == "settled" else 0
    held = (
        micros(entry["reserved_usd"])
        if entry["state"] in {"reserved", "dispatching", "submitted"}
        else 0
    )
    breached = int(
        entry["state"] == "settled" and spent > micros(entry["max_cost_usd"])
    )
    return spent, held, breached


class SQLiteStore:
    def __init__(self, database, snapshot, error):
        self.path = Path(database)
        self.snapshot = Path(snapshot)
        self.error = error
        self.snapshot_stat = None
        if not self.path.is_file():
            raise error(
                "The live ledger database is missing. Do not rebuild from a stale JSON export."
            )

    @contextmanager
    def transaction(self):
        connection = None
        try:
            # mode=rw refuses to create an empty ledger after a deletion.
            connection = sqlite3.connect(
                self.path.as_uri() + "?mode=rw", uri=True, timeout=10
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            meta = json.loads(
                connection.execute("SELECT data FROM metadata WHERE id=1").fetchone()[0]
            )
            if meta["schema_version"] != 1 or not isinstance(meta["blocks"], list):
                raise self.error("Unsupported or corrupt live ledger schema.")
            if (
                meta["cap_usd"] != "50.000000"
                or meta["reservation_multiplier"] != "1.5"
            ):
                raise self.error(
                    "The approved $50 cap and 1.5 multiplier cannot be changed."
                )
            stat = self.snapshot.stat()
            signature = (
                stat.st_dev,
                stat.st_ino,
                stat.st_size,
                stat.st_mtime_ns,
                stat.st_ctime_ns,
            )
            if self.snapshot_stat != signature:
                digest = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()
                expected = connection.execute(
                    "SELECT snapshot_sha256 FROM totals WHERE id=1"
                ).fetchone()[0]
                if digest != expected:
                    raise self.error(
                        "The ledger export changed outside a transaction. Stop and reconcile it."
                    )
                self.snapshot_stat = signature
            yield connection, meta
            connection.commit()
        except (
            sqlite3.Error,
            OSError,
            json.JSONDecodeError,
            UnicodeError,
            KeyError,
            TypeError,
        ) as exc:
            raise self.error(
                "Missing or corrupt live ledger. Do not recreate it to resume spending."
            ) from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def totals(connection):
        row = connection.execute(
            "SELECT spent, held, breached FROM totals WHERE id=1"
        ).fetchone()
        return Decimal(row[0]) / 1_000_000, Decimal(row[1]) / 1_000_000, bool(row[2])

    @staticmethod
    def put(connection, entry, *, insert=False):
        body = json.dumps(entry, separators=(",", ":"), allow_nan=False)
        spent, held, breached = amounts(entry)
        if insert:
            connection.execute(
                "INSERT INTO entries(id, operation, state, data, spent, held, breached) VALUES(?,?,?,?,?,?,?)",
                (
                    entry["id"],
                    entry["operation"],
                    entry["state"],
                    body,
                    spent,
                    held,
                    breached,
                ),
            )
            old = (0, 0, 0)
        else:
            old = connection.execute(
                "SELECT spent, held, breached FROM entries WHERE id=?", (entry["id"],)
            ).fetchone()
            connection.execute(
                "UPDATE entries SET operation=?,state=?,data=?,spent=?,held=?,breached=? WHERE id=?",
                (
                    entry["operation"],
                    entry["state"],
                    body,
                    spent,
                    held,
                    breached,
                    entry["id"],
                ),
            )
        connection.execute(
            "UPDATE totals SET spent=spent+?,held=held+?,breached=breached+? WHERE id=1",
            (spent - old[0], held - old[1], breached - old[2]),
        )
        connection.execute(
            "INSERT INTO events(entry_id,data) VALUES(?,?)", (entry["id"], body)
        )

    @staticmethod
    def entries(connection, *, operation=None, operation_prefix=None, states=None):
        clauses, values = [], []
        if operation is not None:
            clauses.append("operation=?")
            values.append(operation)
        if operation_prefix:
            # The upper bound gives an indexed range and preserves startswith semantics.
            clauses.append("operation>=? AND operation<?")
            values.extend((operation_prefix, operation_prefix + chr(0x10FFFF)))
        if states is not None:
            states = sorted(states)
            if not states:
                return []
            clauses.append("state IN (" + ",".join("?" for _ in states) + ")")
            values.extend(states)
        query = (
            "SELECT data FROM entries"
            + (" WHERE " + " AND ".join(clauses) if clauses else "")
            + " ORDER BY ordinal"
        )
        return [json.loads(row[0]) for row in connection.execute(query, values)]

    @staticmethod
    def summary(connection, operation_prefix=None):
        if not operation_prefix:
            return SQLiteStore.totals(connection)[:2]
        row = connection.execute(
            "SELECT COALESCE(SUM(spent),0),COALESCE(SUM(held),0) FROM entries WHERE operation>=? AND operation<?",
            (operation_prefix, operation_prefix + chr(0x10FFFF)),
        ).fetchone()
        return Decimal(row[0]) / 1_000_000, Decimal(row[1]) / 1_000_000
