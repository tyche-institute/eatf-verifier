"""AST-only negative-test-block counter. Never imports the analysed code.
usage: python3 -I negblocks.py ENTRY1,ENTRY2 EXC1,EXC2 testfile.py [...]
Block forms: `with pytest.raises(E...)`, `pytest.raises(E, callable...)`,
`with self.assertRaises(E)`, `self.assertRaises(E, callable...)`, assertRaisesRegex(...).
A block is counted when (a) its expected class (last dotted component, any element of a tuple)
is in EXC list, and (b) its body (with-form) or callable arg (call-form) calls a name in ENTRY list
(simple name or attribute name), either directly or via a helper function defined in the same
test file that calls an entry (one level of indirection).
message-asserted = match= kwarg, assertRaisesRegex, or the `as` name is used later in the
enclosing function in an assert/self.assert* call.
"""
import ast, sys, collections

entries = set(sys.argv[1].split(","))
excs = set(sys.argv[2].split(","))
files = sys.argv[3:]

def called_names(node, refs=True):
    s = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name): s.add(n.func.id)
            elif isinstance(n.func, ast.Attribute): s.add(n.func.attr)
        if refs and isinstance(n, ast.Name): s.add(n.id)  # callable passed by reference
        if refs and isinstance(n, ast.Attribute): s.add(n.attr)
    return s

def exc_names(node):
    if isinstance(node, ast.Tuple):
        return [x for e in node.elts for x in exc_names(e)]
    return [ast.unparse(node).split(".")[-1]]

def kind(call):
    if not isinstance(call, ast.Call): return None
    f = call.func
    nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
    if nm == "raises" and isinstance(f, ast.Attribute) and ast.unparse(f.value) == "pytest": return "raises"
    if nm in ("assertRaises", "assertRaisesRegex", "assertRaisesRegexp"): return nm
    return None

tot = collections.Counter(); per_file = collections.Counter(); excl = collections.Counter()
for path in files:
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    helpers = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("test"):
            helpers[n.name] = called_names(n, refs=False)
    def hits(names):
        if names & entries: return True
        return any(h in names and (helpers[h] & entries) for h in helpers)
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for fn in funcs:
        for n in ast.walk(fn):
            blocks = []
            if isinstance(n, (ast.With, ast.AsyncWith)):
                for it in n.items:
                    k = kind(it.context_expr)
                    if k:
                        asname = it.optional_vars.id if isinstance(it.optional_vars, ast.Name) else None
                        blocks.append((k, it.context_expr, n.body, asname, n))
            elif isinstance(n, ast.Expr) or isinstance(n, ast.Assign):
                c = n.value
                k = kind(c)
                if k and len(c.args) >= (3 if k.startswith("assertRaisesRegex") else 2):
                    blocks.append((k, c, None, None, n))
            for k, call, body, asname, node in blocks:
                if not call.args: continue
                ex = exc_names(call.args[0])
                if not set(ex) & excs:
                    excl["exc-not-listed:" + "/".join(ex)] += 1; continue
                if body is not None:
                    names = set().union(*[called_names(b, refs=False) for b in body])
                else:
                    first = 2 if k.startswith("assertRaisesRegex") else 1
                    names = set().union(*[called_names(a) for a in call.args[first:]])
                if not hits(names):
                    excl["no-entry-call"] += 1; continue
                msg = k.startswith("assertRaisesRegex") or any(kw.arg == "match" for kw in call.keywords)
                if not msg and asname:
                    for m in ast.walk(fn):
                        if (isinstance(m, ast.Assert) or (isinstance(m, ast.Call) and isinstance(m.func, ast.Attribute) and m.func.attr.startswith("assert"))) and getattr(m, "lineno", 0) > node.lineno:
                            if any(isinstance(x, ast.Name) and x.id == asname for x in ast.walk(m)):
                                msg = True; break
                tot["blocks"] += 1; per_file[path.split("/")[-1]] += 1
                tot["msg" if msg else "class_only"] += 1
                tot["form:" + k + ("-with" if body is not None else "-call")] += 1
print("counted:", dict(tot))
print("per file:", dict(per_file))
print("excluded:", dict(excl))
