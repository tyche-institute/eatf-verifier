#!/usr/bin/env python3
"""Writes `reach.csv` of this folder from the records `6.record.json` to
`10.record.json` that the scripts 6.py to 10.py wrote, and from the reasons
below, which name the source lines that each result rests on.

    python3 -I -B reach_csv.py

It stops, and writes nothing, when the sample is not the deposited one, when
a record is missing, or when a record's check, row or result does not agree
with the sample.

The columns: first those of PROTOCOL.md, section 4.4, in its order (library,
check, result, entry_point, scripts, settings, exception, reason), then row
(of ../../sample.csv), input (in short), fired (`fires`, `does not fire` or
`undecided`: whether a RAISE event of the call passed the firing test of
T/reach/recorder.py, lines 237-270), record, and source_lines (the lines read,
by file, relative to the root of the copy). Paths of this experiment are
relative to the folder of PROTOCOL.md.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
X = HERE.parents[2]
SAMPLE = X / "no-fire" / "sample.csv"
SAMPLE_SHA256 = "5637e6bc9241273992552eb79331b9e5095ee5c8e8b291afc718f2efeea3a8fa"  # no-fire/README.md
LIBRARY = "oauthlib"
FOLDER = "no-fire/reach/oauthlib"

AC = "oauthlib/oauth2/rfc6749/grant_types/authorization_code.py"
GB = "oauthlib/oauth2/rfc6749/grant_types/base.py"
RV = "oauthlib/oauth2/rfc6749/request_validator.py"
DC = "oauthlib/oauth2/rfc8628/grant_types/device_code.py"
RV8 = "oauthlib/oauth2/rfc8628/request_validator.py"
CM = "oauthlib/common.py"
ER = "oauthlib/oauth2/rfc6749/errors.py"
EB = "oauthlib/oauth2/rfc6749/endpoints/base.py"
TK = "oauthlib/oauth2/rfc6749/endpoints/token.py"
PC = "oauthlib/oauth2/rfc6749/endpoints/pre_configured.py"


def client_auth(default: str) -> str:
    return (f"client authentication passes ({GB} 223-224: client_authentication_required answers True, "
            f"{default}; then 184-196: authenticate_client answers True, request.client has a client_id, "
            f"and request.client_id is taken from it at 196)")


CLIENT_AUTH = client_auth(f"the library's default ({RV} 39)")

REASONS = {
    6: (f"The raise statement at {AC}:510 executed and its exception reached the caller. On the way, in "
        f"{AC}: 442 grant_type is authorization_code; 445 no pre_token validator; 448 code present; "
        f"452-453 no duplicate client_id, grant_type or redirect_uri; 457 {CLIENT_AUTH}; 460 "
        f"validate_grant_type passes ({GB} 157-159); 464-465 validate_code answers True; 471 "
        f"get_code_challenge answers None, the library's default ({RV} 645), so 473 skips the PKCE "
        f"tests; 492 is_pkce_required answers False, the default ({RV} 616); 504 the request carries no "
        f"redirect_uri, so 505-507 ask get_default_redirect_uri, which answers None; 509 no redirect URI; "
        f"510 raise."),
    7: (f"The raise statement at {EB}:79-80 executed and its exception reached the caller. On the way: "
        f"{TK} 118 calls _raise_on_bad_method; {EB} 76 reads valid_request_methods, which on a "
        f"WebApplicationServer is the class attribute ('POST',) of IntrospectEndpoint "
        f"(oauthlib/oauth2/rfc6749/endpoints/introspect.py 39), the first class of the method resolution "
        f"order that defines the name (record, facts; {PC} 96-98), so the property of BaseEndpoint "
        f"({EB} 26-28) is not used and the ValueError of {EB}:77 is not raised; 78 GET is not in "
        f"('POST',); 79-80 raise. The call reaches no method of the request validator."),
    8: (f"The raise statement at {GB}:162 executed and its exception reached the caller. On the way, in "
        f"{AC}: 442 grant_type is authorization_code; 445 no pre_token validator; 448 code present; "
        f"452-453 no duplicate parameter; 457 {CLIENT_AUTH}; 460 calls validate_grant_type ({GB} 152): "
        f"157 client_id; 158-159 the request validator answers False for the grant type "
        f"authorization_code; 160-161 log; 162 raise."),
    9: (f"The raise statement at {DC}:125-127 executed (lines 125 and 126; line 127 holds only the closing "
        f"parenthesis and has no line event) and its exception reached the caller. On the way, in {DC}: "
        f"121 no pre_token validator; 124 getattr(request, 'grant_type', None) is None, since the body "
        f"carries no grant_type and a Request answers None for a parameter it knows and does not carry "
        f"({CM} 360-397 and 399-401); 125-127 raise. The call reaches no method of the request validator."),
    10: (f"The raise statement at {DC}:202 executed and its exception reached the caller. On the way, in "
         f"{DC}: 121 no pre_token validator; 124 grant_type present; 129 it is "
         f"urn:ietf:params:oauth:grant-type:device_code; 132-133 no duplicate grant_type or scope; 138 "
         f"{client_auth(f'the default of {RV8} 25')}; "
         f"141 validate_grant_type passes ({GB} 157-159); 147 calls validate_device_code: 164 device_code "
         f"present; 169-171 the request validator answers None; 172 None is not 'authorized'; 189 the map "
         f"of the 4 recognized statuses (lines 20-28) has no entry for None, so 190 does not raise; 196 the "
         f"status is None, so nothing is logged; 202 raise."),
}

SOURCE_LINES = {
    6: (f"{AC} 436-520; {GB} 82-108, 152-162, 178-227; {RV} 12-39, 41-81, 131-143, 448-481, 483-499, "
        f"592-616, 618-645; {CM} 346-435; {ER} 15-73, 143-163, 170-171"),
    7: (f"{TK} 18, 61, 85-119; {EB} 19-34, 75-89; oauthlib/oauth2/rfc6749/endpoints/introspect.py 20, 39; "
        f"oauthlib/oauth2/rfc6749/endpoints/revocation.py 19, 28; {PC} 96-125; {CM} 346-415; "
        f"{ER} 15-73, 186-192; tests/oauth2/rfc6749/endpoints/test_error_responses.py 27-30, 440-466"),
    8: (f"{AC} 436-468; {GB} 82-108, 152-162, 178-227; {RV} 12-39, 41-81, 483-499; {CM} 346-435; "
        f"{ER} 15-73, 305-310"),
    9: (f"{DC} 16-36, 38-59, 116-152, 204-233; {RV8} 1-63; {GB} 82-108; {CM} 346-403; {ER} 15-73, 186-192; "
        f"{TK} 85-119; {PC} 25-93; {AC} 285-307, 442-443"),
    10: (f"{DC} 16-36, 116-202; {RV8} 1-63; {GB} 82-108, 152-162, 178-227; {CM} 346-435; {ER} 15-73, "
         f"292-302"),
}

COLUMNS = ["library", "check", "result", "entry_point", "scripts", "settings", "exception", "reason",
           "row", "input", "fired", "record", "source_lines"]


def main() -> int:
    digest = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
    if digest != SAMPLE_SHA256:
        raise SystemExit(f"{SAMPLE} has SHA-256 {digest}, not the deposited {SAMPLE_SHA256}")
    with SAMPLE.open(newline="", encoding="utf-8") as handle:
        sample = list(csv.DictReader(handle))
    mine = [(n, row) for n, row in enumerate(sample, 1) if row["library"] == LIBRARY]
    if [n for n, _ in mine] != sorted(REASONS):
        raise SystemExit(f"the rows of {LIBRARY} in the sample are {[n for n, _ in mine]}, not {sorted(REASONS)}")
    out = []
    for n, drawn in mine:
        path = HERE / f"{n}.record.json"
        if not path.exists():
            raise SystemExit(f"{path} is missing: run {n}.py first")
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec["row"] != n or rec["check"] != drawn["check"] or rec["library"] != LIBRARY:
            raise SystemExit(f"{path.name} is the record of row {rec['row']}, {rec['check']}, not of row {n}")
        if rec["result"] != "reached" or not rec["raise_lines_executed"]:
            raise SystemExit(f"{path.name}: the check is not reached by its input; this table has no row for it")
        ep, exc = rec["entry_point"], rec["exception"]
        site = exc["raise_site"]
        out.append({
            "library": LIBRARY,
            "check": rec["check"],
            "result": "reached",
            "entry_point": f"{ep['qualname']} ({ep['file']}:{ep['line']}), called on {ep['called_on']}",
            "scripts": f"{FOLDER}/{n}.py, with {FOLDER}/trace_input.py",
            "settings": " | ".join(rec["settings"]),
            "exception": (f"{exc['class']} (error {exc['error']}, description {json.dumps(exc['description'])}, "
                          f"status {exc['status_code']}), raised at {site['file']}:{site['line']}, the check "
                          f"{site['check']}"),
            "reason": REASONS[n],
            "row": n,
            "input": rec["input"],
            "fired": "fires" if rec["fired"] else "does not fire",
            "record": f"{FOLDER}/{n}.record.json",
            "source_lines": SOURCE_LINES[n],
        })
    target = HERE / "reach.csv"
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)
    print(f"{target.name}: {len(out)} rows, rows {[r['row'] for r in out]} of the sample; results "
          f"{sorted({r['result'] for r in out})}; fired {sorted({r['fired'] for r in out})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
