# Analysis B: operator classes that both tools have

Exploratory and post hoc (PROTOCOL.md, section B). Input: the deposited `mutants.csv`, `operators.csv` and `gap-directions.csv` of `../mutation-adequacy/`. The Python port was mutated by mutmut 3.8.1 and the TypeScript port by StrykerJS 9.6.1. A gap mutant is killed under O_C and not under O_V; its direction is the one the first study recorded.

Shared classes, as fixed in the protocol:

| Class | mutmut 3.8.1 | StrykerJS 9.6.1 |
|---|---|---|
| operator replacement | `swap_op` | `ArithmeticOperator`, `EqualityOperator`, `LogicalOperator`, `UnaryOperator`, `AssignmentOperator` |
| boolean literal and negation | `name`, `remove_unary_ops` | `BooleanLiteral` |
| string literal | `string` | `StringLiteral` |
| method swap | `symmetric_string_methods_swap`, `unsymmetrical_string_methods_swap` | `MethodExpression` |

Listed operators with no mutant in the python port: `unsymmetrical_string_methods_swap`.

## All mutants

| Port | Group | Mutants | Kills O_V | Kills O_C | Gap | Later guard | Same guard | Earlier guard | No defined code | Mixed | Later-guard share |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| python | all operators | 1149 | 415 | 500 | 85 | 5 | 23 | 1 | 56 | 0 | 5.9% |
| python | shared classes | 477 | 147 | 186 | 39 | 2 | 4 | 1 | 32 | 0 | 5.1% |
| python | operator replacement | 44 | 23 | 25 | 2 | 1 | 1 | 0 | 0 | 0 | 50.0% |
| python | boolean literal and negation | 52 | 26 | 31 | 5 | 1 | 3 | 1 | 0 | 0 | 20.0% |
| python | string literal | 378 | 95 | 127 | 32 | 0 | 0 | 0 | 32 | 0 | 0.0% |
| python | method swap | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| python | outside the table | 672 | 268 | 314 | 46 | 3 | 19 | 0 | 24 | 0 | 6.5% |
| typescript | all operators | 854 | 291 | 373 | 82 | 39 | 26 | 1 | 16 | 0 | 47.6% |
| typescript | shared classes | 440 | 147 | 183 | 36 | 8 | 11 | 1 | 16 | 0 | 22.2% |
| typescript | operator replacement | 136 | 59 | 70 | 11 | 4 | 7 | 0 | 0 | 0 | 36.4% |
| typescript | boolean literal and negation | 54 | 29 | 35 | 6 | 1 | 4 | 1 | 0 | 0 | 16.7% |
| typescript | string literal | 227 | 55 | 74 | 19 | 3 | 0 | 0 | 16 | 0 | 15.8% |
| typescript | method swap | 23 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| typescript | outside the table | 414 | 144 | 190 | 46 | 31 | 15 | 0 | 0 | 0 | 67.4% |

## Without the mutants that only change a failure-code literal (supplement)

| Port | Group | Mutants | Kills O_V | Kills O_C | Gap | Later guard | Same guard | Earlier guard | No defined code | Mixed | Later-guard share |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| python | all operators | 1075 | 415 | 455 | 40 | 5 | 23 | 1 | 11 | 0 | 12.5% |
| python | shared classes | 425 | 147 | 154 | 7 | 2 | 4 | 1 | 0 | 0 | 28.6% |
| python | operator replacement | 44 | 23 | 25 | 2 | 1 | 1 | 0 | 0 | 0 | 50.0% |
| python | boolean literal and negation | 52 | 26 | 31 | 5 | 1 | 3 | 1 | 0 | 0 | 20.0% |
| python | string literal | 326 | 95 | 95 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| python | method swap | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| python | outside the table | 650 | 268 | 301 | 33 | 3 | 19 | 0 | 11 | 0 | 9.1% |
| typescript | all operators | 828 | 291 | 357 | 66 | 39 | 26 | 1 | 0 | 0 | 59.1% |
| typescript | shared classes | 414 | 147 | 167 | 20 | 8 | 11 | 1 | 0 | 0 | 40.0% |
| typescript | operator replacement | 136 | 59 | 70 | 11 | 4 | 7 | 0 | 0 | 0 | 36.4% |
| typescript | boolean literal and negation | 54 | 29 | 35 | 6 | 1 | 4 | 1 | 0 | 0 | 16.7% |
| typescript | string literal | 201 | 55 | 58 | 3 | 3 | 0 | 0 | 0 | 0 | 100.0% |
| typescript | method swap | 23 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| typescript | outside the table | 414 | 144 | 190 | 46 | 31 | 15 | 0 | 0 | 0 | 67.4% |

## Sentinels

- `1_totals_reproduce_operators_csv`: passed
- `2_gap_reproduces_gap_directions_csv`: passed
- `3_classes_add_up`: passed
