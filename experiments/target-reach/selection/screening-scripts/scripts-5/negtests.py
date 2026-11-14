# usage: python3 -I negtests.py "<entry-call-regex>" "<Exc1,Exc2,...>" file1.py ...
# Finds pytest.raises / assertRaises / assertRaisesRegex blocks (with-form and callable-form) whose
# expected exception (last dotted name) is in the class list and whose body (with-form) or callable
# argument (callable-form) contains a call whose unparsed func matches the regex.
# message asserted = match= kw, assertRaisesRegex, or `as e` followed in the same stmt list by a statement mentioning str(e)/e.value/e.exception/e.args.
import ast, sys, re
rx = re.compile(sys.argv[1]); classes = set(sys.argv[2].split(','))
def excnames(node):
    if isinstance(node, ast.Tuple): return [n for e in node.elts for n in excnames(e)]
    return [ast.unparse(node).split('.')[-1]]
def kind(call):
    f = ast.unparse(call.func)
    if f.endswith('pytest.raises') or f == 'raises': return 'pr'
    if f.endswith('assertRaisesRegex') or f.endswith('assertRaisesRegexp'): return 'arr'
    if f.endswith('assertRaises'): return 'ar'
    return None
def calls_entry(nodes):
    for nd in nodes:
        for n in ast.walk(nd):
            if isinstance(n, ast.Call) and rx.search(ast.unparse(n.func)): return True
            if isinstance(n, (ast.Name, ast.Attribute)) and rx.search(ast.unparse(n)): return True
    return False
tot = cls_only = msg = 0; other = 0
for path in sys.argv[3:]:
    tree = ast.parse(open(path).read())
    for parent in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            stmts = getattr(parent, field, None)
            if not isinstance(stmts, list): continue
            for i, st in enumerate(stmts):
                blocks = []
                if isinstance(st, (ast.With, ast.AsyncWith)):
                    for it in st.items:
                        c = it.context_expr
                        if isinstance(c, ast.Call) and kind(c) and c.args:
                            blocks.append((c, kind(c), st.body, it.optional_vars))
                for n in ast.walk(st) if not isinstance(st,(ast.With,ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef,ast.If,ast.For,ast.Try,ast.While)) else []:
                    if isinstance(n, ast.Call) and kind(n) and len(n.args) >= 2:
                        blocks.append((n, kind(n) , n.args[1:] if kind(n) != 'arr' else n.args[2:], None))
                for c, k, body, var in blocks:
                    names = excnames(c.args[0])
                    if not any(nm in classes for nm in names): continue
                    if not calls_entry(body): other += 1; continue
                    m = k == 'arr' or any(kw.arg == 'match' for kw in c.keywords)
                    if not m and var is not None:
                        v = ast.unparse(var)
                        for later in stmts[i+1:i+4]:
                            s = ast.unparse(later)
                            if re.search(r'str\(%s(\.value|\.exception)?\)|%s\.(value|exception|args)' % (v, v), s): m = True
                    tot += 1; msg += m; cls_only += (not m)
                    print(f"{path.split('/')[-1]}:{c.lineno}\t{k}\t{','.join(names)}\t{'MSG' if m else 'CLS'}")
print('NEG_BLOCKS', tot, 'CLASS_ONLY', cls_only, 'WITH_MSG', msg, 'MATCHING_CLASS_BUT_NO_ENTRY_CALL', other)
