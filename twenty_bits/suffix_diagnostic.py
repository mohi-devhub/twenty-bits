"""Explicitly auxiliary parser tolerance; never imported by a training runner."""

from collections import defaultdict
import re

from .attributes import attribute_aliases
from .game import Game


def suffix_aliases(attributes):
    primary = attribute_aliases(attributes)
    matches = defaultdict(list)
    for name in attributes:
        match = re.fullmatch(r"[A-Za-z]_(.+)", name)
        if match:
            matches[match[1]].append(name)
    extra = {}
    for suffix, names in matches.items():
        if len(names) != 1:
            continue
        for code in primary:
            identifier = code + "_" + suffix
            if identifier not in attributes and identifier not in primary:
                extra[identifier] = names[0]
    return extra


class DiagnosticAliases(dict):
    def __init__(self, primary, extra):
        super().__init__({**primary, **extra})
        self.extra = extra
        self.applied = []

    def get(self, key, default=None):
        value = super().get(key, default)
        if key in self.extra:
            self.applied.append({"identifier": key, "attribute": value})
        return value


class SuffixDiagnosticGame(Game):
    def __init__(self, record):
        if record["domain"] != "synthetic":
            raise ValueError(
                "Suffix tolerance is restricted to the synthetic diagnostic."
            )
        super().__init__(record, grammar_version="attribute-codes-v2")
        self.aliases = DiagnosticAliases(
            self.aliases, suffix_aliases(self.world.attributes)
        )

    def step(self, action, **kwargs):
        self.aliases.applied.clear()
        turn = super().step(action, **kwargs)
        turn["suffix_mappings"] = list(self.aliases.applied)
        turn["suffix_mapped_identifiers"] = len(self.aliases.applied)
        turn["diagnostic_only"] = True
        return turn

    def result(self):
        result = super().result()
        result.update(
            diagnostic_only=True,
            diagnostic_parser_version="suffix-tolerant-v1",
            mapped_identifiers=sum(t["suffix_mapped_identifiers"] for t in self.turns),
            mapped_questions=sum(bool(t["suffix_mappings"]) for t in self.turns),
        )
        return result
