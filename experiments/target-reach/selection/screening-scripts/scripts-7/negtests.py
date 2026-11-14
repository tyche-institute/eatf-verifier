# usage: python3 -I negtests.py <file_or_dir>... ; env ENTRY=regex of called names, EXC=regex of exception names
import ast, sys, os, re, collections
ent=re.compile(os.environ.get('ENTRY','.*')); exc=re.compile(os.environ.get('EXC','.*'))
files=[]
for p in sys.argv[1:]:
    if os.path.isdir(p):
        for r,_,fs in os.walk(p):
            files += [os.path.join(r,f) for f in fs if f.endswith('.py')]
    else: files.append(p)
def calls_entry(nodes):
    for n in nodes:
        for c in ast.walk(n):
            if isinstance(c, ast.Call):
                f=c.func; nm = f.attr if isinstance(f,ast.Attribute) else (f.id if isinstance(f,ast.Name) else '')
                if nm and ent.fullmatch(nm): return True
            if isinstance(c,(ast.Name,ast.Attribute)):
                nm = c.attr if isinstance(c,ast.Attribute) else c.id
                if nm and ent.fullmatch(nm) and isinstance(getattr(c,'ctx',None),ast.Load): pass
    return False
def refnames(args):
    out=[]
    for a in args:
        for c in ast.walk(a):
            if isinstance(c,ast.Name): out.append(c.id)
            if isinstance(c,ast.Attribute): out.append(c.attr)
    return any(ent.fullmatch(x) for x in out)
tot=0; cls_only=0; withmsg=0; per=collections.Counter(); nonmatch=0
for path in files:
    try: tree=ast.parse(open(path).read())
    except Exception as e: print('PARSEFAIL',path,e); continue
    parents={}
    for n in ast.walk(tree):
        for ch in ast.iter_child_nodes(n): parents[ch]=n
    def excname(a): return ast.unparse(a)
    def later_asserts(withnode, var):
        par=parents.get(withnode)
        for fld in ('body','orelse','finalbody'):
            lst=getattr(par,fld,None)
            if lst and withnode in lst:
                i=lst.index(withnode)
                for s in lst[i+1:i+4]:
                    if any(isinstance(x,ast.Name) and x.id==var for x in ast.walk(s)) and ('assert' in ast.unparse(s).lower()): return True
        return False
    for n in ast.walk(tree):
        rec=None
        if isinstance(n,(ast.With,ast.AsyncWith)):
            for it in n.items:
                ce=it.context_expr
                if isinstance(ce,ast.Call):
                    f=ce.func; nm=f.attr if isinstance(f,ast.Attribute) else getattr(f,'id','')
                    if nm in ('raises','assertRaises','assertRaisesRegex','assertRaisesRegexp') and ce.args:
                        e=excname(ce.args[0])
                        if not exc.search(e): nonmatch+=1; continue
                        if not calls_entry(n.body): continue
                        m = nm.startswith('assertRaisesRegex') or any(k.arg=='match' for k in ce.keywords)
                        if not m and it.optional_vars is not None and isinstance(it.optional_vars,ast.Name):
                            m = later_asserts(n, it.optional_vars.id)
                        rec=(e,m)
        elif isinstance(n,ast.Call):
            f=n.func; nm=f.attr if isinstance(f,ast.Attribute) else getattr(f,'id','')
            if nm in ('raises','assertRaises','assertRaisesRegex','assertRaisesRegexp') and len(n.args)>=2:
                par=parents.get(n)
                if isinstance(par,ast.withitem): continue
                e=excname(n.args[0])
                if not exc.search(e): nonmatch+=1; continue
                rest = n.args[2:] if nm.startswith('assertRaisesRegex') else n.args[1:]
                if not refnames(rest[:1]): continue
                rec=(e, nm.startswith('assertRaisesRegex') or any(k.arg=='match' for k in n.keywords))
        if rec:
            tot+=1; per[(os.path.relpath(path), rec[0])]+=1
            if rec[1]: withmsg+=1
            else: cls_only+=1
for k,v in sorted(per.items()): print(v, k)
print('TOTAL',tot,'CLASS_ONLY',cls_only,'WITH_MSG',withmsg,'EXC_NONMATCH_SKIPPED',nonmatch)
