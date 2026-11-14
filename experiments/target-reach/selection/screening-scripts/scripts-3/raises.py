# Usage: python3 -I raises.py file.py[:func1,func2] ...  -> lists raise statements per function, counts checks
import ast, sys, collections
def tmpl(node):
    if node is None: return "<none>"
    if isinstance(node, ast.Constant) and isinstance(node.value, str): return repr(node.value)
    if isinstance(node, ast.JoinedStr):
        return "f" + repr("".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return tmpl(node.func.value) + ".format"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        return tmpl(node.left) + "%"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return tmpl(node.left) + "+" + tmpl(node.right)
    return "<expr:" + ast.unparse(node)[:60] + ">"
def cls_and_msg(exc):
    if exc is None: return ("<reraise>", "")
    if isinstance(exc, ast.Call):
        c = ast.unparse(exc.func)
        m = tmpl(exc.args[0]) if exc.args else ("<kw:" + ",".join(k.arg or "**" for k in exc.keywords) + ">" if exc.keywords else "<noargs>")
        return (c, m)
    return (ast.unparse(exc), "<name>")
total = collections.Counter(); allchecks = set()
for arg in sys.argv[1:]:
    path, _, fl = arg.partition(":")
    funcs = set(fl.split(",")) if fl else None
    tree = ast.parse(open(path, encoding="utf-8-sig").read())
    def walk(node, stack):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(ch, stack + [ch.name])
            elif isinstance(ch, ast.ClassDef):
                walk(ch, stack + [ch.name])
            else:
                if isinstance(ch, ast.Raise):
                    fn = ".".join(stack)
                    if funcs is None or (stack and stack[-1] in funcs) or fn in funcs:
                        c, m = cls_and_msg(ch.exc)
                        print(f"{path.split('/')[-1]}:{ch.lineno}\t{fn}\t{c}\t{m}")
                        allchecks.add((path, fn, c, m))
                walk(ch, stack)
    walk(tree, [])
cnt = collections.Counter(c for (_, _, c, _) in allchecks if c != "<reraise>")
print("CHECKS (distinct file,func,class,template; excl bare re-raise):", sum(cnt.values()))
print("by class:", cnt.most_common())
