# usage: python3 -I checks.py <file> [<file>...]  ; env FUNCS=regex limits functions (qualified name)
import ast, sys, os, re, collections
fre = re.compile(os.environ.get('FUNCS','.*'))
def tmpl(n):
    if n is None: return ''
    if isinstance(n, ast.Constant): return repr(n.value)
    if isinstance(n, ast.JoinedStr):
        return 'f'+repr(''.join(v.value if isinstance(v,ast.Constant) else '{}' for v in n.values))
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod): return tmpl(n.left)+' % ...'
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr=='format': return tmpl(n.func.value)+'.format(...)'
    return '<'+ast.unparse(n)[:60]+'>'
def cname(e):
    if e is None: return '<reraise>'
    f = e.func if isinstance(e, ast.Call) else e
    return ast.unparse(f)
def msg(e):
    if isinstance(e, ast.Call):
        if e.args: return tmpl(e.args[0])
        if e.keywords: return '<kw:'+','.join(k.arg or '**' for k in e.keywords)+'>'
        return '()'
    return '<noargs>'
tot=0; byclass=collections.Counter()
for path in sys.argv[1:]:
    tree = ast.parse(open(path).read())
    def visit(node, qual):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                q = qual+'.'+ch.name if qual else ch.name
                if not isinstance(ch, ast.ClassDef):
                    if fre.search(q):
                        seen=collections.OrderedDict()
                        for r in walk_fn(ch):
                            if r.exc is None: continue
                            k=(cname(r.exc), msg(r.exc)); seen.setdefault(k,[]).append(r.lineno)
                        for (c,m),ls in seen.items():
                            print(f'{os.path.basename(path)}\t{q}\t{c}\t{m}\t{ls}')
                            global tot; tot+=1; byclass[c]+=1
                visit(ch, q)
    def walk_fn(fn):
        st=list(ast.iter_child_nodes(fn))
        while st:
            n=st.pop()
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda)): continue
            if isinstance(n, ast.Raise): yield n
            st.extend(ast.iter_child_nodes(n))
    visit(tree,'')
print('TOTAL_CHECKS',tot); print('BY_CLASS',byclass.most_common())
