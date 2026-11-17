# Deviations from the protocol

Each entry gives the date, the departure from `PROTOCOL.md`, the reason, what
it changed and the files changed. Times are UTC and come from the
`runs.jsonl` of each stream of commands in `logs/` and from
`logs/stream-1/by-hand.txt`.

## 1. Steps 3 and 4 ran at the same time (2026-11-17)

Section 6 places step 4, the 103 deletions, after step 3, the screened
libraries; only the reading (step 5) and the depth runs (step 6) may run while
earlier steps run. Steps 3 and 4 were started at the same time, on the same
machine (24 cores), in 2 streams of commands, to shorten the time of the runs:

- stream 1 (`logs/stream-1/`): `reach/run.py` and `reach/analyse.py` for
  `ecdsa`, `python-jose`, `supabase-auth` and `service-identity`, in rank
  order, with the second computation of the last 3, from 15:29:03Z to
  15:32:08Z; `reach/report.py` at 15:32:26Z; the sweep from 15:32:34Z to
  15:33:30Z;
- stream 2 (`logs/stream-2/`): the draw of the sample again (15:29:05Z), the
  103 deletions from 15:29:05Z to 15:40:19Z (`google-auth` 15:29:05Z to
  15:37:26Z, `oauthlib` to 15:37:34Z, `authlib` to 15:39:28Z, `joserfc` to
  15:40:19Z), and the depth runs from 15:40:19Z to 15:40:20Z.

Each stream ran at most 10 workers (`../target-reach/reach/run.py`, line 105;
`no-fire/summary.json`). No command of one stream reads an output of the
other: step 3 reads `screened/` and the clones and environments of the 4
screened libraries that are run, and step 4 reads `no-fire/` and those of the 4 held-out libraries, and each
run makes its own copies in its own work folder. What the overlap could change
is the time that a run takes. No run reached a time limit: 0 deletions
exceeded the time limit and 0 runs were repeated in the main runs of the 4
screened libraries, under the recorder and in the whole suite
(`screened/generated/<name>/summary.json`), 0 of the 103 deletions and 0
control copies timed out (`no-fire/deletions-nofire.csv`), and the 2
unmodified whole-suite runs of each held-out library give the same outcome
for every test (`no-fire/summary.json`).

Files changed: none.

## 2. `ecdsa` left out of its second computation, of the report and of the sweep, which were run again (2026-11-17)

Section 6, step 3, runs the second computation on the records of each
screened library that is run, then `reach/report.py` on the libraries that
gave outputs, then the sweep in 1 call for the libraries that are not reported
as failed; section 4 names `ecdsa` in that call. For `ecdsa`,
`reach/analyse.py` wrote its outputs and ended with exit status 1, because
sentinel 1 does not hold (2 baseline runs and the control copy give identical
records, message texts aside), as section 9 foresaw for tests that draw
random inputs without a seed. The script that ran stream 1 skips the remaining
commands of a library after a command of it fails, so the second computation
of `ecdsa` did not run (`logs/stream-1/runs.jsonl` records its 2 commands as
skipped); the commands of the report and of the sweep, given by
hand after stream 1, named only the other 3 libraries
(`logs/stream-1/by-hand.txt`). `ecdsa` is not reported as failed (section
3.3): it gave its outputs and gets no verdict (section 2).

The 3 steps were run again with the commands of `README.md` ("How to run"),
in the order of section 6 (`logs/stream-3/`): the second computation of
`ecdsa` and its comparison from 15:47:40Z to 15:47:41Z; `reach/report.py` with
the 4 libraries at 15:47:41Z; the sweep in 1 call for the 4 libraries, in
rank order, from 15:47:41Z to 15:48:56Z, with a new work folder that no git
repository holds. `reach/report.py` ends with exit status 1 when a sentinel
does not hold in a library that it names, and it wrote both of its files
(`../target-reach/reach/report.py`, lines 268-276).

The outputs of the first report and of the first sweep are deposited, as
superseded, in `superseded/screened-generated/` and
`superseded/screened-versions/`; the outputs of the second calls are the
result. For the other 3 libraries, the second calls give the same outputs as
the first: their entries in `report.json` and their verdicts on the 5
expectations are the same, their rows of `interpreters.csv`, `outcomes.csv`
and `cases.csv` are the same, and their `<name>.json` of the sweep differ only
in the seconds of the recorder runs and in the name of the work folder, which
the paths of the environments and their commands hold.

Files changed: none of the scripts. `screened/generated/REPORT.md`,
`screened/generated/report.json` and `screened/versions/` are the outputs of
the second calls, and `screened/recompute/ecdsa/` is new.

## 3. Paths of the machine made relative in outputs and logs (2026-11-17)

`no-fire/summary.json`, `nested-depth/results.jsonl`, the `<name>.json`
files of the sweep (in `screened/versions/` and
`superseded/screened-versions/`), and the JSON records and
`name-paths.txt` of `no-fire/reach/authlib/` name folders of the machine on
which they ran, as do the logs of the commands. Before the commit, these paths were made
relative to this folder by a plain replacement of text: the folder of this
experiment by the relative path, the deposit's `experiments/` by `../`, the
work folder that no git repository holds by `<outside>`, and the home folder
by `~`. Nothing else in these files was changed. The interpreters of the
system keep their paths (`/usr/bin/python3.12`).

Files changed: the files named above and the files of `logs/`.

## 4. The scripts of the reading changed between its runs (2026-11-17)

Section 4.4 has the input of each sampled check sought from the source and
kept as a script, so the scripts of `no-fire/reach/` are written during the
reading (step 5 of section 6), after the protocol commit. Section 8 counts a
change of a script of this folder after that commit as a deviation; it is
meant for the scripts that the commit fixes, but the scripts of the reading
were also changed between their runs, and those changes are listed here. Each
is recorded, with its time, in the section of its library in
`no-fire/reach/READING.md`: in `google-auth`, docstrings of `reach_common.py`
and of `3.py` to `5.py` only, between the first, second and third runs, which
give the same result for each check; in `oauthlib`, `trace_input.py`, so that
its records give paths relative to the root of the repository, after the
first run of `6.py`, whose record was replaced; in `authlib`, the shared
harness after the run of 15:52:04Z to 15:52:06Z, and input d of row 15 after
the run of 15:52:47Z, whose scripts and records are deposited in
`superseded/reach-authlib/` (paths made relative, as in entry 3); in `joserfc`,
`reach_harness.py`, so that the records name the interpreter of the
environment and hold `sys.prefix` and the files of 2 dependencies, before a
final pass that gives the results of the 2 earlier passes. In the other 3 libraries, the records of the earlier runs were replaced by
those of the last run and are not kept; their sections state that the
results did not change. No change touched the package, its tests, the
toolkit or the sample. The result of a check is that of the last run of its
script.

Files changed: the scripts named above, during the reading; `superseded/reach-authlib/` is new.

