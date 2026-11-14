import ast, sys, collections
# usage: negblocks.py ENTRY_ATTR file...
# counts static negative-test blocks (pytest.raises / assertRaises / assertRaisesRegex, call or with form)
# whose callable arg (call form) or with-body contains a call to attribute/name == ENTRY_ATTR
entry = sys.argv[1]
def calls_entry(nodes):
    for nd in nodes:
        for n in ast.walk(nd):
            if isinstance(n, ast.Call):
                f = n.func
                nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
                if nm == entry: return True
            if isinstance(n, ast.Attribute) and n.attr == entry: return True
    return False
def kind(call):
    f = call.func; nm = f.attr if isinstance(f, ast.Attribute) else getattr(f,'id','')
    return nm if nm in ('raises','assertRaises','assertRaisesRegex','assertRaisesRegexp') else None
tot=0; msg=0; cls=collections.Counter(); perfile=collections.Counter()
for fn in sys.argv[2:]:
    t = ast.parse(open(fn).read())
    for n in ast.walk(t):
        if isinstance(n, ast.With):
            for it in n.items:
                c = it.context_expr
                if isinstance(c, ast.Call) and kind(c) and calls_entry(n.body):
                    k = kind(c); tot+=1; perfile[fn]+=1
                    cls[ast.unparse(c.args[0]) if c.args else '?']+=1
                    if k.startswith('assertRaisesRegex') or any(kw.arg=='match' for kw in c.keywords): msg+=1
        elif isinstance(n, ast.Call) and kind(n) and len(n.args) >= 2 and calls_entry([n.args[1]]):
            k=kind(n); tot+=1; perfile[fn]+=1; cls[ast.unparse(n.args[0])]+=1
            if k.startswith('assertRaisesRegex'): msg+=1
print("BLOCKS", tot, "WITH_MESSAGE", msg, "CLASS_ONLY", tot-msg)
print(cls.most_common()); [print(v,k) for k,v in perfile.items()]
