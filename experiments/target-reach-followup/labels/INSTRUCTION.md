# Instruction for labeling the target of a negative-test block

This instruction is the whole task. It is applied to 1 reading pack at a time.

## What the pack holds

- `src/`: the source of the library and its tests at 1 commit, in the layout
  of the repository.
- `checks.tsv`: every check of the library. A check is the group of raise
  statements in 1 function that construct the same rejection class with the
  same message template. Columns: `id`, `file`, `function`, `class`, `lines`,
  `template` (the message, with `{*}` for a computed part) and `guards` (the
  conditions that lead to the raise statements).
- `classes.tsv`: the classes of the library with their bases.
- `blocks.tsv`: the blocks to label. A block is 1 place in a test that expects
  a rejection: a `pytest.raises` or `assertRaises` statement, as a `with`
  statement or with a callable. Columns: `block`, `file`, `lines`, `test`,
  `expected` (the expected classes) and `assertions` (what the block asserts
  on the exception beyond its class).
- `labels.tsv`: the file to fill in. It lists the blocks to label, 1 per row.
- `MANIFEST.txt`: the files of the pack with their SHA-256 values.

A pack can be labeled in parts. A part is a list of test files; the rows of
`labels.tsv` whose block lies in 1 of these files are filled in, and the other
rows stay as they are.

Only the files of the pack are used. Nothing is run: no test and no code of
the library. No file outside the pack is opened, and nothing is looked up
elsewhere.

## The question

For each block: **which check is this block written for?** The label is the
check that the test describes, in its own words. It is not a prediction of
which check rejects the input when the test runs.

## The rule

A label is found by narrowing 3 sets of checks.

1. **C_class.** The checks whose class is an expected class of the block, or a
   subclass of one (`classes.tsv`).
2. **C_assert.** The checks of C_class that can satisfy every assertion the
   block makes on the exception: a `match=` pattern, an asserted message, an
   asserted code or attribute. A block that asserts nothing beyond the class
   leaves C_assert equal to C_class.
3. **C_name.** The checks of C_assert whose message or condition is the defect
   that the test names. What the test names is taken from the name of the test
   function and of its class, from its docstring and from its comments, and
   from nothing else.

If exactly 1 check is left, it is the label. If no check or more than 1 check
is left, the label is `none`.

## How to apply it

- **Read the code as text.** The source is read to learn what each check
  tests: its condition, its message, the function it stands in, and which
  functions call that function. A call through `getattr`, through a table of
  functions or through a name imported under another name is followed like any
  other call.
- **Do not decide by the order of execution.** Whether another check stands
  earlier on the path, and would stop the input first, plays no part in the
  label. A thought of that kind goes into the `note` column and leaves the
  label as it is.
- **The input does not name the defect.** The values that the test builds are
  what the test does, not what it says. They are read only to tell apart
  checks with the same message and condition that stand in different places,
  as the next point says.
- **Same check in several places.** When C_name holds checks with the same
  message and condition in different functions, the entry point that the block
  calls decides among them: the label is the one on the path from that entry
  point, when the source shows exactly 1. Otherwise the label is `none`.
- **Several defects, or a generic name.** A test whose name, docstring and
  comments name no single defect (`test_invalid_token`, `test_errors`) gets
  `none`, unless C_assert already holds exactly 1 check.
- **A block run several times.** A block inside a loop gets 1 label when every
  run is described by the same check; when the runs are described by different
  checks, the label is `none`. A block of a parametrized test whose runs are
  described by different checks gets a label per value of the parameter, in
  the form given below.
- **No guessing.** When 2 checks fit equally well, the label is `none`. A
  label of `none` is a valid answer and is expected for a part of the blocks.

## What to write

`labels.tsv` keeps its header and its rows, in their order, with the
tab-separated columns:

- `block`: the block key, as it stands in the file.
- `label`: the `id` of 1 check of `checks.tsv`, or `none`. For a block of a
  parametrized test whose runs are described by different checks:
  `by-param <parameter>: <value>=<id or none>; <value>=<id or none>`, with
  the name of the parameter and every value of it. A value is written as
  pytest writes it in the identifier of the test: the text of a string or a
  number as it stands in the test; for any other value, the name of the
  parameter followed by the position of the value in the list, counted from 0
  (`key0`, `key1`); or the `id` that the test gives the value. A value holds
  no hyphen, no semicolon and no equals sign; a block where this cannot be
  met gets the label `none` with the reason `varies`.
- `basis`: the sets that removed candidates on the way to the label, out of
  `class`, `assert` and `name`, joined by `+` (for example `class`, `assert`,
  `name`, `assert+name`). For the label `none`, the basis is `none`.
- `quote`: the words of the test that the label rests on, copied exactly, at
  most 20 words: the part of the name, the pattern, the docstring or the
  comment. For `none`, the words that were considered.
- `note`: at most 40 words. For `none` it is required and starts with the
  reason: `no-class` (C_class is empty), `generic` (no single defect is
  named), `tie` (2 or more checks fit), or `varies` (the runs of a loop are
  described by different checks). When the entry point chose among checks in
  several places, the note starts with `place`.

Every row of the pack, or of the part, gets a label. No row is added or
removed, and no tab or line break is written inside a cell.
