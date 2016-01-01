import ast
import astor

from collections import namedtuple


Expr = namedtuple('Expr', ['t', 'v'])


class EId(Expr): pass
class EBlock(Expr): pass
class EInt(Expr): pass
class EStr(Expr): pass
class EList(Expr): pass


def parse(txt):
    stack = []

    scope = {
        k: {'is_callable': True}
        for k, v in __builtins__.__dict__.items()
    }

    scope['__'] = []

    buf = None

    for c in txt:
        if buf is not None:
            buft, bufv = buf

            if buft == 'block':
                if c == ']':
                    push_stack(stack, buf)
                    buf = None
                else:
                    buf = (buft, bufv + c)
            elif c == ',' and buft not in (list,):
                push_stack(stack, buf)
                push_stack(stack, (None, c))
                yield from run_stack(stack, scope)
                buf = None
            elif c == ' ':
                push_stack(stack, buf)
                buf = None
            elif buft == list:
                if c == ')':
                    push_stack(stack, buf)
                    buf = None
                elif c == ',':
                    pass
                else:
                    bufv.append(c)
                    buf = (buft, bufv)
            elif buft == str and c == '"':
                push_stack(stack, buf)
                buf = None
            elif buft == int and c == '.':
                buf = (float, bufv + c)
            elif c == '.':
                if buf is not None:
                    push_stack(stack, buf)
                    buf = None
                yield from run_stack(stack, scope)
            else:
                buf = (buft, bufv + c)

        elif c == ',':
            push_stack(stack, (None, c))
            yield from run_stack(stack, scope)
        elif c == '.':
            yield from run_stack(stack, scope)
        elif c in (' ', '\r', '\n'):
            pass
        elif c == '"':
            buf = (str, "")
        elif c.isdigit():
            buf = (int, c)
        elif c == '(':
            buf = (list, [])
        elif c == '[':
            buf = ('block', "")
        else:
            buf = (None, c)

    if buf is not None:
        push_stack(stack, buf)

    yield from run_stack(stack, scope)


def get_item(item):
    (buft, bufv) = item

    if buft == int:
        val = EInt(buft, int(bufv))
    elif buft == 'block':
        val = EBlock(buft, bufv)
    elif buft == list:
        val = EList(buft, bufv)
    else:
        val = EId(buft, bufv)

    return val


def push_stack(stack, item):
    stack.append(get_item(item))


def run_stack(stack, scope):
    constructs = [
        ('def', [EList, EBlock, EId]),
        ('set', [EId]),
        ('set', [Expr, EId]),
    ]

    for op, p in constructs:
        if match_stack(stack, p):
            if op == 'set':
                name = stack.pop()

                if stack:
                    value = stack.pop()
                else:
                    value = None

                if name.v in scope and scope[name.v]['is_callable']:
                    args = []
                    if value:
                        args.append(value)
                    yield from emit_call(name, args, scope)
                elif name.v == ',':
                    scope['__'].append(value)
                elif isinstance(value, EId) and value.v in scope and scope[value.v]['is_callable'] and scope['__']:
                    call = list(emit_call(value, [], scope))[0].value
                    yield from emit_set(name, call, scope)
                else:
                    scope[name.v] = scope.get(value.v) or {'is_callable': True}
                    value = resolve_value(value, scope)
                    yield from emit_set(name, value, scope)

            elif op == 'def':
                name = stack.pop()
                block = stack.pop()
                args = stack.pop()

                yield from emit_def(name, args, block, scope)

    while True:
        try:
            stack.pop()
        except IndexError:
            break


def match_stack(stack, parts):
    for i, item in enumerate(stack):
        try:
            p = parts[i]
        except IndexError:
            break
        if isinstance(item, p):
            return len(stack) == len(parts)
    return False


def resolve_value(value, scope):
    if isinstance(value, EId):
        return ast.Name(id=value.v, ctx=ast.Load())
    elif isinstance(value, (EInt,)):
        return ast.Num(n=value.v)


def expr(**kwargs):
    node = ast.Expr(**kwargs)
    node = ast.fix_missing_locations(node)
    return node


# id
# expr id
def emit_call(name, args, scope):
    args2 = scope['__']
    args2.extend(args)
    args2 = [resolve_value(a, scope) for a in args2]

    yield expr(value=ast.Call(func=ast.Name(id=name.v, ctx=ast.Load()),
               args=args2,
               kwargs=[],
               starargs=[],
               keywords=[]))

    scope['__'] = []


# id
# expr id
def emit_set(name, value, scope):
    yield ast.fix_missing_locations(ast.Assign(targets=[
        ast.Name(id=name.v, ctx=ast.Store())
    ], value=value))


# list body id
def emit_def(name, args, body, scope):
    scope[name.v] = {'is_callable': True}
    args = [ast.arg(arg=a, annotation=None) for a in args.v]
    args = ast.arguments(args=args, vararg=None, kwonlyargs=[], kw_defaults=[],
                         kwarg=None, defaults=[])
    yield ast.fix_missing_locations(ast.FunctionDef(
        name=name.v,
        args=args,
        body=list(parse(body.v)),
        decorator_list=[]))


def run(txt):
    body = list(parse(txt))
    wrapper = ast.Module(body=body)

    print(astor.dump(wrapper))
    print(astor.to_source(wrapper))

    co = compile(wrapper, '<ast>', 'exec')
    exec(co, {})


run('''

(a,b) [ a print ] add.

1,2, add result.

result print.

''')
