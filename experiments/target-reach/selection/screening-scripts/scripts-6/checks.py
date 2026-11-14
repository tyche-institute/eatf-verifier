"""AST-only check counter. Never imports the analysed code.
usage: python3 -I checks.py ENTRY1,ENTRY2 file1.py [file2.py ...]
Builds a name-based call graph over all functions in the given files
(callee resolved by simple name: f(...) -> any def f; x.m(...) -> any def m;
C(...) where C is a class -> C.__init__/__post_init__). Over-approximate.
From the entry names, walks reachable functions, and lists checks:
distinct (function, exception class, message template) among raise statements.
Bare re-raise (`raise`) and raise of a plain name variable (e.g. `raise e`) are skipped.
"""
import ast, sys, collections

entries = sys.argv[1].split(",")
files = sys.argv[2:]
defs = collections.defaultdict(list)  # simple name -> [(qual, node, file)]
classes = {}
bases = {}
owner = {}
for f in files:
    tree = ast.parse(open(f, encoding="utf-8").read(), f)
    def visit(node, prefix, cls):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, ast.ClassDef):
                classes.setdefault(ch.name, []).append((prefix + ch.name, f))
                bases[ch.name] = [ast.unparse(b).split(".")[-1] for b in ch.bases]
                visit(ch, prefix + ch.name + ".", ch.name)
            elif isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = prefix + ch.name
                defs[ch.name].append((q, ch, f))
                if cls:
                    defs[cls + "." + ch.name].append((q, ch, f))
                    owner[id(ch)] = cls
                visit(ch, q + ".", None)
            else:
                visit(ch, prefix, cls)
    visit(tree, "", None)

def tmpl(node):
    if node is None:
        return ""
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.JoinedStr):
        s = ""
        for v in node.values:
            s += v.value if isinstance(v, ast.Constant) else "{}"
        return "f" + repr(s)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        return tmpl(node.left) + " % ..."
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return tmpl(node.func.value) + ".format(...)"
    return "<" + ast.unparse(node)[:60] + ">"

def callees(fn):
    out = set()
    cls = owner.get(id(fn))
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                nm = n.func.id
                out.add(nm)
                if nm in classes:
                    out.update({nm + ".__init__", nm + ".__post_init__"})
            elif isinstance(n.func, ast.Attribute):
                if n.func.attr.startswith("__"):
                    v = n.func.value
                    if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "super" and cls:
                        for b in bases.get(cls, []):
                            out.add(b + "." + n.func.attr)
                    continue  # other dunder attribute calls skipped
                out.add(n.func.attr)
    return out

seen = set(); order = []
stack = []
for e in entries:
    stack += defs.get(e, [])
    if not defs.get(e):
        print("WARN no def for entry", e)
while stack:
    q, node, f = stack.pop()
    key = (q, f, node.lineno)
    if key in seen:
        continue
    seen.add(key); order.append((q, node, f))
    for c in callees(node):
        stack += defs.get(c, [])

checks = collections.OrderedDict()
for q, node, f in sorted(order, key=lambda t: (t[2], t[1].lineno)):
    for n in ast.walk(node):
        if isinstance(n, ast.Raise) and n.exc is not None:
            exc = n.exc
            if isinstance(exc, ast.Call):
                cls = ast.unparse(exc.func)
                msg = tmpl(exc.args[0]) if exc.args else ""
                if exc.args and isinstance(exc.args[0], ast.Name):
                    # resolve `msg = "..."; raise E(msg)`: nearest preceding assignment in the function
                    best = None
                    for a in ast.walk(node):
                        if isinstance(a, ast.Assign) and a.lineno <= n.lineno and any(isinstance(t, ast.Name) and t.id == exc.args[0].id for t in a.targets):
                            if best is None or a.lineno > best.lineno:
                                best = a
                    if best is not None:
                        msg = "=" + tmpl(best.value)
                if not exc.args and exc.keywords:
                    msg = "kw:" + ",".join(k.arg or "**" for k in exc.keywords)
            elif isinstance(exc, (ast.Name, ast.Attribute)):
                cls = ast.unparse(exc)
                if cls[:1].islower():
                    continue  # raise e (variable)
                msg = ""
            else:
                continue
            k = (q, cls, msg)
            checks.setdefault(k, []).append(n.lineno)

print("reachable functions:", len(order))
print("files reached:", sorted({f for _, _, f in order}))
for (q, cls, msg), lines in checks.items():
    print(f"  {q} | {cls} | {msg[:70]} | lines {lines}")
print("TOTAL checks:", len(checks))
cnt = collections.Counter(cls for (_, cls, _) in checks)
print("by class:", cnt.most_common())
