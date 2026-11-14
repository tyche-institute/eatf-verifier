# usage: python3 -I raises.py file.py [file.py...]  -- lists checks = (file, function, exc class, message template)
import ast, sys, collections
def tmpl(node):
    if node is None: return "<bare re-raise>"
    call = node
    if isinstance(call, ast.Call):
        name = ast.unparse(call.func)
        if call.args:
            a = call.args[0]
            if isinstance(a, ast.Constant): m = repr(a.value)
            elif isinstance(a, ast.JoinedStr):
                m = "f:" + "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in a.values)
            else: m = "<expr:" + ast.unparse(a)[:40] + ">"
        else: m = "<no msg>"
        return name + " | " + m
    return ast.unparse(call) + " | <var>"
checks = collections.OrderedDict()
for path in sys.argv[1:]:
    tree = ast.parse(open(path).read())
    def walk(n, fn):
        for c in ast.iter_child_nodes(n):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(c, fn + "." + c.name if fn else c.name)
            elif isinstance(c, ast.ClassDef):
                walk(c, (fn + "." if fn else "") + c.name)
            else:
                if isinstance(c, ast.Raise):
                    k = (path.split("/")[-1], fn, tmpl(c.exc))
                    checks.setdefault(k, []).append(c.lineno)
                walk(c, fn)
    walk(tree, "")
for k, v in checks.items(): print(k[0], k[1], "::", k[2], v)
print("TOTAL checks:", len(checks))
cls = collections.Counter(k[2].split(" | ")[0] for k in checks)
print(cls.most_common())
