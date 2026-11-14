# Usage: python3 -I negtests.py <testdir_or_file> [entrypoint names comma-separated]
# Lists negative-test blocks: with pytest.raises/assertRaises/assertRaisesRegex, and call forms.
import ast, sys, os
root = sys.argv[1]; eps = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
files = [root] if root.endswith(".py") else [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if f.endswith(".py")]
def kind(call):
    if not isinstance(call, ast.Call): return None
    n = ast.unparse(call.func)
    if n.endswith("pytest.raises") or n == "raises": return "pytest.raises"
    if n.endswith("assertRaisesRegex") or n.endswith("assertRaisesRegexp"): return "assertRaisesRegex"
    if n.endswith("assertRaises"): return "assertRaises"
    return None
def called(nodes):
    s = set()
    for nd in nodes:
        for x in ast.walk(nd):
            if isinstance(x, ast.Call):
                f = x.func
                s.add(f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else ""))
            if isinstance(x, (ast.Name, ast.Attribute)):
                s.add("REF:" + (x.attr if isinstance(x, ast.Attribute) else x.id))
    return s
tot = 0; hits = 0; msg = 0
for fp in sorted(files):
    try: tree = ast.parse(open(fp, encoding="utf-8-sig").read())
    except Exception as e: print("PARSEFAIL", fp, e); continue
    withcalls = {id(it.context_expr) for n in ast.walk(tree) if isinstance(n,(ast.With,ast.AsyncWith)) for it in n.items}
    parents = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parents[c] = p
    for node in ast.walk(tree):
        blocks = []
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for it in node.items:
                k = kind(it.context_expr)
                if k:
                    ce = it.context_expr
                    has_match = k == "assertRaisesRegex" or any(kw.arg == "match" for kw in ce.keywords)
                    var = it.optional_vars.id if isinstance(it.optional_vars, ast.Name) else None
                    post = False
                    if var:
                        par = parents.get(node)
                        for fld in ("body", "orelse", "finalbody"):
                            lst = getattr(par, fld, None)
                            if isinstance(lst, list) and node in lst:
                                for st in lst[lst.index(node)+1:]:
                                    if isinstance(st, ast.Assert) and var in ast.unparse(st): post = True
                                    if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and "assert" in ast.unparse(st.value.func) and var in ast.unparse(st.value): post = True
                    cargs = ce.args[1:] if ce.args and ast.unparse(ce.args[0]) == "self" else ce.args
                    blocks.append((node.lineno, k, ast.unparse(cargs[0]) if cargs else "?", has_match or post, called(node.body)))
        elif isinstance(node, ast.Call):
            k = kind(node)
            args = node.args[1:] if node.args and ast.unparse(node.args[0]) == "self" else node.args
            if k and id(node) not in withcalls and len(args) >= 2:
                blocks.append((node.lineno, k + "(call)", ast.unparse(args[0]), k == "assertRaisesRegex" or any(kw.arg == "match" for kw in node.keywords), called(args[1:])))
        for (ln, k, e, m, cs) in blocks:
            tot += 1
            sel = eps is None or bool(cs & (eps | {"REF:" + x for x in eps}))
            if sel:
                hits += 1; msg += m
                print(f"{os.path.relpath(fp, root) if not root.endswith('.py') else fp}:{ln}\t{k}\t{e}\tmsg={m}\t" + ",".join(sorted(x for x in cs & (eps | {'REF:'+x for x in eps})) if eps else ""))
print(f"TOTAL blocks={tot} selected={hits} with_message={msg} class_only={hits-msg}")
