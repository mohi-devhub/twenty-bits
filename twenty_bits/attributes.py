"""One exact column-code mapping for both table headers and predicates."""


def attribute_code(index: int) -> str:
    if index < 0:
        raise ValueError("Column indices must be nonnegative.")
    result = ""
    while True:
        result = chr(97 + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            return result


def attribute_aliases(attributes: tuple[str, ...]) -> dict[str, str]:
    aliases = {attribute_code(i): name for i, name in enumerate(attributes)}
    if any(code in attributes and code != name for code, name in aliases.items()):
        raise ValueError("A column code conflicts with another full attribute name.")
    return aliases
