"""Count 'checks' = distinct (function, raised class, message template) per function.
Usage: python3 -I checks.py <file> [<file> ...]
Message template: the unparsed args of the raise call with f-string values replaced by {}.
Bare 're-raise' (raise without exc) and 'raise X from e' are reported; bare raise skipped.
Only parses with ast."""
import ast, sys, collections


class T(ast.NodeTransformer):
    def visit_FormattedValue(self, n):
        return ast.Constant("{}")


def tmpl(args):
    out = []
    for a in args:
        a = T().visit(ast.parse(ast.unparse(a), mode="eval")).body
        out.append(ast.unparse(a))
    return ", ".join(out)


checks = set()
for p in sys.argv[1:]:
    tree = ast.parse(open(p, encoding="utf-8").read())

    def walk(node, stack):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                walk(ch, stack + [ch.name])
            else:
                if isinstance(ch, ast.Raise) and ch.exc is not None:
                    e = ch.exc
                    if isinstance(e, ast.Call):
                        cls = ast.unparse(e.func)
                        t = tmpl(e.args + [k.value for k in e.keywords])
                    else:
                        cls = ast.unparse(e)
                        t = "<no-call>"
                    checks.add((p.split("/src/")[-1], ".".join(stack) or "<module>", cls, t))
                walk(ch, stack)

    walk(tree, [])

for c in sorted(checks):
    print("\t".join(c))
cnt = collections.Counter(c[2] for c in checks)
print("TOTAL_CHECKS", len(checks))
print("BY_CLASS", cnt.most_common())
