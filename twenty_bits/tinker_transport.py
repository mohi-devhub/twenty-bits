"""Durable, budgeted Tinker requests. A pending future is never submitted again.

The low-level SDK exposes a submission receipt before waiting for a result.
That lets us save its request_id and recover it after a process restart.
Cookbook renderers and rollout interfaces sit above this transport.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shlex
import tempfile

import tinker
from tinker import types
from tinker._client import AsyncTinker

from .budget import ACTIVE_STATES, MULTIPLIER, BudgetError, Ledger, money, now
from .worlds import ROOT


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
        temporary = f.name
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def load_credentials() -> None:
    """Read ignored local configuration as data, without shell execution."""
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            key, separator, value = line.removeprefix("export ").partition("=")
            key = key.strip()
            if separator and key in {"TINKER_API_KEY", "TINKER_PROJECT_ID"}:
                parts = shlex.split(value, comments=True)
                if len(parts) != 1:
                    raise ValueError("Malformed local Tinker configuration.")
                os.environ.setdefault(key, parts[0])
    if (
        not os.environ.get("TINKER_API_KEY")
        and not (Path.home() / ".tinker/credentials.json").exists()
    ):
        raise RuntimeError("Configure a local Tinker credential before running.")


def rates(model: str) -> dict[str, Decimal]:
    rows = json.loads((ROOT / "research/tinker-models-2026-11-17.json").read_text())
    row = next(r for r in rows if r["tinker_id"] == model)
    return {
        k: Decimal(row[k].removeprefix("$"))
        for k in ("prefill", "cached_prefill", "sample", "train")
    }


def sample_cost(model: str, prompt: int, output: int, cached: int = 0) -> str:
    if not 0 <= cached <= prompt or output < 0:
        raise ValueError("Invalid observed token usage.")
    r = rates(model)
    return str(
        money(
            (
                (prompt - cached) * r["prefill"]
                + cached * r["cached_prefill"]
                + output * r["sample"]
            )
            / Decimal(1_000_000)
        )
    )


class NetworkInterruption(BudgetError):
    """Pause producers, drain HTTP tasks, then reconnect and collect futures."""


class GuardedTinker:
    def __init__(
        self,
        config: dict,
        directory: Path,
        *,
        ledger: Ledger | None = None,
        usage_path: Path | None = None,
        run_cap_usd: str | None = None,
        approved_replacements: dict[str, str] | None = None,
    ):
        self.config = config
        self.directory = directory
        self.ledger = ledger or Ledger(ROOT / "ledger.json")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state_path = directory / "sessions.json"
        self.state = (
            json.loads(self.state_path.read_text())
            if self.state_path.exists()
            else {
                "session_id": None,
                "samplers": {},
                "next_sampler": 0,
                "finished": False,
            }
        )
        self.usage_path = usage_path or ROOT / "results/phase2/usage.jsonl"
        self.run_cap = money(run_cap_usd) if run_cap_usd is not None else None
        self.operation_prefix = (
            f"[{config['run_id']}] " if self.run_cap is not None else ""
        )
        self.usage_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.sampler_lock = asyncio.Lock()
        self.failed = False
        incident_path = ROOT / "research/phase2_incident.json"
        self.replacements = (
            json.loads(incident_path.read_text()).get("approved_replacements", {})
            if incident_path.exists()
            else {}
        )
        self.replacements.update(approved_replacements or {})

    def evidence(self, entry_id: str, row: dict) -> str:
        row = {"entry_id": entry_id, "recorded_at": now(), **row}
        with self.usage_path.open("a") as f:
            f.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        path = (
            self.usage_path.relative_to(ROOT)
            if self.usage_path.is_relative_to(ROOT)
            else self.usage_path
        )
        return f"{path}#{entry_id}"

    def run_status(self) -> dict:
        entries = [
            e
            for e in self.ledger.status()["entries"]
            if e["operation"].startswith(self.operation_prefix)
        ]
        spent = sum(
            (money(e["actual_usd"]) for e in entries if e["state"] == "settled"),
            Decimal(0),
        )
        held = sum(
            (money(e["reserved_usd"]) for e in entries if e["state"] in ACTIVE_STATES),
            Decimal(0),
        )
        return {"spent_usd": str(spent), "held_usd": str(held)}

    def call(self, send, *, operation, estimate_usd, max_cost_usd):
        # The runner lock permits one coordinator. No await separates this
        # admission check from the existing, atomic project-ledger reservation.
        if self.run_cap is not None:
            status = self.run_status()
            extra = max(money(money(estimate_usd) * MULTIPLIER), money(max_cost_usd))
            if (
                money(status["spent_usd"]) + money(status["held_usd"]) + extra
                > self.run_cap
            ):
                raise BudgetError(
                    f"The run's ${self.run_cap} limit, including active holds, would be exceeded."
                )
        return self.ledger.call(
            send,
            phase=self.config.get("ledger_phase", 2),
            operation=self.operation_prefix + operation,
            estimate_usd=estimate_usd,
            max_cost_usd=max_cost_usd,
        )

    async def free(
        self, operation: str, send: Callable[[], Awaitable], *, pending_ok=False
    ):
        entry_id, task = self.call(
            lambda: asyncio.create_task(send()),
            operation=operation,
            estimate_usd="0",
            max_cost_usd="0",
        )
        try:
            result = await task
            if hasattr(result, "model_dump"):
                result = result.model_dump(mode="json", warnings=False)
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            evidence = self.evidence(
                entry_id,
                {
                    "operation": operation,
                    "actual_usd": "0.000000",
                    "error_type": type(exc).__name__,
                    "http_status": status,
                    "billing_basis": "Non-billable metadata or future retrieval",
                },
            )
            self.ledger.settle(entry_id, actual_usd="0", evidence=evidence)
            if self.run_cap is not None and isinstance(exc, tinker.APIConnectionError):
                self.failed = True
                raise NetworkInterruption(
                    "Reconnect and collect pending futures before new sampling."
                ) from exc
            if pending_ok and (
                status == 408
                or status in (429, 500, 502, 503, 504)
                or isinstance(exc, tinker.APIConnectionError)
            ):
                return {"type": "try_again", "http_status": status}
            raise
        evidence = self.evidence(
            entry_id,
            {
                "operation": operation,
                "actual_usd": "0.000000",
                "billing_basis": "Non-billable metadata or future retrieval",
                "pending": isinstance(result, dict)
                and result.get("type") == "try_again",
            },
        )
        self.ledger.settle(entry_id, actual_usd="0", evidence=evidence)
        return result

    async def open(self, *, recover_pending=False):
        load_credentials()
        entry, self.client = self.call(
            lambda: AsyncTinker(
                max_retries=0,
                timeout=45,
                default_headers={
                    "x-sdk-version": tinker.__version__,
                    "x-sdk-method": "TwentyBits.GuardedTinker",
                },
            ),
            operation="construct low-level SDK client",
            estimate_usd="0",
            max_cost_usd="0",
        )
        self.ledger.settle(
            entry,
            actual_usd="0",
            evidence=self.evidence(
                entry,
                {
                    "operation": "construct low-level SDK client",
                    "actual_usd": "0.000000",
                    "network": False,
                },
            ),
        )
        if recover_pending:
            await self.collect_pending()
        capabilities = await self.free(
            "server capabilities", self.client.service.get_server_capabilities
        )
        save_json(self.directory / "capabilities.json", capabilities)
        models = {r["model_name"]: r for r in capabilities["supported_models"]}
        for model in self.config.get(
            "active_models",
            (self.config["primary_model"], self.config["reference_model"]),
        ):
            if model not in models or models[model].get("sampleable") is False:
                raise RuntimeError(f"Approved model is unavailable: {model}")
        if self.state["finished"]:
            raise RuntimeError(
                "This session was finished. Completed samples may be read offline."
            )
        if self.state["session_id"] is None:
            result = await self.free(
                "create Phase 2 session",
                lambda: self.client.service.create_session(
                    request=types.CreateSessionRequest(
                        tags=["twenty-bits", "phase2"],
                        user_metadata={
                            "project": "twenty-bits",
                            "phase": "2",
                            "run": self.config["run_id"],
                        },
                        sdk_version=tinker.__version__,
                        project_id=os.environ.get("TINKER_PROJECT_ID"),
                        display_name=self.config.get(
                            "display_name", "Twenty Bits base evaluation"
                        ),
                    )
                ),
            )
            self.state["session_id"] = result["session_id"]
            save_json(self.state_path, self.state)

    async def heartbeat(self, stop_event: asyncio.Event | None = None):
        while True:
            if stop_event is None:
                await asyncio.sleep(30)
            else:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=30)
                    return
                except TimeoutError:
                    pass
            await self.free(
                "session heartbeat",
                lambda: self.client.service.session_heartbeat(
                    session_id=self.state["session_id"],
                    timeout=40,
                    max_retries=0,
                ),
                pending_ok=stop_event is not None,
            )

    async def sampler(self, model: str):
        async with self.sampler_lock:
            return await self._sampler(model)

    async def _sampler(self, model: str):
        if model not in self.state["samplers"]:
            seq = self.state["next_sampler"]
            self.state["next_sampler"] += 1
            save_json(self.state_path, self.state)
            result = await self.free(
                f"create sampler {model}",
                lambda: self.client.service.create_sampling_session(
                    request=types.CreateSamplingSessionRequest(
                        session_id=self.state["session_id"],
                        sampling_session_seq_id=seq,
                        base_model=model,
                        model_path=self.config.get("sampling_checkpoint_paths", {}).get(
                            model
                        ),
                    )
                ),
            )
            self.state["samplers"][model] = {
                "id": result["sampling_session_id"],
                "next_seq": 0,
            }
            checkpoint = self.config.get("sampling_checkpoint_paths", {}).get(model)
            if checkpoint:
                self.state["samplers"][model]["model_path"] = checkpoint
            save_json(self.state_path, self.state)
        return self.state["samplers"][model]

    async def poll(self, request_id: str) -> dict:
        while True:

            async def retrieve():
                response = await self.client.futures.with_raw_response.retrieve(
                    request=types.FutureRetrieveRequest(
                        request_id=request_id, allow_metadata_only=False
                    ),
                    timeout=45,
                    max_retries=0,
                    extra_headers={"Accept": "application/json"},
                )
                return await response.json()

            result = await self.free(
                f"retrieve {request_id}", retrieve, pending_ok=True
            )
            if result.get("type") == "try_again":
                await asyncio.sleep(1)
                continue
            if "error" in result or result.get("type") == "request_failed":
                save_json(
                    self.directory
                    / "future_failures"
                    / (hashlib.sha256(request_id.encode()).hexdigest() + ".json"),
                    {
                        "request_id": request_id,
                        "observed_at": now(),
                        "response": result,
                    },
                )
                raise RuntimeError(
                    "Tinker future failed; its sample hold remains for reconciliation."
                )
            return result

    async def collect_pending(self):
        """Collect every saved recoverable request before permitting producers."""
        pending = []
        for path in sorted((self.directory / "requests").glob("*.json")):
            journal = json.loads(path.read_text())
            if (
                journal.get("settled")
                or journal.get("orphaned")
                or journal.get("output_allowed") is False
            ):
                continue
            if not journal.get("request_id") and not journal.get("receipt"):
                raise BudgetError(
                    "An uncertain request has no recovery ID. Keep its hold."
                )
            pending.append((path, journal))
        # One failed future must not prevent the others from being retrieved.
        results = await asyncio.gather(
            *(self.collect(journal, path) for path, journal in pending),
            return_exceptions=True,
        )
        report = {
            "observed_at": now(),
            "pending_requests": [j.get("request_id") for _, j in pending],
            "collected": sum(not isinstance(r, BaseException) for r in results),
            "errors": [
                {
                    "request_id": pending[i][1].get("request_id"),
                    "type": type(r).__name__,
                }
                for i, r in enumerate(results)
                if isinstance(r, BaseException)
            ],
            "new_submissions": 0,
        }
        save_json(self.directory / "latest_collection.json", report)
        failures = [r for r in results if isinstance(r, BaseException)]
        if failures:
            self.failed = True
            network = next(
                (r for r in failures if isinstance(r, NetworkInterruption)), None
            )
            raise network or failures[0]

    async def sample(self, *, model: str, key: str, prompt, params) -> dict:
        if self.failed:
            raise BudgetError(
                "An adapter error stopped new sampling. Recover saved requests before resuming."
            )
        key = self.replacements.get(key, key)
        payload = {
            "model": model,
            "prompt_ids": prompt.to_ints(),
            "sampling_params": params.model_dump(mode="json"),
        }
        signature = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        path = (
            self.directory
            / "requests"
            / (hashlib.sha256(key.encode()).hexdigest() + ".json")
        )
        if path.exists():
            journal = json.loads(path.read_text())
            if journal.get("orphaned"):
                raise BudgetError("Orphaned output is excluded permanently.")
            if journal["signature"] != signature:
                raise RuntimeError("A resumed sample changed its prompt or settings.")
            if journal.get("settled"):
                return journal
            entry_id = journal["entry_id"]
            if journal.get("rejected"):
                raise BudgetError("This rejected attempt needs a reviewed replacement.")
            if not journal.get("receipt") and not journal.get("request_id"):
                raise BudgetError(
                    "Dispatched sample has no saved receipt. Retain its hold; do not resubmit."
                )
        else:
            sampler = await self.sampler(model)
            sequence = sampler["next_seq"]
            sampler["next_seq"] += 1
            save_json(self.state_path, self.state)
            estimate = sample_cost(model, prompt.length, min(64, params.max_tokens))
            maximum = sample_cost(model, prompt.length, params.max_tokens)
            journal = {
                "key": key,
                "signature": signature,
                "model": model,
                "prompt_tokens": prompt.length,
                "max_tokens": params.max_tokens,
                "parameters": payload["sampling_params"],
                "sampler_seq": sequence,
                "request_id": f"{sampler['id']}:{sequence}",
                "request_id_saved_before_dispatch": True,
            }

            operation = f"sample {model} {key}"

            def submit():
                matching = [
                    e["id"]
                    for e in self.ledger.status()["entries"]
                    if e["operation"] == self.operation_prefix + operation
                    and e["state"] == "dispatching"
                ]
                if len(matching) != 1:
                    raise BudgetError(
                        "Sample dispatch does not have one unique reservation."
                    )
                journal["entry_id"] = matching[0]
                journal["saved_before_dispatch_at"] = now()
                save_json(path, journal)
                self.ledger.attach_request_id(
                    journal["entry_id"], journal["request_id"]
                )
                return asyncio.create_task(
                    self.client.sampling.asample(
                        request=types.SampleRequest(
                            prompt=prompt,
                            num_samples=1,
                            sampling_params=params,
                            sampling_session_id=sampler["id"],
                            seq_id=sequence,
                            prompt_logprobs=False,
                            record_stability_info=False,
                        ),
                        max_retries=0,
                        extra_headers={"X-Tinker-Sampling-Backpressure": "1"},
                    )
                )

            if self.failed:
                raise BudgetError(
                    "New sampling is paused until pending requests are collected."
                )
            entry_id, task = self.call(
                submit,
                operation=operation,
                estimate_usd=estimate,
                max_cost_usd=maximum,
            )
            try:
                receipt = await task
            except Exception as exc:
                self.failed = True
                journal["submission_error"] = {
                    "type": type(exc).__name__,
                    "http_status": getattr(exc, "status_code", None),
                }
                if isinstance(exc, tinker.APIStatusError) and exc.status_code == 422:
                    journal["submission_error"]["detail"] = (
                        exc.body.get("detail") if isinstance(exc.body, dict) else None
                    )
                    evidence = self.evidence(
                        entry_id,
                        {
                            "operation": "rejected sample",
                            "key": key,
                            "actual_usd": "0.000000",
                            "http_status": 422,
                            "detail": journal["submission_error"]["detail"],
                            "billing_basis": "HTTP validation rejection before a future was created",
                        },
                    )
                    self.ledger.settle(entry_id, actual_usd="0", evidence=evidence)
                    journal["rejected"] = True
                save_json(path, journal)
                if self.run_cap is not None and isinstance(
                    exc, tinker.APIConnectionError
                ):
                    raise NetworkInterruption(
                        "Sampling connection interrupted; recover its saved ID before new work."
                    ) from exc
                raise
            journal["receipt"] = receipt.model_dump(mode="json")
            save_json(path, journal)
            if receipt.request_id != journal["request_id"]:
                self.failed = True
                raise BudgetError(
                    "Server receipt differs from the saved deterministic request ID."
                )
        return await self.collect(journal, path)

    async def collect(self, journal: dict, path: Path) -> dict:
        entry_id = journal["entry_id"]
        model = journal["model"]
        request_id = journal.get("request_id") or journal["receipt"]["request_id"]
        entry = next(e for e in self.ledger.status()["entries"] if e["id"] == entry_id)
        if entry["state"] != "settled":
            self.ledger.attach_request_id(entry_id, request_id)
        if "response" not in journal:
            journal.setdefault("collection_started_at", now())
            save_json(path, journal)
            journal["response"] = await self.poll(request_id)
            journal["response_received_at"] = now()
            save_json(path, journal)
        if not journal.get("receipt"):
            journal["receipt"] = {
                "request_id": request_id,
                "recovered_without_receipt": True,
            }
        response = journal["response"]
        sequences = response["sequences"]
        if len(sequences) != 1 or "prompt_cache_hit_tokens" not in response:
            raise ValueError("Unexpected sample usage response. Hold retained.")
        count = len(sequences[0]["tokens"])
        if count > journal["max_tokens"]:
            raise ValueError("Server exceeded the declared output cap. Hold retained.")
        cached = response["prompt_cache_hit_tokens"]
        actual = sample_cost(model, journal["prompt_tokens"], count, cached)
        journal.update(
            output_tokens=count, prompt_cache_hit_tokens=cached, actual_usd=actual
        )
        if entry["state"] == "settled":
            if entry["actual_usd"] != actual:
                raise BudgetError(
                    "Saved response usage disagrees with its settled ledger cost."
                )
            journal["settled"] = True
            save_json(path, journal)
            return journal
        evidence = self.evidence(
            entry_id,
            {
                "operation": "sample",
                "key": journal["key"],
                "model": model,
                "request_id": request_id,
                "prompt_tokens": journal["prompt_tokens"],
                "output_tokens": count,
                "prompt_cache_hit_tokens": cached,
                "actual_usd": actual,
                "billing_basis": "Observed response tokens and published token rates, rounded upward per call; invoice reconciliation pending",
                "rates_usd_per_million": {k: str(v) for k, v in rates(model).items()},
            },
        )
        self.ledger.settle(entry_id, actual_usd=actual, evidence=evidence)
        journal["settled"] = True
        save_json(path, journal)
        return journal

    async def finish(self):
        await self.free(
            "finish Phase 2 session",
            lambda: self.client.post(
                f"/api/v1/sessions/{self.state['session_id']}/finish",
                body={
                    "reason": {"type": "success"},
                    "detail": "Phase 2 evaluation complete",
                },
                cast_to=type(None),
            ),
        )
        self.state["finished"] = True
        save_json(self.state_path, self.state)

    async def close(self):
        if self.client is not None:
            await self.free("close SDK transport", self.client.close)
