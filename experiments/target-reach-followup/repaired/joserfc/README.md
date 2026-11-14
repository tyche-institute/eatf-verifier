# Repaired variants of 3 joserfc 1.8.0 tests

In 3 cases of `joserfc` 1.8.0 the target does not fire, because an earlier
check rejects the input with the same exception class (class A in
`../target-reach/readings/joserfc/FLAGS.md`; rows of
`../target-reach/generated/joserfc/flags.csv`). This folder holds, for each of
the 3, a repaired variant: a new test in the style of the original whose input
differs from the original as little as found, and which the target decides on
the unmodified library with its default limits. The original tests are not
changed. No line of the library is changed, no check is deleted and no mutant
is made.

Line numbers refer to the commit of `../target-reach/subjects/joserfc/subject.json`
(`f345ff71cd6c36452a4e11e47b805ad450a95dd8`); library paths are relative to
`src/`.

| File | Variant | Original block | Deciding check of the original | Target, deciding check of the variant |
|---|---|---|---|---|
| `tests_repaired/test_repaired_jwe_compact.py` | `TestJWECompactRepaired::test_repaired_ciphertext_exceeds_size` | `tests/jwe/test_compact.py::TestJWECompact.test_ciphertext_exceeds_size#0` | `_rfc7516.registry.JWERegistry.validate_compact_value_size#1` | `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1` |
| `tests_repaired/test_repaired_jws_compact.py` | `TestCompactRepaired::test_repaired_payload_exceeded_size_error` | `tests/jws/test_compact.py::TestCompact.test_payload_exceeded_size_error#0` | `_rfc7515.registry.JWSRegistry.validate_compact_value_size#1` | `_rfc7515.registry.JWSRegistry.validate_payload_size#1` |
| `tests_repaired/test_repaired_jws_json.py` | `TestJSONRepaired::test_repaired_b64_must_be_protected` | `tests/jws/test_json.py::TestJSON.test_b64_must_be_protected#1` | `registry.reject_unprotected_crit_header#2` | `_rfc7797.json._is_payload_base64_encoded#1` |

Each variant is 1 test method in a `unittest.TestCase` subclass, as the
originals are, with the same `assertRaises` call: the same expected class,
the same entry point and the same key, and no other assertion. It imports
from the same modules as the original (`joserfc.errors`, `joserfc.jwe` or
`joserfc.jws`, `joserfc.jwk`, `joserfc.util`) and only the names it uses. The
class names end in `Repaired` so that no node identifier repeats one of the
original suite. All 3 work with the default limits; no
`test_repaired_nondefault_*` variant was needed.

## What each variant changes

**1. Ciphertext size (JWE compact).** The only change is the number of bytes
encoded into the ciphertext segment: 49153 instead of 70000, so the segment
has 65538 characters instead of 93334. The limit of the segment is
`max_ciphertext_length = 65536` (`joserfc/_rfc7516/registry.py`, line 62),
checked by `validate_ciphertext_size` (lines 138 to 140). Before the segments
are checked, `extract_compact` (`joserfc/_rfc7516/compact.py`, line 37) checks
the whole value against the sum of the 5 segment limits (registry, lines 56,
58, 60, 62 and 64: 1024 + 1024 + 64 + 65536 + 64 = 67712) in
`validate_compact_value_size` (lines 113 to 122). The original value has
93415 characters and is rejected there; the variant has 65619 and reaches
line 47 of `compact.py`, where `validate_ciphertext_size` rejects it. With
the other segments of the test (81 characters with the 4 dots), every count
of bytes from 49153 to 50723 gives a segment above 65536 and a value of at
most 67712 characters; 49153 is the smallest, since 49152 bytes encode to
exactly 65536 characters.

**2. Payload size (JWS compact).** The only change is the number of bytes
encoded into the payload segment: `96000 + 1` instead of `128000 + 1`, so the
segment has 128002 characters instead of 170668. The limit
`max_payload_length = 128000` (`joserfc/_rfc7515/registry.py`, line 53) is
compared, in `validate_payload_size` (lines 113 to 115), with the length of
the encoded segment, not of the decoded payload; the original adds 1 to the
limit before encoding. `extract_rfc7515_compact`
(`joserfc/_rfc7797/compact.py`, line 44) first checks the whole value against
512 + 128000 + 1024 = 129536 (registry, lines 51, 53 and 55;
`validate_compact_value_size`, lines 104 to 107). The original value has
170692 characters and is rejected there; the variant has 128026 and reaches
line 55 of `compact.py`, where `validate_payload_size` rejects it. Every count
from 96001 to 97134 bytes does the same with the other segments of the test;
96001 is the smallest.

**3. `b64` in the unprotected header (JWS flattened JSON).** The only change
is 1 member added to the protected header: `{"alg": "HS256", "b64": True,
"crit": ["b64"]}` instead of `{"alg": "HS256", "crit": ["b64"]}`; the
unprotected header stays `{"b64": True}`. `_is_payload_base64_encoded`
(`joserfc/_rfc7797/json.py`, lines 112 to 115) first calls
`check_json_member_headers` (line 113; `joserfc/_rfc7515/json.py`, lines 168
to 172), which calls `reject_unprotected_crit_header`
(`joserfc/registry.py`, lines 217 to 230). With `b64` now in the protected
header, the condition of line 229 (`name not in protected and name in
unprotected`) is false and nothing is raised. `check_header` then accepts the
merged header: `b64` is present and registered (`check_crit_header`, lines
200 to 214; `"b64"` at line 131 and `"crit"` at line 129, with the
validators `is_bool` and `is_list_str`). Line 114 then finds `b64` in the
unprotected header and line 115 raises "'b64' header MUST be protected". The
protected segment has 55 characters, below `max_header_length = 512`
(`joserfc/_rfc7515/registry.py`, line 51; checked at line 74 of
`joserfc/_rfc7797/json.py`). The variant repeats the second block of the
original only; the first block is already decided by its target.

### Why the original input of case 3 cannot reach its target

With the protected header of the original block, `{"alg": "HS256", "crit":
["b64"]}`, no unprotected header can make the target decide. The target
raises only when the unprotected header holds `b64`
(`joserfc/_rfc7797/json.py`, line 114). Every path to that line passes line
113 first, and there `reject_unprotected_crit_header` raises at line 230 of
`joserfc/registry.py` for every string listed in the protected `crit` that is
absent from the protected header and present in the unprotected one (line
229). So the block, as written, tests that a name listed in `crit` must be
protected (`registry.reject_unprotected_crit_header#2`, the same message
template "'{*}' header MUST be protected"), and the repair has to change the
protected header. The other change of 1 item, removing `"b64"` from `crit`,
was not tried.

For cases 1 and 2 the same holds for every input whose whole value exceeds
67712 or 129536 characters: lines 37 and 44 run before the segment checks, so
the target can decide only an input below those sums.

## Where the variants go and how they run

The folder `tests_repaired/` is copied, as it is, into the root of a copy of
the release, next to `tests/` (the copy holds `src/`, `tests/` and
`pyproject.toml`, the paths of "copy" in `subject.json`). From the root of
that copy, with `src/` on the module search path:

    <env>/bin/python -m pytest -q -p no:cacheprovider -p reach_offline --rootdir=. tests_repaired

and, for the whole suite with the variants, `tests tests_repaired` as the
test paths. The folder has no `__init__.py`; its 3 module names do not occur
in `tests/`. `verify.py` makes these copies and calls itself.

## Verification

    python3 -I -B repaired/joserfc/verify.py

from the experiment directory (any directory works; the defaults are taken
relative to the script). It uses the interpreter and the clone named in
`../target-reach/work/joserfc/local.json`, writes its work files to
`work/repaired/verify/` and its result to `repaired/joserfc/verify.json`, and
then exits with status 1 when a sentinel does not hold. It first runs the
`verify` step of the toolkit's runner on that clone and interpreter, with its
work folder in `work/repaired/verify/toolkit-verify/`. Every pytest call
loads `../target-reach/guard/reach_offline.py` and gets the environment of
the toolkit's runner (`PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, `LANG`
and `LC_ALL` set to `C.UTF-8`, the options of "pytest_args"), on a fresh copy.

The raise site is read from the traceback of the exception that reached
`assertRaises`: a probe plugin wraps the `__exit__` method of unittest's
`assertRaises` context, which also serves the callable form, and takes the
innermost frame of the traceback (file, function, line) and the innermost
frame inside the package directory. A sentinel requires the 2 to be the same
frame, so the raise site of the task and that of the protocol (section 4,
"Deciding check") coincide. The file, relative to `src/`, and the line are
looked up in the line ranges of the checks in
`../target-reach/subjects/joserfc/checks.json`.

The recorder step builds a derived subject in `work/repaired/verify/derived/`:
a directory with the copied paths of the clone plus `tests_repaired/`, and a
`subject.json` that differs from the toolkit's in 5 fields: `name`
(`joserfc-repaired`), `commit` (removed, because the derived directory is no
git clone), `copy` (`tests_repaired` added), `tests` (the 3 variant files
added) and `suite_runs` (`tests_repaired` added to the paths). The toolkit's
runner then runs `define targets baseline` on it, with `--defs` and `--work`
in that folder; `verify` of the runner is not run, because it requires the
commit.

### Results

All 7 sentinels hold (`verify.json`). 2 runs of the script gave byte-identical
`verify.json` files.

| Block | Raise site (file, function, line) | Check | Test |
|---|---|---|---|
| original 1 (`tests/jwe/test_compact.py:276`) | `joserfc/_rfc7516/registry.py`, `JWERegistry.validate_compact_value_size`, 122 | `_rfc7516.registry.JWERegistry.validate_compact_value_size#1` | passes |
| variant 1 | `joserfc/_rfc7516/registry.py`, `JWERegistry.validate_ciphertext_size`, 140 | `_rfc7516.registry.JWERegistry.validate_ciphertext_size#1` | passes |
| original 2 (`tests/jws/test_compact.py:71`) | `joserfc/_rfc7515/registry.py`, `JWSRegistry.validate_compact_value_size`, 107 | `_rfc7515.registry.JWSRegistry.validate_compact_value_size#1` | passes |
| variant 2 | `joserfc/_rfc7515/registry.py`, `JWSRegistry.validate_payload_size`, 115 | `_rfc7515.registry.JWSRegistry.validate_payload_size#1` | passes |
| original 3 (`tests/jws/test_json.py:166`, second block) | `joserfc/registry.py`, `reject_unprotected_crit_header`, 230 | `registry.reject_unprotected_crit_header#2` | passes |
| variant 3 | `joserfc/_rfc7797/json.py`, `_is_payload_base64_encoded`, 115 | `_rfc7797.json._is_payload_base64_encoded#1` | passes |

The messages are "Value size exceeds 67712 bytes.", "Ciphertext size exceeds
65536 bytes.", "Value size exceeds 129536 bytes.", "Payload size exceeds
128000 bytes." and, for both blocks of case 3, "'b64' header MUST be
protected".

Whole suite (`tests`, the suite run of `subject.json`): 310 tests pass
without the variants and 313 with them (91 subtests pass in each run), with
no failure, error or skip; the passing tests with the variants are those
without them plus the 3 variants. No pytest call made an attempt to reach
another machine.

Under the recorder of the toolkit, both baseline records give each of the 6
blocks the deciding check of the table above, and each block fires that check
only. The derived subject has the 97 checks of `checks.json` and the blocks of
`blocks.json` for the original test files, plus 3 included blocks; the rule
`reach-target-rule/2` gives the 3 variant blocks the targets named above (name
tier) and every original block the target of
`../target-reach/subjects/joserfc/targets.json`.

## Files

| Path | What it holds |
|---|---|
| `tests_repaired/` | The 3 variants, 1 file each |
| `verify.py` | The verification script: standard library, plus pytest of the subject environment inside the pytest calls |
| `verify.json` | Its output: per original and per variant the raise site, the check and the outcome of the test; the whole-suite counts; the recorder section; the 7 sentinels |
| `selftest/` | Tests of `verify.py` on a small synthetic package |

The tests of `verify.py`, with an environment that has pytest:

    <env>/bin/python -B -m pytest -q -p no:cacheprovider \
        --basetemp=work/repaired/selftest-tmp repaired/joserfc/selftest

## Not verified

- The own test of each variant on a copy without its target was not run: no
  check is deleted in this part. That each variant fails without its target
  is therefore not shown.
- The variants were run in 1 environment only: the pinned environment of
  `../target-reach/subjects/joserfc/requirements.txt` on CPython 3.12.3 (with
  pytest 9.2.0), which the toolkit's `verify` step checks at the start of
  every run of `verify.py`.
- For case 3, the alternative repair that removes `"b64"` from `crit` was not
  run.
