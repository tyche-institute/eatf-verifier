import ast,sys,re,os,collections
# usage: negblocks.py <ENTRY_REGEX> <EXC_REGEX> files/dirs...
# counts blocks: with pytest.raises(E..)/self.assertRaises(E)/assertRaisesRegex (with or callable form)
# whose exception name matches EXC_REGEX and whose body/callable args contain a call/attr whose name matches ENTRY_REGEX
entry=re.compile(sys.argv[1]); excre=re.compile(sys.argv[2])
files=[]
for a in sys.argv[3:]:
    if os.path.isdir(a):
        for r,d,f in os.walk(a):
            files+= [os.path.join(r,x) for x in f if x.endswith('.py')]
    else: files.append(a)
RAISERS={'raises','assertRaises','assertRaisesRegex','assertRaisesRegexp'}
def rname(call):
    f=call.func
    return f.attr if isinstance(f,ast.Attribute) else (f.id if isinstance(f,ast.Name) else None)
def names_in(nodes):
    s=set()
    for n in nodes:
        for x in ast.walk(n):
            if isinstance(x,ast.Attribute): s.add(x.attr)
            elif isinstance(x,ast.Name): s.add(x.id)
    return s
tot=0; msg=0; clsonly=0; perfile=collections.Counter(); excc=collections.Counter()
for p in sorted(files):
    try: t=ast.parse(open(p).read())
    except Exception as e: print('PARSEFAIL',p,e); continue
    # map body statements to following siblings for message assertions after with-block
    for parent in ast.walk(t):
        for field in ('body','orelse','finalbody'):
            stmts=getattr(parent,field,None)
            if not isinstance(stmts,list): continue
            for i,st in enumerate(stmts):
                cands=[]
                if isinstance(st,ast.With):
                    for it in st.items:
                        c=it.context_expr
                        if isinstance(c,ast.Call) and rname(c) in RAISERS and c.args:
                            cands.append(('with',c,st.body,it.optional_vars))
                for x in ([st.value] if isinstance(st,ast.Expr) else []):
                    if isinstance(x,ast.Call) and rname(x) in RAISERS and len(x.args)>=2:
                        cands.append(('call',x,[a for a in x.args[1:]],None))
                for kind,c,body,var in cands:
                    exc=ast.unparse(c.args[0])
                    if not excre.search(exc): continue
                    if not any(entry.fullmatch(n) for n in names_in(body)): continue
                    tot+=1; perfile[p]+=1; excc[exc]+=1
                    m = rname(c).startswith('assertRaisesRegex') or any(k.arg=='match' for k in c.keywords)
                    if kind=='call' and rname(c).startswith('assertRaisesRegex'): pass
                    if not m and var is not None:
                        vn=ast.unparse(var)
                        for nxt in stmts[i+1:i+4]:
                            src=ast.unparse(nxt)
                            if isinstance(nxt,(ast.Assert,ast.Expr)) and vn in src and ('str(' in src or '.args' in src or 'msg' in src or 'message' in src or 'value' in src or 'exception' in src):
                                m=True;break
                    if m: msg+=1
                    else: clsonly+=1
print('blocks',tot,'msg',msg,'classonly',clsonly)
for p,n in perfile.most_common(): print(' ',n,p)
print(excc.most_common())
