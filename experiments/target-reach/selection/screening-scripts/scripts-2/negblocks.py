import ast, sys, collections, os
# usage: negblocks.py ENTRYNAMES(comma) CLASSES(comma) file_or_dir...
entries=set(sys.argv[1].split(',')); classes=set(sys.argv[2].split(','))
files=[]
for p in sys.argv[3:]:
    if os.path.isdir(p):
        for r,_,fs in os.walk(p):
            files+= [os.path.join(r,f) for f in fs if f.endswith('.py')]
    else: files.append(p)
def names_called(nodes):
    s=set()
    for n in nodes:
        for x in ast.walk(n):
            if isinstance(x, ast.Call):
                f=x.func
                if isinstance(f, ast.Attribute): s.add(f.attr)
                elif isinstance(f, ast.Name): s.add(f.id)
            # callable passed as argument
            if isinstance(x, ast.Attribute): s.add(x.attr)
            if isinstance(x, ast.Name): s.add(x.id)
    return s
def clsname(n):
    if isinstance(n, ast.Tuple): return [clsname(e)[0] for e in n.elts]
    return [ast.unparse(n).split('.')[-1]]
res=[]
for path in sorted(files):
    tree=ast.parse(open(path).read())
    # map stmt -> following siblings for message-after-block detection
    for parent in ast.walk(tree):
        for field in ('body','orelse','finalbody'):
            body=getattr(parent, field, None)
            if not isinstance(body, list): continue
            for i, st in enumerate(body):
                kinds=[]
                if isinstance(st, ast.With):
                    for it in st.items:
                        c=it.context_expr
                        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in ('raises','assertRaises','assertRaisesRegex') and c.args:
                            match = c.func.attr=='assertRaisesRegex' or any(k.arg=='match' for k in c.keywords) or len(c.args)>1 and c.func.attr=='assertRaisesRegex'
                            var = it.optional_vars.id if isinstance(it.optional_vars, ast.Name) else None
                            kinds.append((clsname(c.args[0]), match, var, st.body))
                elif isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
                    c=st.value
                    if isinstance(c.func, ast.Attribute) and c.func.attr in ('raises','assertRaises','assertRaisesRegex') and len(c.args)>=2:
                        match = c.func.attr=='assertRaisesRegex' or any(k.arg=='match' for k in c.keywords)
                        kinds.append((clsname(c.args[0]), match, None, [ast.Expr(ast.Tuple(c.args[1:] if c.func.attr!='assertRaisesRegex' else c.args[2:], ast.Load()))]))
                for cl, match, var, blk in kinds:
                    called=names_called(blk)
                    if not (entries & called): continue
                    if not (set(cl) & classes): continue
                    after=False
                    if var and not match:
                        for nxt in body[i+1:]:
                            for x in ast.walk(nxt):
                                if isinstance(x, ast.Name) and x.id==var: after=True
                    res.append((path, st.lineno, '/'.join(cl), match, after))
cnt=collections.Counter()
for r in res:
    print(*r, sep=' | ')
    cnt['total']+=1; cnt['msg' if (r[3] or r[4]) else 'classonly']+=1
print(dict(cnt)); print(collections.Counter(r[2] for r in res).most_common())
