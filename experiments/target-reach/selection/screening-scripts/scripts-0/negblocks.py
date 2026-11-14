"""List negative-test blocks (pytest.raises / assertRaises / assertRaisesRegex) in test files.
Usage: python3 -I negblocks.py <testdir> <entrypoint-regex> [exc-regex]
Prints one line per block whose body (or callable arg) calls a name matching entrypoint-regex
and whose expected exception matches exc-regex. Only parses with ast."""
import ast, os, re, sys

root, ep_re = sys.argv[1], re.compile(sys.argv[2])
exc_re = re.compile(sys.argv[3]) if len(sys.argv) > 3 else re.compile(".")


def name_of(n):
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        return n.attr
    if isinstance(n, ast.Call):
        return name_of(n.func)
    return ""


def exc_names(n):
    if isinstance(n, ast.Tuple):
        return [x for e in n.elts for x in exc_names(e)]
    return [ast.unparse(n)]


def called(nodes):
    out = set()
    for nd in nodes:
        for c in ast.walk(nd):
            if isinstance(c, ast.Call):
                out.add(name_of(c.func))
            if isinstance(c, (ast.Name, ast.Attribute)):
                out.add(name_of(c))  # names passed as callables
    return out


def kind(call):
    f = call.func
    nm = name_of(f)
    if nm == "raises" and isinstance(f, ast.Attribute) and name_of(f.value) == "pytest":
        return "pytest.raises"
    if nm in ("assertRaises", "assertRaisesRegex", "assertRaisesRegexp"):
        return nm
    return None


total = 0
per = {"class_only": 0, "message": 0}
exc_count = {}
for dp, dn, fn in os.walk(root):
    for f in fn:
        if not f.endswith(".py"):
            continue
        p = os.path.join(dp, f)
        try:
            tree = ast.parse(open(p, encoding="utf-8", errors="replace").read())
        except SyntaxError:
            print("SYNTAXERR", p)
            continue
        # map with-blocks
        for node in ast.walk(tree):
            blocks = []
            if isinstance(node, (ast.With, ast.AsyncWith)):
                for it in node.items:
                    c = it.context_expr
                    if isinstance(c, ast.Call) and kind(c) and c.args:
                        k = kind(c)
                        msg = k.startswith("assertRaisesRegex") or any(kw.arg == "match" for kw in c.keywords)
                        # str(exc) assertion after the block, within the parent body
                        if not msg and it.optional_vars is not None:
                            v = ast.unparse(it.optional_vars)
                            msg = "AFTER?" + v
                        blocks.append((k, c.args[0], node.body, msg, node.lineno))
            elif isinstance(node, ast.Call) and kind(node) and len(node.args) >= (3 if kind(node).startswith("assertRaisesRegex") else 2):
                k = kind(node)
                msg = k.startswith("assertRaisesRegex") or any(kw.arg == "match" for kw in node.keywords)
                rest = node.args[2:] if k.startswith("assertRaisesRegex") else node.args[1:]
                blocks.append((k, node.args[0], rest, msg, node.lineno))
            for k, exc, body, msg, ln in blocks:
                names = called(body)
                hit = sorted(n for n in names if ep_re.fullmatch(n))
                ex = exc_names(exc)
                if not hit or not any(exc_re.search(e) for e in ex):
                    continue
                total += 1
                print(f"{p}:{ln}\t{k}\t{'|'.join(ex)}\t{','.join(hit)}\tmsg={msg}")
                for e in ex:
                    exc_count[e] = exc_count.get(e, 0) + 1
print("TOTAL", total)
print("EXC", exc_count)
