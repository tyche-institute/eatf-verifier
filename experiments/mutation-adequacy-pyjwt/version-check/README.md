# Version check: the nested-header test on Python 3.9 to 3.12

Added on 12 November 2026, after the results of this experiment were known.
It is outside the protocol: it changes no file in `../generated/` and no
prediction's verdict.

On the unmutated library, O_T fails on 1 of the 81 cases with a target: the
test `test_decode_deeply_nested_header_throws_decode_error` of
`tests/test_api_jws.py`. Its header is 1000 nested JSON arrays, and it expects
`DecodeError` with a message matching "Invalid header". Upstream commit
`0657369` ("Handle recursive JWS headers as decode errors", 9 September 2026)
added the test together with a change to the JSON check of `PyJWS._load`,
`jws.header-json` in `../checks.json`: the check now catches `RecursionError`
as well as `ValueError`. The labelling rule gave the test that check. On
Python 3.12.3, the version of every run of this experiment, `json.loads`
parses the header, and the next check, `jws.header-object`, rejects the token.

`nested_header.py` makes the test's decode call, with the token built as the
test builds it, on the Python that runs it, and records which check rejects
the token. It does so on PyJWT 2.15.1 as released and on a copy with the JSON
check's change of `0657369` reverted, so that the check catches `ValueError`
only. Where pytest is installed, it also runs the test itself, as
`../run_s2.py` runs the suite. Every decode runs in a fresh interpreter, in a
copy of `jwt/`, `tests/` and `pyproject.toml`; the clone is never changed.
Where pytest is not installed, the script applies the test's expectation
itself: the class `DecodeError` and a message matching "Invalid header".

## Result

`results.jsonl` holds one line per Python version and variant.

| Python | JSON check | `json.loads` of the header | Rejected by | The test's expectation |
|---|---|---|---|---|
| 3.9.25, 3.10.20, 3.11.15 | as released | `RecursionError` | `jws.header-json`, `jwt/api_jws.py:374` | holds |
| 3.9.25, 3.10.20, 3.11.15 | change reverted | `RecursionError` | no check: the `RecursionError` escapes from line 372 | fails |
| 3.12.3 | as released | parses, to a list | `jws.header-object`, line 377 | holds; pytest 9.1.1: passed |
| 3.12.3 | change reverted | parses, to a list | `jws.header-object`, line 377 | holds; pytest 9.1.1: passed |

On Python 3.9 to 3.11 the test reaches its target, and reverting its commit's
change makes the decode raise `RecursionError` instead of the `DecodeError` the
test expects. On 3.12.3 the test passes with or without that change. The label
therefore holds; on 3.12.3 the test does not exercise its target. Python 3.13
to 3.15 and PyPy, which PyJWT's continuous integration also runs at commit
`7d5ef55`, were not run.

## Run it

The interpreters were CPython 3.9.25, 3.10.20 and 3.11.15, installed with
`uv python install`, and CPython 3.12.3 of Ubuntu 24.04 in `../work/venv`.
Below Python 3.11, PyJWT requires `typing_extensions`; version 4.16.0 was
installed for 3.9 and 3.10. pytest was installed only in `../work/venv`
(9.1.1). From this directory, with the clone of `../README.md` in
`../work/pyjwt`:

```sh
uv venv -p 3.9 ../work/vc39 && uv pip install -p ../work/vc39/bin/python typing_extensions
uv venv -p 3.10 ../work/vc310 && uv pip install -p ../work/vc310/bin/python typing_extensions
uv venv -p 3.11 ../work/vc311
for py in ../work/vc39 ../work/vc310 ../work/vc311 ../work/venv; do
  $py/bin/python -I -B nested_header.py ../work/pyjwt
done > results.jsonl
```

The script refuses to run if the clone is not at commit
`7d5ef55e42ce42221f58dc49943e92ccad1fa66a`.
