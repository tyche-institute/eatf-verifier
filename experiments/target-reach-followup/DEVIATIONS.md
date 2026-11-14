# Deviations from the protocol

`PROTOCOL.md`, section 6, asks that a defect of a program found after the
protocol commit be corrected and described here with the change, and that
every run that used the program be repeated; a correction of form of a labels
file is listed here too. Times are in Coordinated Universal Time (UTC), on
14 November 2026.

## 1. Defects of the programs

### 1.1 The wording of 1 kind of assertion in the reading pack

`labels/prepare.py` writes the assertions of a block as text into the column
`assertions` of `blocks.tsv`. For the statement `excinfo.match(pattern)` made
after a block, the text was "after the block: re.match <pattern> on the
exception". pytest searches the pattern in the text of the exception; it does
not match from the start of the text. The first experiment computes a search
as well (`reach/targets.py`), so no target and no count of the first
experiment is affected. The wording of the pack could be read as a match from
the start of the text, which removes more checks than the assertion does.

The defect was found from a remark returned with reading A of google-auth, at
14:17, before a labels file was compared with a record, a target or another
reading, and before reading B started.

Change: 1 line of `labels/prepare.py`; the text is now "after the block:
re.search <pattern> in str(exception)". A unit test fixes the texts of the 5
kinds of assertion (`labels/tests/test_labels.py`).

Runs repeated:

- The 4 packs and their parts were built again at 14:20:08. The packs of
  oauthlib, authlib and joserfc, and their parts, are byte for byte equal to
  the first build: no block of the 3 libraries carries an assertion of this
  kind. The pack of google-auth differs in the column `assertions` of 14 of
  the 17 rows of `blocks.tsv` and in the line of that file in `MANIFEST.txt`,
  and in nothing else.
- Reading A of google-auth was repeated on the corrected pack. The labels of
  the first run are kept in `labels/readings/google-auth/A-first-pack.tsv`;
  no analysis reads that file.
- Reading B used the corrected pack of google-auth from its start.

### 1.2 The trace plugin read an environment variable inside its callback

`trace/plugin.py` took the test id of a start from the environment variable
`PYTEST_CURRENT_TEST`, with a call of `os.environ.get` inside the callback of
`sys.monitoring`. 3 tests of google-auth replace `os.environ.get` for their
duration (`tests/oauth2/test_webauthn_handler.py`, 2 tests, and
`tests/oauth2/test_webauthn_handler_factory.py`, 1 test). Under the plugin the
call of the callback reached the replaced function, and the 3 tests failed in
each of the 3 traced runs, while all 2349 tests passed in the 3 runs without
the plugin. Sentinel T3 did not hold for google-auth (2346 passing tests
against 2349 deposited), and the step stopped for that library, as section
4.2 of the protocol asks. The traced runs of joserfc, authlib and oauthlib
had ended with every sentinel holding.

Change: the callback calls nothing that a test can replace. The test id is
the node id that pytest passes to its `pytest_runtest_logstart` hook; the
paths of the subject files are spelled out when the plugin starts, and a file
name is looked up among them without a call of `os`; `threading.get_ident`
and `sys._getframe` are bound when the module is imported. A new sentinel,
T-files, does not hold when a code of a subject file ran under a file name
that is none of the spellings. The synthetic package of the unit tests holds
a test that replaces `os.environ.get` and counts its calls; it fails under
the plugin as it was and passes under the corrected one.

Runs repeated: the traced and plain runs of the 4 libraries and of the 3
development subjects, 3 repeats each, with the corrected plugin. No output of
the first runs is used. Rule 3 had not been computed for any of the 4
libraries when the defect was found, and no labels file had been compared.
