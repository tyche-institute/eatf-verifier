"""The declared-target rule: a deterministic function of the block and the checks.

Every constant of the rule lives in this module. RULE_VERSION changes when
any of them changes.

The rule reads, for one included block: the expected exception classes, the
block's `match` pattern, the assertions on the bound exception after the
block, and the name of the test. It never reads a run.

Steps, in this order:

1. C_class: the reachable checks whose class is, or inherits from, an
   expected class. Empty: no target.
2. Each assertion of the block gives each candidate one of 3 verdicts: `no`
   (the assertion cannot hold on an exception this check raises), `yes` (a
   literal part of the check's message, or a literal argument, satisfies it)
   or `maybe`. C_assert: the candidates without a `no`. Empty: no target.
3. C_class has 1 check: that check, basis `class`.
4. C_assert has 1 check: that check, basis `assert`.
5. C_pos: the checks of C_assert with at least 1 `yes`. 1 check: that check,
   basis `assert-literal`.
6. The name of the test breaks the tie, over C_pos when it has 2 or more
   checks and over C_assert otherwise: the check with the single highest
   score, basis `assert+name` when the pool is smaller than C_class and
   `name` otherwise. No single highest score above 0: no target.

Bases `class`, `assert` and `assert-literal` form the assertion tier; bases
`assert+name` and `name` form the name tier.
"""

from __future__ import annotations

import math
import re

from .checks import ancestors, is_subclass

RULE_VERSION = "reach-target-rule/2"

STOP = frozenset("""test tests should raise raises raised throw throws error errors exception
exceptions fail fails failure reject rejects rejected when if with on for of in to the a an and
or is are be that it as by at""".split())
MIN_LEN = 2          # tokens shorter than this are dropped
STRIP_S_ABOVE = 3    # a final "s" is stripped from tokens longer than this
SCORE_DIGITS = 9     # scores are compared after rounding to this many decimals
TOP = 3              # how many scores targets.json keeps
PROBE = "\x00"       # stands for a placeholder when a pattern is tried on a template

ASSERTION_TIER = ("class", "assert", "assert-literal")
NAME_TIER = ("assert+name", "name")

YES, NO, MAYBE = "yes", "no", "maybe"

_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")
_SPLIT = re.compile(r"[^A-Za-z0-9]+")
_WORD = re.compile(r"\w")


def tokens(text: str) -> list[str]:
    out = []
    for piece in _SPLIT.split(text or ""):
        for t in _CAMEL.split(piece):
            t = t.lower()
            if len(t) < MIN_LEN:
                continue
            if len(t) > STRIP_S_ABOVE and t.endswith("s"):
                t = t[:-1]
            if t in STOP:
                continue
            out.append(t)
    return out


def descriptor(check: dict) -> set[str]:
    out: set[str] = set()
    for part in check["template_parts"]:
        if part is not None:
            out |= set(tokens(part))
    out |= set(tokens(check.get("class_name") or check["class"] or ""))
    for w in check["guard_words"]:
        out |= set(tokens(w))
    for w in check["other_literals"]:
        out |= set(tokens(w))
    out |= set(tokens(check["function_name"]))
    return out


def name_tokens(test_name: str) -> set[str]:
    return set(tokens(test_name))


# -- the assertion step ------------------------------------------------------------

def shape_known(check: dict, classes: dict) -> bool:
    """True when str() of the raised exception is taken to be the text of its
    message argument: no raise call of the check passes a keyword argument,
    none passes more than 1 positional argument (a call without arguments,
    and `raise Class` without a call, pass), and no class in `ancestors()` of the
    check's class defines __str__ or __init__. `ancestors()` holds the class
    itself and every ancestor that `classes` knows, up to the top of the known
    hierarchy and not only up to the rejection base; a class that `classes`
    does not hold (a built-in or external class) is not inspected."""
    if check["has_keywords"]:
        return False
    if any(n > 1 for n in check["n_positional"]):
        return False
    for name in ancestors(check["class"], classes):
        defines = classes.get(name, {}).get("defines", [])
        if "__str__" in defines or "__init__" in defines:
            return False
    return True


def text_known(check: dict, classes: dict) -> bool:
    """The whole text is known: the shape is known and there is no placeholder."""
    return shape_known(check, classes) and not check["has_placeholder"]


def template_pattern(parts: list) -> re.Pattern:
    return re.compile("".join(".*" if p is None else re.escape(p) for p in parts), re.S)


def text_verdict(check: dict, kind: str, value: str, classes: dict) -> str:
    """Verdict of one assertion on the message text: `str_eq`, `str_in` or `match`."""
    if not shape_known(check, classes):
        return MAYBE
    parts = check["template_parts"]
    literal = [p for p in parts if p is not None]
    open_text = len(literal) != len(parts)
    whole = "".join(literal)
    if kind == "str_eq":
        if template_pattern(parts).fullmatch(value) is None:
            return NO
        if not open_text:
            return YES
        return YES if any(_WORD.search(p) for p in literal) else MAYBE
    if kind == "str_in":
        if not open_text:
            return YES if value in whole else NO
        return YES if _WORD.search(value) and any(value in p for p in literal) else MAYBE
    if kind == "match":
        try:
            pattern = re.compile(value)
        except re.error:
            return MAYBE
        if not open_text:
            return YES if pattern.search(whole) else NO
        probe = "".join(PROBE if p is None else p for p in parts)
        return YES if pattern.search(probe) and not pattern.search(PROBE) else MAYBE
    return MAYBE


def attribute_literals(check: dict, attr: str, classes: dict) -> set | None:
    """The literal values the check's raise calls give attribute `attr`, or None
    when any of its raise calls does not give a literal for it."""
    index = None
    for name in ancestors(check["class"], classes):
        mapping = classes.get(name, {}).get("init_attrs", {})
        if attr in mapping:
            index = mapping[attr]
            break
    values = set()
    for lit in check["literal_args"]:
        if attr in lit["kw"]:
            values.add(repr(lit["kw"][attr]))
        elif index is not None and str(index) in lit["pos"]:
            values.add(repr(lit["pos"][str(index)]))
        else:
            return None
    return values


def verdicts(check: dict, block: dict, classes: dict) -> list[tuple[str, str]]:
    """(assertion as text, verdict) for every assertion of the block."""
    out = []
    if block.get("match") is not None:
        out.append((f"match {block['match']!r}", text_verdict(check, "match", block["match"], classes)))
    for spec in block.get("post", []):
        kind = spec[0]
        if kind == "match":
            out.append((f"match {spec[1]!r}", text_verdict(check, "match", spec[1], classes)))
        elif kind == "str_eq":
            out.append((f"str == {spec[1]!r}", text_verdict(check, "str_eq", spec[1], classes)))
        elif kind == "str_in":
            out.append((f"{spec[1]!r} in str", text_verdict(check, "str_in", spec[1], classes)))
        elif kind == "attr_eq":
            values = attribute_literals(check, spec[1], classes)
            if values is None:
                v = MAYBE
            else:
                v = YES if repr(spec[2]) in values else NO
            out.append((f".{spec[1]} == {spec[2]!r}", v))
    return out


def excluded_by(check: dict, block: dict, classes: dict) -> list[str]:
    """The block's assertions that cannot hold on the check (empty: kept)."""
    return [text for text, v in verdicts(check, block, classes) if v == NO]


# -- the rule ----------------------------------------------------------------------

def target_for(block: dict, checks: list[dict], classes: dict) -> dict:
    expected = block["expected"] or []
    cand = [c for c in checks if c["reachable"]
            and any(is_subclass(c["class"], e, classes) for e in expected)]
    c_class = sorted(c["id"] for c in cand)
    exclusions, positive = {}, {}
    kept = []
    for c in cand:
        vs = verdicts(c, block, classes)
        no = [text for text, v in vs if v == NO]
        if no:
            exclusions[c["id"]] = no
            continue
        kept.append(c)
        yes = [text for text, v in vs if v == YES]
        if yes:
            positive[c["id"]] = yes
    c_assert = sorted(c["id"] for c in kept)
    c_pos = sorted(positive)
    out = {"key": block["key"], "expected": expected, "C_class": c_class,
           "C_assert": c_assert, "C_pos": c_pos, "excluded": exclusions, "positive": positive,
           "scores": [], "name_tokens": sorted(name_tokens(block["test"])), "target": None,
           "basis": None, "tier": None, "reason": None}

    def done(target: str, basis: str) -> dict:
        out.update(target=target, basis=basis,
                   tier="assertion" if basis in ASSERTION_TIER else "name")
        return out

    if not c_class:
        out["reason"] = "no reachable check of the expected class"
        return out
    if not c_assert:
        out["reason"] = "the assertions exclude every candidate"
        return out
    if len(c_class) == 1:
        return done(c_class[0], "class")
    if len(c_assert) == 1:
        return done(c_assert[0], "assert")
    if len(c_pos) == 1:
        return done(c_pos[0], "assert-literal")
    pool = [c for c in kept if c["id"] in positive] if len(c_pos) >= 2 else kept
    narrowed = len(pool) < len(c_class)
    n = len(pool)
    desc = {c["id"]: descriptor(c) for c in pool}
    df: dict[str, int] = {}
    for d in desc.values():
        for t in d:
            df[t] = df.get(t, 0) + 1
    names = name_tokens(block["test"])
    scored = []
    for cid in sorted(desc):
        hits = sorted(t for t in names if t in desc[cid])
        score = round(float(sum(math.log(n / df[t]) for t in hits)), SCORE_DIGITS)
        scored.append((score, cid, hits))
    scored.sort(key=lambda s: (-s[0], s[1]))
    out["scores"] = [{"check": cid, "score": round(score, 6), "tokens": hits}
                     for score, cid, hits in scored[:TOP]]
    out["pool"] = "C_pos" if len(c_pos) >= 2 else "C_assert"
    best = scored[0][0]
    tied = [cid for score, cid, _ in scored if score == best]
    if best <= 0:
        out["reason"] = "no name token matches"
    elif len(tied) > 1:
        out["reason"] = "tie"
        out["tied"] = tied
    else:
        return done(tied[0], "assert+name" if narrowed else "name")
    return out


def compute_targets(blocks_doc: dict, checks_doc: dict) -> dict:
    classes = checks_doc["classes"]
    rows = [target_for(b, checks_doc["checks"], classes)
            for b in blocks_doc["blocks"] if b["included"]]
    counts: dict[str, int] = {}
    for r in rows:
        k = r["basis"] or f"none: {r['reason']}"
        counts[k] = counts.get(k, 0) + 1
    return {"rule_version": RULE_VERSION,
            "constants": {"stop": sorted(STOP), "min_len": MIN_LEN, "strip_s_above": STRIP_S_ABOVE,
                          "score_digits": SCORE_DIGITS, "weight": "log(N / df(t))",
                          "assertion_tier": list(ASSERTION_TIER), "name_tier": list(NAME_TIER)},
            "counts": dict(sorted(counts.items())), "blocks": rows}
