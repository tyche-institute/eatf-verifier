# usage: python3 -I checks.py file1.py [file2.py ...]
# Per function: group raise statements by (exception class, message template). One group = one check.
import ast, sys, collections
def tmpl(node):
    if isinstance(node, ast.Constant): return repr(node.value)
    if isinstance(node, ast.JoinedStr):
        return 'f"' + ''.join(v.value if isinstance(v, ast.Constant) else '{}' for v in node.values) + '"'
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod): return tmpl(node.left) + ' %'
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'format': return tmpl(node.func.value) + '.format'
    return '<expr:' + ast.unparse(node)[:90] + '>'
def cls(e):
    if isinstance(e, ast.Call):
        n = ast.unparse(e.func); m = tmpl(e.args[0]) if e.args else ''
        return n, m
    return ast.unparse(e), '<noncall>'
total = 0; bycls = collections.Counter()
for path in sys.argv[1:]:
    tree = ast.parse(open(path).read())
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
        groups = collections.Counter()
        for n in ast.walk(fn):
            # skip raises in nested functions
            if isinstance(n, ast.Raise) and n.exc is not None:
                owner = [f for f in ast.walk(fn) if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)) and f is not fn and n in list(ast.walk(f))]
                if owner: continue
                c, m = cls(n.exc)
                if m == '<noncall>' and c[:1].islower(): continue  # re-raise of a variable
                groups[(c, m)] += 1
        for (c, m), k in groups.items():
            total += 1; bycls[c.split('.')[-1]] += 1
            print(f"{path.split('/')[-1]}:{fn.name}\t{c}\t{m}\t(x{k})")
print('TOTAL_CHECKS', total); print('BY_CLASS', bycls.most_common())
