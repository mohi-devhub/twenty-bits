"""One exact sampling replacement, with retained holds and durable exclusions."""

from decimal import Decimal
import hashlib
import json

import tinker

from .budget import ACTIVE_STATES, BudgetError, now
from .rl_pilot import PilotTransport
from .tinker_transport import NetworkInterruption, save_json
from .worlds import ROOT


class ReplacementApprovalRequired(BudgetError):
    pass


class RecoveringTransport(PilotTransport):
    def __init__(self, *args, registry_path=None, policy_path=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry_path = (
            registry_path or ROOT / "research/main_A11_replacements.json"
        )
        self.policy_path = policy_path or ROOT / "research/replacement_policy.json"
        self.registry = json.loads(self.registry_path.read_text())
        self.replacements.update(
            {
                c["logical_key"]: c["replacement_key"]
                for c in self.registry["cases"]
                if not c.get("requires_approval")
            }
        )

    def original_holds(self, extra_id=None):
        ids = set(self.registry["legacy_lost_entry_ids"])
        ids.update(c["original_entry_id"] for c in self.registry["cases"])
        if extra_id:
            ids.add(extra_id)
        return sum(
            (
                Decimal(e["reserved_usd"])
                for e in self.ledger.status()["entries"]
                if e["id"] in ids and e["state"] in ACTIVE_STATES
            ),
            Decimal(0),
        )

    def check_approval(self):
        policy = json.loads(self.policy_path.read_text())
        if not policy["authorized"] or self.original_holds() >= Decimal(
            policy["aggregate_unresolved_lost_original_holds_must_be_below_usd"]
        ):
            raise ReplacementApprovalRequired(
                "Lost-original holds reached the standing replacement limit; approval is required."
            )
        if any(c.get("requires_approval") for c in self.registry["cases"]):
            raise ReplacementApprovalRequired(
                "A replacement was lost or is outside the standing rule; approval is required."
            )

    async def open(self, **kwargs):
        await super().open(**kwargs)
        self.check_approval()

    async def free(self, operation, send, *, pending_ok=False):
        try:
            return await super().free(operation, send, pending_ok=pending_ok)
        except tinker.APIStatusError as exc:
            if exc.status_code == 429 or exc.status_code >= 500:
                if pending_ok:
                    return {"type": "try_again", "http_status": exc.status_code}
                self.failed = True
                raise NetworkInterruption(
                    "Transient metadata failure; drain and recover original IDs before new work."
                ) from exc
            raise

    def record_loss(self, journal, path, reason):
        self.failed = True
        case = next(
            (
                c
                for c in self.registry["cases"]
                if journal["key"] in (c["logical_key"], c["replacement_key"])
            ),
            None,
        )
        if case and journal["key"] == case["replacement_key"]:
            case.update(
                requires_approval=True,
                second_lost_entry_id=journal["entry_id"],
                second_lost_request_id=journal["request_id"],
                second_loss_observed_at=now(),
            )
            save_json(self.registry_path, self.registry)
            self.ledger._update(
                journal["entry_id"],
                lambda e: e.update(
                    evidence=f"Second loss of logical request; approval required; {self.registry_path}"
                ),
            )
            raise ReplacementApprovalRequired(
                "Second loss of the same logical sampling request. Its hold remains; no additional replacement is authorized."
            )
        if case is None:
            case = {
                "logical_key": journal["key"],
                "original_entry_id": journal["entry_id"],
                "original_request_id": journal["request_id"],
                "signature": journal["signature"],
                "replacement_key": journal["key"] + "/approved-replacement-v1",
                "loss_observed_at": now(),
                "loss_reason": reason,
                "replacements_used": 0,
            }
            self.registry["cases"].append(case)
        policy = json.loads(self.policy_path.read_text())
        case["requires_approval"] = not policy["authorized"] or self.original_holds(
            journal["entry_id"]
        ) >= Decimal(
            policy["aggregate_unresolved_lost_original_holds_must_be_below_usd"]
        )
        save_json(self.registry_path, self.registry)
        journal.update(
            orphaned=True,
            output_allowed=False,
            loss_status=reason,
            replacement_authorized=not case["requires_approval"],
        )
        save_json(path, journal)
        self.ledger._update(
            journal["entry_id"],
            lambda e: e.update(
                evidence=f"orphaned, possibly billed; outputs permanently excluded; {self.registry_path}",
                original_lost_request=True,
                output_allowed=False,
                replacement_authorized=not case["requires_approval"],
            ),
        )
        if case["requires_approval"]:
            raise ReplacementApprovalRequired(
                "Unresolved original holds reached $0.50. Approval required before replacement."
            )
        self.replacements[case["logical_key"]] = case["replacement_key"]
        raise NetworkInterruption(
            "Lost sampling result excluded under the standing rule; drain every active operation before its one exact replacement."
        )

    async def collect(self, journal, path):
        if journal.get("orphaned") or journal.get("output_allowed") is False:
            raise BudgetError(
                "An excluded original can never provide an action or score."
            )
        try:
            return await super().collect(journal, path)
        except tinker.APIStatusError as exc:
            if (
                exc.status_code in (404, 410)
                or "expired" in str(getattr(exc, "body", "")).lower()
            ):
                self.record_loss(
                    journal, path, f"HTTP {exc.status_code}: unavailable saved future"
                )
            raise
        except RuntimeError:
            failure = (
                self.directory
                / "future_failures"
                / (hashlib.sha256(journal["request_id"].encode()).hexdigest() + ".json")
            )
            if failure.exists() and not journal.get("settled"):
                self.record_loss(
                    journal,
                    path,
                    "Server future failed without usable output; original response is quarantined.",
                )
            raise
        except (KeyError, IndexError, TypeError):
            response = journal.get("response", {})
            if not journal.get("settled") and not response.get("sequences"):
                self.record_loss(
                    journal,
                    path,
                    "Transport response has no usable sequences; this is not a model format error.",
                )
            raise

    async def sample(self, *, model, key, prompt, params):
        case = next(
            (c for c in self.registry["cases"] if c["logical_key"] == key), None
        )
        if case:
            self.check_approval()
            saved = (
                self.directory
                / "requests"
                / (
                    hashlib.sha256(case["replacement_key"].encode()).hexdigest()
                    + ".json"
                )
            )
            if case.get("replacements_used", 0) and not saved.exists():
                raise ReplacementApprovalRequired(
                    "The authorized replacement was already attempted and its journal is missing. Approval required; do not submit another attempt."
                )
        elif any(c.get("requires_approval") for c in self.registry["cases"]):
            raise ReplacementApprovalRequired(
                "A lost replacement requires approval before new work."
            )
        if case:
            signature = hashlib.sha256(
                json.dumps(
                    {
                        "model": model,
                        "prompt_ids": prompt.to_ints(),
                        "sampling_params": params.model_dump(mode="json"),
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            if signature != case["signature"]:
                raise BudgetError(
                    "Replacement prompt, seed or settings differ from the original; no request submitted."
                )
        try:
            return await super().sample(
                model=model, key=key, prompt=prompt, params=params
            )
        finally:
            if case:
                path = (
                    self.directory
                    / "requests"
                    / (
                        hashlib.sha256(case["replacement_key"].encode()).hexdigest()
                        + ".json"
                    )
                )
                if path.exists():
                    r = json.loads(path.read_text())
                    case.update(
                        replacements_used=1,
                        replacement_entry_id=r["entry_id"],
                        replacement_request_id=r["request_id"],
                    )
                    save_json(self.registry_path, self.registry)
                    self.ledger._update(
                        case["original_entry_id"],
                        lambda e: e.update(
                            replacement_submitted=True,
                            replacement_entry_id=r["entry_id"],
                            replacement_request_id=r["request_id"],
                        ),
                    )
