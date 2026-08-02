# Facilitator run sheets

All versions use the same prepared six-package corpus. The 60-minute plan is
the conference core. The 45-minute plan removes optional inspection detail;
the 90-minute plan adds local signing.

## 45-minute reduced path

| Time | Activity | Required result |
|---:|---|---|
| 0–5 | State the two policies and the “same canonical bytes” rule. | Participants can distinguish `if-present` from `required`. |
| 5–12 | Inspect and verify `01-valid-hybrid.aep` with both implementations. | Both accept under `required`; RFC 9881 SPKI is visible. |
| 12–25 | Replay signature tamper, pair stripping, and legitimate classical transition. | Participants record the first failure code for each policy. |
| 25–35 | Replay incomplete pair and payload tamper in pairs or as a facilitator demonstration. | Both implementations agree on verdict and first code. |
| 35–42 | Each participant writes the acceptance rule for one relying-party context. | A bounded transition or explicit PQC-required rule exists. |
| 42–45 | Debrief and point to the take-home bundle. | `Cross-language policy mismatches: 0`. |

## 60-minute conference core

| Time | Activity | Required result |
|---:|---|---|
| 0–8 | Frame self-interoperability, RFC 9881, and downgrade policy. | No general PQC overview; the task is defined. |
| 8–18 | Inspect `01-valid-hybrid.aep`; confirm both signatures cover the same canonical bytes. | Key encoding and witness references are identified. |
| 18–28 | Verify the valid package in TypeScript and Python under `required`. | Both accept and report a valid ML-DSA signature. |
| 28–45 | Replay all five controls under both policies. | Expected verdict and first failure code are recorded. |
| 45–53 | Compare pair stripping with the legitimate classical transition package. | Structural binding and relying-party policy are separated. |
| 53–58 | Participants write a minimum acceptance-test matrix for their own format. | Positive interop, tamper, stripping, transition, and encoding rows exist. |
| 58–60 | Close and identify the optional signing exercise. | Offline core is complete. |

## 90-minute extended path

Run the complete 60-minute core, then continue:

| Time | Activity | Required result |
|---:|---|---|
| 60–68 | Generate disposable ML-DSA-65 development keys. | Seed PEM and RFC 9881 public SPKI are created. |
| 68–78 | Sign a fresh local hybrid package. | RSA-4096 and ML-DSA-65 cover the same canonical bytes. |
| 78–85 | Verify the new package with both implementations under `required`. | Both accept independently. |
| 85–90 | Compare output with the prepared corpus and capture questions. | Participants leave with a replayable next step. |

## No-network fallback

If setup fails, the facilitator runs `./workshops/pqc-hybrid-lab/run.sh` and
uses `EXPECTED-TRANSCRIPT.md`. Participants still complete the policy matrix
from the prepared results. No live timestamp authority, hosted service, or
conference network is required.
