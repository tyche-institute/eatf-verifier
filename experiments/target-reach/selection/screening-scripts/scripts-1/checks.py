import ast,sys,collections
# For each file: groups raise statements by (enclosing function, exception class, message template).
# message template: first arg as source with f-string values replaced by {}
def tmpl(node):
    if node is None: return ''
    if isinstance(node,ast.Constant): return repr(node.value)
    if isinstance(node,ast.JoinedStr):
        return 'f'+repr(''.join(v.value if isinstance(v,ast.Constant) else '{}' for v in node.values))
    if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Mod): return tmpl(node.left)+' % ...'
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='format': return tmpl(node.func.value)+'.format'
    return ast.unparse(node)[:60]
total=collections.Counter(); 
for path in sys.argv[1:]:
    src=open(path).read(); t=ast.parse(src)
    groups=collections.OrderedDict()
    def visit(n,fn):
        for c in ast.iter_child_nodes(n):
            if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef)):
                visit(c,(fn+'.' if fn else '')+c.name)
            elif isinstance(c,ast.ClassDef):
                visit(c,(fn+'.' if fn else '')+c.name)
            else:
                if isinstance(c,ast.Raise) and c.exc is not None:
                    e=c.exc
                    if isinstance(e,ast.Call):
                        cls=ast.unparse(e.func); m=tmpl(e.args[0]) if e.args else ''
                    else: cls=ast.unparse(e); m='<noargs>'
                    groups.setdefault((fn,cls,m),[]).append(c.lineno)
                visit(c,fn)
    visit(t,'')
    print('==',path,len(groups))
    for (fn,cls,m),ls in groups.items():
        print(f'  {fn} | {cls} | {m} | lines {ls}'); total[cls]+=1
print('TOTAL checks',sum(total.values()),total.most_common(8))
