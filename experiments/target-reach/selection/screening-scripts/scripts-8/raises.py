import ast, sys, collections
# usage: raises.py file [file...]; prints per function: (exception class, message template) groups = checks
def msg(node):
    if isinstance(node, ast.Call):
        name = ast.unparse(node.func)
        m = ast.unparse(node.args[0]) if node.args else ''
        return name, m
    if node is None: return 'reraise',''
    return ast.unparse(node), ''
tot=collections.Counter(); nchecks=0
for f in sys.argv[1:]:
    t = ast.parse(open(f).read())
    for fn in ast.walk(t):
        if isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)):
            groups=collections.Counter()
            for n in ast.walk(fn):
                if isinstance(n, ast.Raise):
                    groups[msg(n.exc)]+=1
            for (c,m),k in groups.items():
                print(f"{f.split('/lib/')[-1]}:{fn.name}: {c} | {m} x{k}")
                tot[c]+=1; nchecks+=1
print("CHECKS", nchecks, tot.most_common())
