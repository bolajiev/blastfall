"""npm semver range matching, minimal but faithful to the cases that matter.

Supported: exact, *, x/y wildcards, ^, ~, partial (1, 1.2, 1.2.x),
comparison sets (>=1.0.0 <2.0.0), hyphen ranges, and || unions.
Prerelease versions are excluded unless the range itself mentions a
prerelease (matching npm's default resolution behavior).
"""

import re

_RE_NUM = re.compile(r"^v?\d+(?:\.\d+)*")
_PART_RE = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(.*)$")


class Version:
    __slots__ = ("raw", "major", "minor", "patch", "pre")

    def __init__(self, raw):
        raw = raw.strip()
        if raw.startswith("v"):
            raw = raw[1:]
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?", raw)
        if not m:
            raise ValueError(f"not a version: {raw!r}")
        self.raw = raw
        self.major = int(m.group(1))
        self.minor = int(m.group(2))
        self.patch = int(m.group(3))
        self.pre = m.group(4) or ""

    @property
    def is_pre(self):
        return bool(self.pre)

    def key(self):
        if self.is_pre:
            pre_key = tuple(int(x) if x.isdigit() else x for x in self.pre.split("."))
            return (self.major, self.minor, self.patch, pre_key)
        return (self.major, self.minor, self.patch, ())

    def __lt__(self, other):
        return self.key() < other.key()

    def __le__(self, other):
        return self.key() <= other.key()

    def __str__(self):
        return self.raw


def _partial_bounds(parts):
    """Return (min, max) for partial version strings like '1', '1.2', '1.2.x'."""
    m = _PART_RE.match(parts)
    if not m:
        return None
    major = int(m.group(1))
    minor = m.group(2)
    patch = m.group(3)
    tail = m.group(4)
    if tail not in ("", ".x", ".X", ".*"):
        return None
    if minor is None:
        return (major, 0, 0), (major + 1, 0, 0)
    if patch is None or patch.lower() == "x" or patch == "*":
        return (major, int(minor), 0), (major, int(minor) + 1, 0)
    return (major, int(minor), int(patch)), (major, int(minor), int(patch) + 1)


def _cmp_pred(operator, ver):
    v = Version(ver)
    ops = {
        ">": lambda x: x > v,
        "<": lambda x: x < v,
        ">=": lambda x: x >= v,
        "<=": lambda x: x <= v,
        "=": lambda x: x == v,
    }
    return ops[operator]


def _compile_one(part):
    part = part.strip()
    if not part or part in ("*", "x", "X"):
        return lambda c: not c.is_pre
    if part.lower() == "latest":
        return lambda c: not c.is_pre
    m = re.match(r"^(>=|<=|>|<|=)?\s*(.+)$", part)
    operator, rest = m.group(1) or "=", m.group(2)
    if operator != "=":
        return _cmp_pred(operator, rest)
    if " - " in part:
        lo_s, hi_s = part.split(" - ", 1)
        lo = Version(lo_s.strip())
        hi = Version(hi_s.strip())
        return lambda c: (not c.is_pre) and lo <= c <= hi
    if part.startswith("^"):
        v = Version(part[1:])
        if v.major > 0:
            return lambda c: (not c.is_pre) and v <= c < Version(f"{v.major + 1}.0.0")
        if v.minor > 0:
            return lambda c: (not c.is_pre) and v <= c < Version(f"0.{v.minor + 1}.0")
        return lambda c: (not c.is_pre) and c == v
    if part.startswith("~"):
        v = Version(part[1:])
        return lambda c: (not c.is_pre) and v <= c < Version(f"{v.major}.{v.minor + 1}.0")
    bounds = _partial_bounds(part)
    if bounds:
        (a, b, c), (d, e, f) = bounds
        lo = Version(f"{a}.{b}.{c}")
        hi = Version(f"{d}.{e}.{f}")
        return lambda x: (not x.is_pre) and lo <= x < hi
    try:
        v = Version(part)
    except ValueError:
        return lambda c: not c.is_pre
    return lambda c: (not c.is_pre) and c == v


def compile_range(requirement):
    """Compile an npm range string into a predicate(Version) -> bool."""
    if requirement is None:
        return lambda c: not c.is_pre
    requirement = requirement.strip().replace(" ", " ").lower()
    if not requirement:
        return lambda c: not c.is_pre
    alternatives = [a for a in requirement.split("||") if a.strip()]
    compiled = [_compile_one(a) for a in alternatives]
    return lambda c: any(pred(c) for pred in compiled)


def resolves(requirement, candidate):
    """True if `candidate` (a version string) satisfies the npm range."""
    try:
        return compile_range(requirement)(Version(candidate))
    except ValueError:
        return False
