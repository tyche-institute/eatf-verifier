# Extension of target reach: 3 more runs

The experiment in `../target-reach/` found, for 4 held-out Python verification
libraries, the check that rejects the input of each negative-test block and
compared it with the check that a fixed rule assigns. This folder holds 3 more
runs on that experiment, chosen after its results and those of
`../target-reach-followup/` had been read. `PROTOCOL.md` fixes them before they
run; its section 1 gives the source of each number below.

1. **No-fire deletions (`no-fire/`).** 103 of the 223 reachable checks of the
   4 held-out libraries fire in no case. Each is deleted, and the whole suite
   runs on the copy without the recorder. 20 of the 103, 5 per library, drawn
   by a script with a fixed seed, are read for an input through an entry
   point that reaches them.
2. **Nested-header depth (`nested-depth/`).** PyJWT 2.15.1 decodes, through
   `jwt.decode`, headers of 10000 and 50000 nested JSON arrays on CPython
   3.12.3, 3.13.14 and 3.14.6, as released and with the fix of the JSON check
   reverted; each run records which check rejects the header, or that none
   does.
3. **The 7 screened libraries (`screened/`).** The toolkit of
   `../target-reach/`, unchanged, on the 7 candidates of its selection that
   pass the criteria I1 to I4 and were not needed, without readings, and a
   sweep of CPython 3.9 to 3.14 over the tests that hold their included
   blocks. 3 of the 7 cannot be run from a copy and go through no step
   (`PROTOCOL.md`, section 3.3).

## Status

None of the runs that `PROTOCOL.md` describes has been made. The folder holds
the protocol, the definitions of the 7 screened libraries with the record of
their preparation, the sample of 20 checks, the scripts of the 3 parts and
their tests. The outputs listed under "Files" as "after the runs" do not exist
yet. Section 5 of the protocol states what had been done before its commit.

## Files

| File | Content |
|---|---|
| `PROTOCOL.md` | The protocol of the 3 parts, fixed by its commit |
| `DEVIATIONS.md` | The departures from the protocol; none so far |
| `no-fire/README.md` | The scripts of the part, the population, the dry run and the preparation of the clones and environments |
| `no-fire/sample.py`, `no-fire/sample.csv` | The draw of the 20 sampled checks, and its 20 rows |
| `no-fire/nofire_deletions.py` | The deletion of the 103 checks and the whole-suite runs, with the functions of the toolkit |
| `nested-depth/depth_runs.py` | The 12 decodes of nested headers |
| `screened/subjects/<name>/` | The definitions of each of the 7 libraries (`draft.json`, `subject.json`, `checks.json`, `blocks.json`, `targets.json`, `requirements.txt`) and `PREPARATION.md`, every command run on it before the protocol commit |
| `screened/versions.py` | The interpreter sweep |
| `tests/` | Unit tests of the 4 scripts, on synthetic packages |
| `.gitignore` | Keeps `work/` and `__pycache__/` out of the deposit |

After the runs (`PROTOCOL.md`, section 6):

| File | Content |
|---|---|
| `no-fire/deletions-nofire.csv` | 1 row per deleted check and 1 per control copy |
| `no-fire/summary.json`, `no-fire/records/<library>/` | The summary of the run, and `whole/base.json` and `whole/deletions.json` of each library |
| `no-fire/reach/` | `reach.csv`, `READING.md` and the scripts of the inputs of the 20 sampled checks |
| `nested-depth/results.jsonl` | 1 line per run, 12 in all |
| `screened/generated/<name>/` | The outputs of `reach/analyse.py` and the archive of the records, per library run |
| `screened/generated/REPORT.md`, `report.json` | The libraries run, side by side, and the 5 expectations |
| `screened/recompute/<name>/` | The second computation and its comparison |
| `screened/versions/` | `<name>.json`, `interpreters.csv`, `outcomes.csv` and `cases.csv` of the sweep |
| `timestamps/` | The tokens of the protocol commit and of the results commit |

`work/` (clones, interpreters, environments, copies, raw records and logs) is
not deposited.

## How to run

Every command runs from this folder. The order, and what must hold before
each step, is section 6 of the protocol: no step starts before the protocol
commit has its 2 time stamps. The toolkit needs Python 3.12 or later; the
environments of the libraries are those of `requirements.txt` on CPython
3.12.3, and `verify` refuses any other (`../target-reach/README.md`, "How to
run"). The other interpreters are the builds of `uv python install` (uv
0.11.21) in `work/pythons/`:

    UV_PYTHON_INSTALL_DIR="$PWD/work/pythons" uv python install --no-bin \
        3.9.25 3.10.20 3.11.15 3.13.14 3.14.6

The defaults of `reach/run.py` and `reach/analyse.py` point into
`../target-reach/`; every call below passes `--defs`, `--work` and `--out`.

### Time stamps

The protocol commit and the results commit are time-stamped by freetsa.org
and DigiCert (RFC 3161), and the tokens are verified, as
`../target-reach/timestamps/README.md` describes.

### The 7 screened libraries

`paramiko`, `pycryptodome` and `scramp` go through no step (`PROTOCOL.md`,
section 3.3). For each of `ecdsa`, `python-jose`, `supabase-auth` and
`service-identity`, in that order, with `<clone>` and `<env>` those of
`work/<name>/local.json` (on another machine: a clone at the commit of
`subject.json` and an environment made from `requirements.txt`, as the
library's `PREPARATION.md` records):

    export PYTHONHASHSEED=0
    python3 -I -B ../target-reach/reach/run.py verify baseline deletions \
        whole-baseline whole-deletions pack \
        --subject screened/subjects/<name>/subject.json --defs screened/subjects/<name> \
        --clone <clone> --python <env>/bin/python \
        --work <work> --out screened/generated/<name>
    python3 -I -B ../target-reach/reach/analyse.py \
        --subject screened/subjects/<name>/subject.json --defs screened/subjects/<name> \
        --work <work> --out screened/generated/<name>

`<work>` is `work/<name>`, except for `ecdsa`: its import runs `git describe`
in the first git repository above the copy (`PROTOCOL.md`, section 4), so its
`<work>` is a folder that no git repository holds, the same in both commands.
Before the run, `git -C <folder> rev-parse --git-dir` must fail with "not a
git repository".

The second computation, per library:

    python3 -I -B ../target-reach/recompute/second.py \
        --subject screened/subjects/<name>/subject.json \
        --records screened/generated/<name>/records.tar.xz \
        --out screened/recompute/<name>/second.json
    python3 -I -B ../target-reach/recompute/compare.py \
        --second screened/recompute/<name>/second.json \
        --first screened/generated/<name>/summary.json

The table, once every library named has its outputs (name only those; the
script writes nothing while a named summary lacks the whole-suite records):

    python3 -I -B ../target-reach/reach/report.py \
        --held-out ecdsa python-jose supabase-auth service-identity \
        --generated screened/generated

The sweep, in 1 call, since the script writes its 3 tables from the libraries
of its own call alone, with a work folder that no git repository holds
(`<outside>`):

    python3 -I -B screened/versions.py --support requires-python --only-binary \
        --libraries ecdsa python-jose supabase-auth service-identity \
        --work <outside>/screened-versions

`--support requires-python` and `--only-binary` are the rules of the protocol
(section 4.6); the defaults of the script differ. A library reported as failed
in its main run is left out of `--libraries`. The script compares the 3.12.3
run of each library with its main baseline, read from
`screened/generated/<name>/records.tar.xz` (the default of `--generated`), so
it runs after the main runs, and it refuses a `--work` that a git repository
holds. `--dry` prints the plan from the cached metadata in
`work/screened-versions/pypi/` and fetches nothing, so before the first run it
plans no interpreter.

### No-fire deletions

The clone of each held-out library is in `work/no-fire/src/<name>`, at the
commit of `../target-reach/subjects/<name>/subject.json`, and its environment,
made from that folder's `requirements.txt` on CPython 3.12.3, in
`work/no-fire/venvs/<name>`; `--clone NAME=DIR` and `--python NAME=PYTHON`
give others.

    python3 -I -B no-fire/sample.py --out <file>
    python3 -I -B no-fire/nofire_deletions.py --dry --collect
    python3 -I -B no-fire/nofire_deletions.py

The first command draws the sample again into `<file>`, which must equal
`no-fire/sample.csv`. The last writes `no-fire/deletions-nofire.csv` and
`no-fire/summary.json`, and copies, per library, the records `whole/base.json`
and `whole/deletions.json` from `work/no-fire/<name>/records/` to
`no-fire/records/<name>/whole/`; the other records and the logs stay in
`work/no-fire/<name>/`. The reading of the 20 sampled checks follows
section 4.4 of the protocol.

### Nested-header depth

A clone of PyJWT at commit `7d5ef55e42ce42221f58dc49943e92ccad1fa66a` in
`work/nested-depth/pyjwt`, and 3 environments without packages,
`work/nested-depth/venvs/py312` (from `/usr/bin/python3.12`), `py313` and
`py314` (from the builds in `work/pythons/`), each made with `uv venv -p`:

    python3 -I -B nested-depth/depth_runs.py --dry
    python3 -I -B nested-depth/depth_runs.py

The second command writes `nested-depth/results.jsonl`.

### Tests of the scripts

They run the 4 scripts on the synthetic package
`../target-reach/tests/fixture/toy` and on synthetic files, never on a library
of the study (`tests/conftest.py`, lines 1-4):

    uv venv -p /usr/bin/python3.12 work/tests-venv
    uv pip install --only-binary :all: -p work/tests-venv/bin/python \
        pytest==9.2.0 iniconfig==2.3.1 packaging==26.3 pluggy==1.7.0 Pygments==2.21.0
    work/tests-venv/bin/python -B -m pytest -q -p no:cacheprovider tests
