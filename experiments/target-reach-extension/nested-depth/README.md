# Which check rejects a deeply nested header

This folder holds `depth_runs.py`, the script of the part `nested-depth/` of
`../PROTOCOL.md` (sections 3.2 and 4.5, and step 6 of section 6), and, after
the next stage, its output `results.jsonl`. Paths are relative to this folder;
times are UTC.

## What the script does

It decodes headers of 10000 and 50000 nested JSON arrays with PyJWT 2.15.1
on CPython 3.12.3, 3.13.14 and 3.14.6, in 2 variants of the JSON check, and
records for each of the 12 runs which check rejects the header, or that none
does. It is adapted from `../../target-reach-followup/versions/nested_header.py`
(lines 8-11 of the script; the differences are its lines 13-42):

- **Variants** (lines 39-42 and 94-95): `released`, the commit as released,
  whose JSON check catches `(ValueError, RecursionError)`; `before-fix`, a copy
  whose clause reads `except ValueError as e:`, the line before upstream
  commit `0657369` ("Handle recursive JWS headers as decode errors"). The
  script reads that commit from the clone with `git show` and stops unless it
  removes exactly the one line and adds exactly the other (sentinel N2, lines
  193-203).
- **Copy** (lines 224-240): each run gets a fresh copy of `jwt/`, `tests/` and
  `pyproject.toml` from the clone, without `__pycache__`; the `before-fix`
  copy has its 1 except clause replaced (sentinel N4).
- **Token** (lines 13-15, 99-100 and 137-138): the header
  `b"[" * N + b"]" * N`, base64url-encoded, with the payload and signature
  parts of the token of PyJWT's test
  `test_decode_deeply_nested_header_throws_decode_error`.
- **Decode** (lines 16-26 and 148): 1 child process per run,
  `PYTHON -I -B depth_runs.py --child COPY VARIANT N`, which calls
  `jwt.decode(token, "secret", algorithms=["HS256"])`, with a time limit of
  60 s (`--timeout`, line 108), the environment of the toolkit's runner (PATH
  starting with the folder of the interpreter, HOME inherited from the caller,
  `LANG` and `LC_ALL` `C.UTF-8`, `PYTHONHASHSEED=0`,
  `PYTHONDONTWRITEBYTECODE=1`; lines 211-214) and a soft stack size limit of
  8192 KiB (`--stack-kib`, line 109; lines 243-251), that of `depth.jsonl` of
  the follow-up (`../../target-reach-followup/versions/README.md`, lines
  44-46). The child keeps the default recursion limit.
- **Result** (lines 27-38 and 254-264): `outcome` is `rejected by a check`
  when the innermost frame of the traceback inside the copy (`raise_site`) is
  a line of a raise statement of a check of
  `../../target-reach/subjects/pyjwt-package/checks.json`; `exception outside
  the checks` when it is no such line or no frame is inside the copy;
  `accepted` when the call returns; `interpreter failed` when the child ends
  on a signal or without its row; `timed out` past the time limit. `check`
  is the id of that file at the raise site and `check_earlier_study` that of
  `../../mutation-adequacy-pyjwt/checks.json`.
- **Sentinels** (lines 51-62): the script stops at once when N1 (the clone is
  at the commit), N2, N4 or N5 (`jwt` is imported from the copy) does not
  hold. It writes every row and exits with status 1 when N3 (lines 372, 374
  and 377 of `jwt/api_jws.py` hold the expected statements in the clone and
  in each copy, and both definition files give a check at lines 374 and 377),
  N6 (the interpreter is CPython in the version asked for), N7 (the C scanner
  of `json` is in use) or N8 (the child has the stack limit asked for) does
  not.

## Inputs

| Input | Where | Made by |
|---|---|---|
| PyJWT 2.15.1 at commit `7d5ef55e42ce42221f58dc49943e92ccad1fa66a` (`../../target-reach/subjects/pyjwt-package/subject.json`, lines 4 and 7) | `../work/nested-depth/pyjwt` | `git clone --quiet https://github.com/jpadilla/pyjwt ../work/nested-depth/pyjwt` (14:06:09Z) and `git -C ../work/nested-depth/pyjwt -c advice.detachedHead=false checkout --quiet 7d5ef55e42ce42221f58dc49943e92ccad1fa66a` (14:06:10Z) |
| CPython 3.13.14 and 3.14.6, Linux x86_64 builds | `../work/pythons/` | `uv python install --no-bin 3.9.25 3.10.20 3.11.15 3.13.14 3.14.6` (14:05:43Z to 14:05:45Z; `../preparation/tools/logs/uv-python-install.log`) |
| CPython 3.12.3 | `/usr/bin/python3.12`, of Ubuntu 24.04 (`/etc/os-release`: "Ubuntu 24.04.4 LTS") | the system |
| 3 environments without any package | `../work/nested-depth/venvs/py312`, `py313`, `py314` | `uv venv --quiet -p <interpreter> <environment>`, uv 0.11.21 (14:06:56Z; the `pyvenv.cfg` of each gives `uv = 0.11.21` and the version) |
| The checks, read at run time | `../../target-reach/subjects/pyjwt-package/checks.json`, SHA-256 `750d91cb2ae9a9826ac0edeed126d23c741fd79ea490e32f1a29f3a92e1859d2`; `../../mutation-adequacy-pyjwt/checks.json`, SHA-256 `4a132395acc22906e563daadf24599f84b50019286426cf33beb932bd4d36a86` | the earlier studies (the script prints both digests, `../preparation/tools/logs/depth-dry.txt`, line 1) |

The commands and their times are the lines labeled `interpreters`,
`clone-pyjwt`, `check-clone` and `venv-nested` of
`../preparation/tools/commands.tsv` (lines 1-3, 17-22 and 31-33), each with its
start, end and exit status (0 for all). PyJWT 2.15.1 needs no dependency on
Python 3.11 and later (`../../target-reach-followup/versions/README.md`,
lines 139-140; lines 44-49 of the script).

## Output

`results.jsonl` (`--out`, lines 68-69): 12 lines, 1 JSON object per run, in
the order interpreter, variant, depth (line 376). Its keys:

- from the script: `interpreter`, `python_path`, `variant`, `depth`,
  `timeout_seconds`, `stack_kib_asked`, `returncode` and `wall_seconds`
  (lines 309-330);
- the settings that the child prints before the decode (lines 140-145), kept
  when the child ends by a signal or a time-out: `python`, `implementation`,
  `executable`, `base_prefix`, `recursion_limit`, `json_c_scanner` and
  `stack_limit_kib`;
- the result (lines 147-161 and 254-264): `decoded`, `value_type` when the
  call returns; for an exception, `exception`, `message`, `cause`,
  `cause_message`, `raise_site` and `innermost_frame` (each with `file`,
  `line`, `function` and `in`: `copy`, `stdlib` or `other`) and `frames`;
  `seconds`; `check`, `check_earlier_study` and `outcome`;
- for `interpreter failed`, `signal`, `stderr_tail` and, when the child had
  printed its row, `row_before_the_signal` (lines 323-328); for `timed out`,
  `returncode` is null (lines 314-318).

The copies go to `../work/nested-depth/copies/` and each is removed after its
run (lines 394-401). The rows are printed as they come and `results.jsonl` is
written after the 12th run (lines 400-405).

## The dry runs

`python3 -I -B depth_runs.py --dry` ran at 14:23:15Z and at 14:46:17Z, both
times with exit status 0 (`../preparation/tools/commands.tsv`, lines 42 and 47). It
makes no copy and decodes nothing (lines 64-66). The log of the second run,
`../preparation/tools/logs/depth-dry.txt`, gives:

- line 1: the clone at `7d5ef55e42ce42221f58dc49943e92ccad1fa66a` (N1),
  `0657369` replacing the except clause as expected (N2), and the 2 digests
  of the table above;
- lines 2-4: the 3 environments report CPython 3.12.3, 3.13.14 and 3.14.6;
- lines 5-16: the 12 child commands, each with its copy, its environment, a
  time limit of 60 s and a stack limit of 8192 KiB.

## What was known before the runs

From `../../target-reach-followup/versions/README.md`:

- lines 28-35: with the 1000 nested arrays of the test, on 3.12.3, 3.13.14
  and 3.14.6, `json.loads` parses the header and the check at
  `jwt/api_jws.py:377` ("must be a json object") rejects it, in both variants;
- lines 44-55: the deepest nesting that `json.loads` accepts with the C
  scanner, with a recursion limit of 1000 and a stack size limit of 8192 KiB,
  is 993 on 3.9.25 to 3.11.15, 9997 on 3.12.3, 9998 on 3.13.14 and 40121 on
  3.14.6;
- lines 57-61: the depth was measured at a fixed Python call depth, and the
  same call made from deeper in a program reaches less deep; 3 runs on 3.14.6
  gave 40111, 40121 and 40139.

The depths 10000 and 50000 were chosen with these numbers known
(`../PROTOCOL.md`, section 9): 10000 is just above 9997 and 9998, and 50000 is
above 40121. A result holds for the call through `jwt.decode` and the stack
size limit of its run.

## The next stage

After the protocol commit and its 2 time-stamp tokens (`../PROTOCOL.md`,
section 6, steps 1 and 6), from this folder:

    python3 -I -B depth_runs.py

It makes the 12 runs, each within 60 s, and writes `results.jsonl`. It uses
no output of the other parts and may run while they run (section 6, step 6).
`--python VERSION=PYTHON` (repeated) replaces the 3 environments, `--clone`
the clone, `--stack-kib 0` keeps the caller's stack limit; the defaults are
those of the protocol.

## Tests

`../tests/test_depth_runs.py` runs the script on a synthetic package named
`jwt`, written into a temporary folder; it is not PyJWT, and the tests decode
no header of the study (its lines 1-9). Its decode raises at the line of a
check, raises a `RecursionError` elsewhere, returns, ends its own process by a
signal, or sleeps past the time limit, by the nesting of the header; the
tests check each outcome, that the settings stay in the row of a failed or
timed-out child, the stack limit 0, sentinels N3, N4 and N6, and the helpers
`child_rows` and `signal_name`. From `..`:

    work/tests-venv/bin/python -B -m pytest -q -p no:cacheprovider tests

The suite of `../tests/` gave 54 passed and 1 skipped in its last run, at
15:10:45Z (`../preparation/tools/commands.tsv`, line 56;
`../preparation/tools/logs/unit-tests.txt`); the skipped test, of the sweep, runs
only with `SWEEP_TOY=1`.
