"""A bounded Boolean parser. Model text never becomes executable Python."""

from __future__ import annotations
from dataclasses import dataclass
import json
import re
import numpy as np


class ParseError(ValueError):
    pass


LEX = re.compile(r'\s*(==|[()]|"(?:[^"\\]|\\.)*"|[A-Za-z_][A-Za-z_0-9]*)')


@dataclass(frozen=True)
class Expr:
    kind: str
    value: str = ""
    children: tuple[Expr, ...] = ()

    def evaluate(
        self, attributes: tuple[str, ...], names: tuple[str, ...], rows: np.ndarray
    ) -> np.ndarray:
        values = {}
        stack = [(self, False)]
        while stack:
            node, ready = stack.pop()
            if not ready and node.children:
                stack.append((node, True))
                stack.extend((child, False) for child in reversed(node.children))
                continue
            if node.kind == "attribute":
                if node.value not in attributes:
                    raise ParseError(f"Unknown attribute: {node.value}")
                value = rows[:, attributes.index(node.value)].astype(bool)
            elif node.kind == "item":
                if node.value not in names:
                    raise ParseError(f"Unknown item: {node.value}")
                value = np.array([name == node.value for name in names])
            elif node.kind == "not":
                value = ~values[id(node.children[0])]
            else:
                a, b = (values[id(child)] for child in node.children)
                value = a & b if node.kind == "and" else a | b
            values[id(node)] = value
        return values[id(self)]

    @property
    def named_items(self) -> int:
        names, stack = set(), [self]
        while stack:
            node = stack.pop()
            if node.kind == "item":
                names.add(node.value)
            stack.extend(node.children)
        return len(names)


def lex(text: str) -> list[str]:
    if len(text) > 32768:
        raise ParseError("Expression exceeds the 32768-character parser limit.")
    tokens, position = [], 0
    while position < len(text.rstrip()):
        match = LEX.match(text, position)
        if match is None:
            raise ParseError(f"Unexpected text at character {position}.")
        tokens.append(match.group(1))
        position = match.end()
    if len(tokens) > 4096:
        raise ParseError("Expression exceeds the 4096-token parser limit.")
    return tokens


def parse(text: str) -> Expr:
    tokens = lex(text)
    position = 0

    def take(expected: str | None = None) -> str:
        nonlocal position
        if position >= len(tokens) or (
            expected is not None and tokens[position] != expected
        ):
            raise ParseError(f"Expected {expected or 'an expression'}.")
        value = tokens[position]
        position += 1
        return value

    def expression(precedence: int = 0, depth: int = 0) -> Expr:
        if depth > 64:
            raise ParseError("Expression nesting exceeds 64 levels.")
        token = take()
        if token == "NOT":
            left = Expr("not", children=(expression(3, depth + 1),))
        elif token == "(":
            left = expression(0, depth + 1)
            take(")")
        elif token == "item":
            take("==")
            name = take()
            if name in {"AND", "OR", "NOT", "(", ")", "=="}:
                raise ParseError("Expected an item name.")
            try:
                left = Expr("item", json.loads(name) if name.startswith('"') else name)
            except (ValueError, TypeError) as exc:
                raise ParseError("Malformed quoted item name.") from exc
        elif re.fullmatch(r"[a-z_][a-z_0-9]*", token) and token != "item":
            left = Expr("attribute", token)
        else:
            raise ParseError(
                "Expected an attribute, NOT, parentheses, or item equality."
            )
        while position < len(tokens) and tokens[position] in {"AND", "OR"}:
            operator = tokens[position]
            rank = 2 if operator == "AND" else 1
            if rank <= precedence:
                break
            take()
            right = expression(rank, depth + 1)
            left = Expr(operator.lower(), children=(left, right))
        return left

    if not tokens:
        raise ParseError("An empty expression is invalid.")
    result = expression()
    if position != len(tokens):
        raise ParseError("Unexpected trailing tokens.")
    return result
