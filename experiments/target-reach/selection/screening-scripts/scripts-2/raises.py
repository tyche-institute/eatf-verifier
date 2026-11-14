import ast, sys, collections
# usage: raises.py file [file...]; prints per-function raise checks (func, class, message template)
def tmpl(n):
    if n is None: return ''
    if isinstance(n, ast.Constant): return repr(n.value)
    if isinstance(n, ast.JoinedStr):
        return 'f:'+''.join(v.value if isinstance(v, ast.Constant) else '{}' for v in n.values)
    if isinstance(n, ast.BinOp): return '%:'+tmpl(n.left)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr=='format': return 'fmt:'+tmpl(n.func.value)
    return ast.dump(n)[:60]
checks=set()
for path in sys.argv[1:]:
    tree=ast.parse(open(path).read())
    def walk(node, stack):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                walk(ch, stack+[ch.name])
            else:
                if isinstance(ch, ast.Raise) and ch.exc is not None:
                    e=ch.exc
                    if isinstance(e, ast.Call):
                        cls=ast.unparse(e.func); msg=tmpl(e.args[0]) if e.args else ''
                    else:
                        cls=ast.unparse(e); msg='<noargs/reraise>'
                    checks.add((path.split('/')[-1], '.'.join(stack), cls, msg, ch.lineno))
                walk(ch, stack)
    walk(tree, [])
uniq=collections.OrderedDict()
for f,fn,c,m,l in sorted(checks, key=lambda x:(x[0],x[4])):
    uniq.setdefault((f,fn,c,m),l)
for k,l in uniq.items(): print(l, *k, sep=' | ')
print('TOTAL checks', len(uniq))
print(collections.Counter(k[2] for k in uniq).most_common())
