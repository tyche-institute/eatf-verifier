# Inputs of 3 second scripts

Three of the second scripts in `work/verify-A` to `work/verify-D` read files
outside the tracked tree: `work/verify-A/recompute_a.py`,
`work/verify-D/derive.py` and `work/verify-D/rerun.py`. Some of these files are
written by other scripts, and the others are the clone of PyJWT and the virtual
environment of the PyJWT analysis. This folder was added on 17 November 2026.
It holds copies of the written files and the SHA-256 of the files of the
clone, so that the inputs can be checked without re-running the scripts that
write them. The second scripts are unchanged and still read the original
paths.

## Copies

Each copy was compared byte for byte with its original when it was made, with
2 exceptions given below, and `SHA256SUMS` lists the SHA-256 of each copy. A
copy stands at the path of its original under `experiments/`, without the
folder `work/`, which the ignore rule of each experiment leaves out of the
tracked tree.

| Copy | Original, under `experiments/` | Read by | Written by | Modified (UTC) | Bytes |
|---|---|---|---|---|---|
| `mutation-adequacy/cases.json` | `mutation-adequacy/work/cases.json` | `work/verify-A/recompute_a.py` | `cases.py` of the verifier's mutation analysis | 2026-11-12 06:39:53Z | 12287 |
| `mutation-adequacy-pyjwt/records/baseline/base-1.json` | `mutation-adequacy-pyjwt/work/records/baseline/base-1.json` | `work/verify-D/rerun.py` | the first baseline run of the PyJWT analysis (`run_s2.py`) | 2026-11-12 19:51:34Z | 142880 |
| `mutation-adequacy-robustness/copies/R/jws.segment-encoding/jwt/api_jws.py` | `mutation-adequacy-robustness/work/copies/R/jws.segment-encoding/jwt/api_jws.py` | `work/verify-D/rerun.py` | `handler_variant.py` (analysis D) | 2026-11-14 02:57:57Z | 17705 |
| `mutation-adequacy-robustness/copies/R/jwt.iat-type/jwt/api_jwt.py` | `mutation-adequacy-robustness/work/copies/R/jwt.iat-type/jwt/api_jwt.py` | `work/verify-D/rerun.py` | `handler_variant.py` (analysis D) | 2026-11-14 02:57:57Z | 22239 |
| `mutation-adequacy-robustness/copies/R/jws.header-json/jwt/api_jws.py` | `mutation-adequacy-robustness/work/copies/R/jws.header-json/jwt/api_jws.py` | `work/verify-D/rerun.py` | `handler_variant.py` (analysis D) | 2026-11-14 02:57:57Z | 17863 |

The times of modification are those that the file system gave for the
originals on 17 November 2026. The repository does not record them. All are
earlier than the runs of the second scripts on 15 November 2026. To run the
3 scripts without re-running the scripts that write these files, copy each
file to its original path.

The 2 exceptions are the 2 JSON files. In the 25 cases of `cases.json`, the
fields `package` and `signer_pin_pem` gave 27 paths of files as absolute
paths on the machine of the runs, and in the baseline record the fields `cwd`
and `package_dir` of `env` gave 2 more. Each copy gives these paths relative
to the root of the repository and is otherwise the same. `recompute_a.py`
reads neither field of the cases, and on 17 November 2026, run on the copy in
a scratch tree, it wrote `work/verify-A/recomputed-a.json` byte for byte.
Neither `rerun.py` nor `analyse_s2.py`, whose functions it calls, reads the
`env` of a record. The originals had these SHA-256:

- `mutation-adequacy/work/cases.json`: `ae4d68f5636dfd764b5b1ad9787f1f5bd235661e2cfbd2350d8158c384892e66`
- `mutation-adequacy-pyjwt/work/records/baseline/base-1.json`: `1eae781a5e3f56f5f67ab191a26c4cc202bc044b9c963ed21aeacef9f5526519`

The 3 files under `mutation-adequacy-robustness/copies/R/` are files of PyJWT
2.15.1 with the edit of analysis D. PyJWT is under the MIT license, and
`LICENSE-PyJWT` is its license file at the commit given below.

## Clone and environment

`derive.py` reads the source files of the checks in
`../mutation-adequacy-pyjwt/work/pyjwt`, and `rerun.py` copies `jwt/`,
`tests/` and `pyproject.toml` of that clone. On 17 November 2026 the clone was
at commit `7d5ef55e42ce42221f58dc49943e92ccad1fa66a` (PyJWT 2.15.1), with no changed and no untracked file.
`pyjwt-7d5ef55.sha256` lists the SHA-256 of these 58 files, and
each file was byte for byte the file of that commit.

`rerun.py` runs its copies with the Python of
`../mutation-adequacy-pyjwt/work/venv`. On 17 November 2026 that environment
ran Python 3.12.3, and the packages that `pip freeze` listed were exactly those
of `../mutation-adequacy-pyjwt/generated/pip-freeze.txt`.

## Check

```sh
cd experiments/mutation-adequacy-robustness/second-script-inputs
sha256sum -c SHA256SUMS
(cd ../../mutation-adequacy-pyjwt/work/pyjwt && sha256sum -c -) < pyjwt-7d5ef55.sha256
```
