# Deviations from the protocol

`PROTOCOL.md`, section 6, asks that every defect of the toolkit found during
the run, every change of `reach/analyse.py` or `reach/report.py` after the
protocol commit, and every other departure be listed here. Times are in
Coordinated Universal Time (UTC).

| | |
|---|---|
| Protocol commit | `b93e078770feeebbb1e9b7824f0d4a42f515b4e6`, time-stamped 14 November 2026, 09:22:14 |
| Commit of the 4 `targets.json` files | `0a026ca9fc7e62155a0e2401ca7bb96dec4f1ac6`, time-stamped 14 November 2026, 09:25:09 and 09:25:10 |
| Step 3, the 4 libraries in rank order | 14 November 2026, 09:25:35 to 09:35:51 |
| Steps 4 and 5, readings and witness tests | 14 November 2026, 09:38 to 09:51 |
| Step 6, the table across subjects | 14 November 2026, 09:51:48 |
| Step 7, the second computation applied to the 4 libraries | 14 November 2026, 09:51:57 |

## 1. Defects of the toolkit

None was found. No run crashed, and all 7 sentinels hold in each of the 4
libraries. `reach/`, `guard/`, `PROTOCOL.md`, `SELECTION.md` and the
definitions of the subjects are as the protocol commit left them; the only
files under `subjects/` added since are the 4 `targets.json` files of step 2.
No library was run a second time, and no output is superseded.

## 2. Changes of the analysis or of the report after the protocol commit

None. `reach/analyse.py` and `reach/report.py` are unchanged.

## 3. The second computation

The second script agrees with the first analysis on every compared count of
the 7 subjects (`recompute/NOTES.md`). Before its outputs were compared for
the first time, it differed in 1 count of 1 development subject: the blocks
of `pyjwt`, 179 against 215. The sentence of section 4 that defines the count
allows 2 readings for that subject; the first analysis follows the protocol,
and the second script was corrected. No count of the first analysis was
changed. The sentences of the protocol that allow 2 readings are listed in
`recompute/NOTES.md`; none of them changes a count or a verdict of a subject.

## 4. Other departures

**The table across subjects was computed 1 time before steps 4 and 5 were
finished.** Section 6 puts `reach/report.py` (step 6) after the readings
(steps 4 and 5). On 14 November 2026 at 09:39:08, after step 3 and as the
readings began, the table was computed into a folder outside this deposit,
so the verdicts on the 5 expectations were known while the flags and the
undetected deletions were read. The table of the deposit
(`generated/REPORT.md`) was computed after the witness step. The 2 tables
differ only in the 2 rows on witness tests, which did not exist at the first
computation. The classes of the readings are reported apart from the counts
in any case (section 6, step 4).

## 5. Corrections of committed texts

**The period of the download counts.** `SELECTION.md`, section 1, says that
the frame holds the 1,000 most-downloaded projects "over 30 days", and
`selection/frame-top1000.json` names its field `downloads_30d`. The snapshot
of 1 November 2026 counts the downloads of the calendar month before it,
October 2026: the script that writes the snapshot (`clickhouse.py` of the
`top-pypi-packages` project, release 2026.11, read on 14 November 2026)
queries the downloads per month for the month before the day it runs, and
the page of the project records the change as "2025-06: Fetch data for full
month". The snapshot file, its digest, the ranks and the selection do not
change. `SELECTION.md` and the frame file are left as committed.

**The address of the snapshot.** `SELECTION.md` gives
<https://hugovk.github.io/top-pypi-packages/>. On 14 November 2026 that
address redirects to <https://hugovk.dev/top-pypi-packages/>. The release
2026.11 of the project is archived with the Digital Object Identifier (DOI)
10.5281/zenodo.23853731.
