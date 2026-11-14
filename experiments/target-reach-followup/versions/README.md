# Versions: the nested-header test on Python 3.13 and 3.14

This folder repeats the version check of
`../../mutation-adequacy-pyjwt/version-check/` (called "the earlier check"
below) on CPython 3.13 and 3.14, with CPython 3.12.3 as a control, and
measures how deep the `json` module can nest arrays on each interpreter.

The earlier check ran the test
`test_decode_deeply_nested_header_throws_decode_error` of PyJWT 2.15.1
(commit `7d5ef55e42ce42221f58dc49943e92ccad1fa66a`) on CPython 3.9 to 3.12.
Its header is 1000 nested JSON arrays; the test expects `DecodeError` with a
message matching "Invalid header". On 3.9.25, 3.10.20 and 3.11.15,
`json.loads` raises `RecursionError` and the JSON check `jws.header-json`
(`jwt/api_jws.py:374`) rejects the token; on 3.12.3, `json.loads` parses the
header and the next check, `jws.header-object` (line 377), rejects it, with a
message the test's pattern also matches.

## Result

`results.jsonl` holds one line per interpreter and variant, in the format of
the earlier check's `results.jsonl`, with 1 more key in the `pytest` object
(`offline_refused`). Variant `released` is PyJWT 2.15.1 as released; variant
`before-fix` is a copy whose JSON check catches `ValueError` only, as before
upstream commit `0657369`.

| Python | Variant | `json.loads` of the header | Deciding check (raise site) | Test passes | Exception and message |
|---|---|---|---|---|---|
| 3.12.3 (control) | released | parses, to a list | `jws.header-object`, `jwt/api_jws.py:377` | yes (pytest 9.1.1) | `DecodeError`: "Invalid header string: must be a json object" |
| 3.12.3 (control) | before-fix | parses, to a list | `jws.header-object`, `jwt/api_jws.py:377` | yes (pytest 9.1.1) | `DecodeError`: "Invalid header string: must be a json object" |
| 3.13.14 | released | parses, to a list | `jws.header-object`, `jwt/api_jws.py:377` | yes (pytest 9.1.1) | `DecodeError`: "Invalid header string: must be a json object" |
| 3.13.14 | before-fix | parses, to a list | `jws.header-object`, `jwt/api_jws.py:377` | yes (pytest 9.1.1) | `DecodeError`: "Invalid header string: must be a json object" |
| 3.14.6 | released | parses, to a list | `jws.header-object`, `jwt/api_jws.py:377` | yes (pytest 9.1.1) | `DecodeError`: "Invalid header string: must be a json object" |
| 3.14.6 | before-fix | parses, to a list | `jws.header-object`, `jwt/api_jws.py:377` | yes (pytest 9.1.1) | `DecodeError`: "Invalid header string: must be a json object" |

On every row the recursion limit is 1000, the C scanner of `json` is
present, the guard refused 0 outside connections, and the direct decode
agrees with pytest. The control repeats the 2 rows of the earlier check for
3.12.3 value for value. On 3.13.14 and 3.14.6, as on 3.12.3, the test
passes with or without the change of `0657369`: it does not exercise its
target check `jws.header-json` on these interpreters.

`depth.jsonl` holds, per interpreter, the deepest nesting of JSON arrays that
`json.loads` accepts with the C scanner and with the pure-Python scanner, with
a recursion limit of 1000 and a stack size limit (`ulimit -s`) of 8192 KiB:

| Python | C scanner | pure-Python scanner |
|---|---|---|
| 3.9.25 | 993 | 496 |
| 3.10.20 | 993 | 496 |
| 3.11.15 | 993 | 496 |
| 3.12.3 | 9997 | 496 |
| 3.13.14 | 9998 | 496 |
| 3.14.6 | 40121 | 496 |

The depth is measured at a fixed Python call depth (see `depth_probe.py`); the
same call made from deeper in a program reaches less deep. The 3.14.6 value
differs between runs: 3 runs of `depth_probe.py` gave 40111, 40121 and 40139.
3.12.3 gave 9997 in both of 2 runs; 3.9, 3.10, 3.11 and 3.13 were run once.
The deposited file holds 1 run per interpreter.

## Files

| File | Content |
|---|---|
| `nested_header.py` | the earlier check's script, adapted; its docstring lists every difference |
| `results.jsonl` | 6 lines: 3 interpreters, 2 variants |
| `depth_probe.py` | the nesting-depth measurement |
| `depth.jsonl` | 6 lines: 1 per interpreter, 3.9 to 3.14 |
| `test_nested_header.py` | unit tests of `nested_header.py` on synthetic packages |

## Differences from the earlier check

1. Each pytest call loads the offline guard `../../target-reach/guard/reach_offline.py`
   with `-p reach_offline`, as `../../target-reach/reach/run.py` does, and the
   number of refused outside connections is recorded.
2. The environment of the pytest call is that of `run.py`: `PATH` starts with
   the folder of the interpreter, and `HOME` is inherited. The earlier check
   set `PATH=/usr/bin:/bin` and `HOME=/tmp`.
3. The copy of the library is made in a subfolder of a temporary directory,
   so that the guard's output file lies outside the copy.
4. The script checks 8 sentinels (S1 to S8 in its docstring), prints all rows
   and then exits with status 1 when one does not hold.
5. pytest 9.1.1 is installed for 3.13 and 3.14, so the test itself runs there;
   the earlier check ran pytest on 3.12.3 only.

## Environments

The interpreters are CPython 3.13.14 and 3.14.6 (Linux x86_64 builds
installed with `uv python install 3.13 3.14`, uv 0.11.21), and CPython 3.12.3
of Ubuntu 24.04 in the environment of the earlier study. For 3.13 and 3.14,
these packages were installed from wheels at the versions of the earlier
study's environment: pytest 9.1.1, iniconfig 2.3.1, packaging 26.3,
pluggy 1.7.0, Pygments 2.21.0, cryptography 49.0.0, cffi 2.1.1,
pycparser 3.12. Every one installed. The other packages of the earlier
study's environment (the mutation tool and its dependencies, coverage) were
not installed; the test does not import them. PyJWT 2.15.1 itself needs no
dependency on Python 3.11 and later.

## Run it

From this directory, with the PyJWT clone of the earlier study at
`../../mutation-adequacy-pyjwt/work/pyjwt` and the environments in
`../work/versions/` (`$(realpath …)` avoids a warning of 3.14 about a
relative `sys.prefix`):

```sh
export UV_PYTHON_INSTALL_DIR="$(realpath ../work/versions)/pythons"
uv python install --no-bin 3.13 3.14
for v in 3.13 3.14; do
  uv venv -p "$UV_PYTHON_INSTALL_DIR/cpython-$v-linux-x86_64-gnu/bin/python$v" ../work/versions/vc${v/./}
  uv pip install --only-binary :all: -p ../work/versions/vc${v/./}/bin/python \
    pytest==9.1.1 iniconfig==2.3.1 packaging==26.3 pluggy==1.7.0 Pygments==2.21.0 \
    cryptography==49.0.0 cffi==2.1.1 pycparser==3.12
done
for spec in "../../mutation-adequacy-pyjwt/work/venv 3.12.3" \
            "../work/versions/vc313 3.13.14" "../work/versions/vc314 3.14.6"; do
  set -- $spec
  "$(realpath $1)/bin/python" -I -B nested_header.py ../../mutation-adequacy-pyjwt/work/pyjwt --expect $2
done > results.jsonl
for py in python3.9 python3.10 python3.11 /usr/bin/python3.12 \
          "$(realpath ../work/versions/vc313)/bin/python" "$(realpath ../work/versions/vc314)/bin/python"; do
  $py -I -B depth_probe.py
done > depth.jsonl
../../mutation-adequacy-pyjwt/work/venv/bin/python -I -B -m pytest -q -p no:cacheprovider test_nested_header.py
```

The interpreters 3.9 to 3.11 are those of the earlier check.

## Sources

The documentation of CPython 3.12 states the change under "Improved Modules",
"sys" (https://docs.python.org/3/whatsnew/3.12.html):

> sys.setrecursionlimit() and sys.getrecursionlimit().
> The recursion limit now applies only to Python code. Builtin functions do
> not use the recursion limit, but are protected by a different mechanism
> that prevents recursion from causing a virtual machine crash.

The changelog (https://docs.python.org/3/whatsnew/changelog.html, "Python
3.12.0 alpha 1", "Core and Builtins"):

> gh-91079: Separate Python recursion checking from C recursion checking
> which reduces the chance of C stack overflow and allows the recursion
> limit to be increased safely.

The C scanner of `json` (`Modules/_json.c`) guards the parse of each array
with `_Py_EnterRecursiveCall` at the tags `v3.11.15`, `v3.12.3`, `v3.13.14`
and `v3.14.6`. In `Include/internal/pycore_ceval.h`, that check decrements
`recursion_remaining` (the Python recursion limit) at `v3.11.15` and
`c_recursion_remaining` at `v3.12.3` and `v3.13.14`, whose default on Linux
is 10000 (`Include/cpython/pystate.h`); at `v3.14.6` it compares the machine
stack pointer with a stack limit. The changelog, "Python 3.14.0 alpha 6",
"Core and Builtins":

> gh-91079: Change C stack overflow protection to consider the amount of
> stack consumed, rather than a counter. This allows deeper recursion in
> many cases, but remains safe.

The What's New page of 3.13 (https://docs.python.org/3/whatsnew/3.13.html)
contains no occurrence of "recursion". The page of 3.14
(https://docs.python.org/3/whatsnew/3.14.html), "C API changes", "Removed C
APIs":

> Remove the undocumented APIs Py_C_RECURSION_LIMIT
> and PyThreadState.c_recursion_remaining.
> These were added in 3.13 and have been removed without deprecation.
> Use Py_EnterRecursiveCall() to guard against runaway
> recursion in C code.
> (Removed by Petr Viktorin in gh-133079, see also gh-130396.)

The pages were read on 14 November 2026; docs.python.org then served the
documentation of Python 3.15.2.
