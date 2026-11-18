"""Carry unresolved-original identities across serial run boundaries."""

import json

from .tinker_transport import save_json
from .worlds import ROOT


def refresh_legacy_ids(path):
    current = json.loads(path.read_text())
    ids = set(current["legacy_lost_entry_ids"])
    for source in (ROOT / "research").glob("*_replacements.json"):
        registry = json.loads(source.read_text())
        ids.update(registry.get("legacy_lost_entry_ids", []))
        ids.update(c["original_entry_id"] for c in registry.get("cases", []))
    current["legacy_lost_entry_ids"] = sorted(ids)
    save_json(path, current)
