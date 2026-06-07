"""Human file size parsing and formatting helpers.

Vendored replacement for the abandoned `hfilesize` package (single release,
2014). Mirrors the exact semantics the validator relied on:
`FileSize(value, case_sensitive=False)` parsing (case-insensitive units,
binary base) and the `"{:.02fH}"` human formatting.
"""
import math

# unit -> power of 1024
_UNIT_EXPONENTS = {
    "": 0,
    "b": 0,
    "byte": 0,
    "bytes": 0,
}

for _exponent, _letter in enumerate("kmgtpezy", start=1):
    _UNIT_EXPONENTS[_letter] = _exponent
    _UNIT_EXPONENTS[f"{_letter}b"] = _exponent
    _UNIT_EXPONENTS[f"{_letter}ib"] = _exponent

for _exponent, _name in enumerate(
    ["kilo", "mega", "giga", "tera", "peta", "exa", "zetta", "yotta"], start=1
):
    _UNIT_EXPONENTS[f"{_name}byte"] = _exponent
    _UNIT_EXPONENTS[f"{_name}bytes"] = _exponent

for _exponent, _name in enumerate(
    ["kibi", "mebi", "gibi", "tebi", "pebi", "exbi", "zebi", "yobi"], start=1
):
    _UNIT_EXPONENTS[f"{_name}byte"] = _exponent
    _UNIT_EXPONENTS[f"{_name}bytes"] = _exponent

_SUFFIXES = [("byte", "bytes"), "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]


def parse_human_size(value):
    """Parse a humanized size like '2MB', '512 KiB' or an int into bytes.

    Units are case-insensitive and use the binary base (1024), matching the
    historical behavior of the size validation rule.
    """
    if isinstance(value, int):  # includes bool, matching the old behavior
        return int(value)
    if not isinstance(value, str):
        raise ValueError(f"Invalid file size: {value!r}")

    stripped = value.strip()
    index = len(stripped)
    while index and stripped[index - 1].isalpha():
        index -= 1
    size_part, unit_part = stripped[:index].strip(), stripped[index:]

    try:
        exponent = _UNIT_EXPONENTS[unit_part.lower()]
        return int(size_part) * 1024**exponent
    except (KeyError, ValueError):
        raise ValueError(f"Invalid file size: {value!r}")


def format_human_size(size, float_fmt=".2f"):
    """Format a byte count as a human string using the binary base.

    Examples: 0 -> '0 bytes', 1 -> '1 byte', 1536 -> '1.50 KB',
    2 * 1024**2 -> '2 MB'.
    """
    size = int(size)

    exponent = 0 if size <= 0 else int(math.log(size, 1024))
    exponent = min(max(exponent, 0), len(_SUFFIXES) - 1)

    suffix = _SUFFIXES[exponent]
    if isinstance(suffix, tuple):
        suffix = suffix[0] if size == 1024**exponent else suffix[1]

    if size % (1024**exponent) == 0:
        return f"{size // 1024 ** exponent} {suffix}"

    return f"{size / 1024 ** exponent:{float_fmt}} {suffix}"
