# First reading of the flags: transcription

The deposited readings of the flags (`../target-reach/readings/<name>/FLAGS.md`)
are prose. Each file here transcribes 1 of them into a table, so that
`analyse_labels.py` can set the check that the first reading names as the
described check beside the target labels of a later reading. The readings
themselves are not changed and not repeated here beyond the quoted sentences.

## Files

`<name>.tsv` for jwcrypto, google-auth, oauthlib, authlib and joserfc, in the
csv excel-tab dialect, with the columns:

| column | content |
|---|---|
| block | block key of the flag, as in `generated/<name>/flags.csv` |
| index | index of the case in the block, as in flags.csv |
| test_node | test node of the flagged case, as in `generated/<name>/cases.csv` |
| class | class of the flag in FLAGS.md: A, B, C or D |
| target | target of the flag, copied from flags.csv |
| deciding_check | deciding check of the flag, copied from flags.csv |
| described_check | full check id of the check that FLAGS.md names as the check the test describes; empty when the reading names no check |
| quote | the sentence of FLAGS.md that names the described check, copied verbatim (2 consecutive sentences where the note says so) |
| note | why the row reads as it does where that is not evident from the quote |

## Method

1. The rows follow flags.csv: 1 row per flag, in its order. Block, index,
   target and deciding check are copied from flags.csv; the test node from
   the row of cases.csv with that block and index whose raise site is not
   its target.
2. The class is the class that FLAGS.md gives the flag.
3. The described check is the check id that the quoted sentence names in
   backquotes. FLAGS.md often writes a suffix of the id (`_decrypt#5` for
   `jwe.JWE._decrypt#5`) or a short prefix that it defines (`ac.` in
   oauthlib); the full id from `subjects/<name>/checks.json` is written,
   and a defined prefix is spelled out in the note.
4. For class A and class B flags, FLAGS.md reads the target as the check the
   test describes; the described check is then the target, and the note
   says so.
5. Where FLAGS.md names a raise statement that is no check (authlib,
   `test_invalid_input`, 6 flags: a raise of a class held in a parameter),
   the described check is empty and the note gives the reason.
6. Where 1 sentence covers several flags (a parameterized test, or several
   test classes), the same sentence is quoted for each of them and the note
   says which part applies.

`check_first.py` checks every file against flags.csv, cases.csv,
checks.json and FLAGS.md (see its docstring): order of the flags, the test
node, the class and the counts per class against the line "Counts: ..." of
FLAGS.md, that every quote occurs in FLAGS.md (white space collapsed) and
that it names the described check.

    python3 -I -B labels/check_first.py

## Counts

| subject | flags | A | B | C | D | without a described check id |
|---|---|---|---|---|---|---|
| jwcrypto | 4 | 0 | 3 | 1 | 0 | 0 |
| google-auth | 2 | 0 | 0 | 2 | 0 | 0 |
| oauthlib | 10 | 0 | 0 | 10 | 0 | 0 |
| authlib | 12 | 0 | 0 | 12 | 0 | 6 |
| joserfc | 60 | 3 | 0 | 57 | 0 | 0 |
| all | 88 | 3 | 3 | 82 | 0 | 6 |

For every class C row with a check id the described check equals the
deciding check, except jwcrypto `test_jwe_decompression_max#1`, where it is
`jwe.JWE._decrypt#5` and the deciding check is `jwe.JWE.decrypt#3`. For the
class A and class B rows it equals the target.

google-auth, oauthlib, authlib and joserfc are held out from development:
for them only FLAGS.md and the deposited flags.csv, cases.csv and
checks.json were read; nothing was run on them.
