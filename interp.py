import ast

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

        elif c == ' ':
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


def push_stack(stack, item):
    (buft, bufv) = item

    if buft == int:
        val = EInt(buft, int(bufv))
    elif buft == 'block':
        val = EBlock(buft, bufv)
    elif buft == list:
        val = EList(buft, bufv)
    else:
        val = EId(buft, bufv)

    stack.append(val)


def run_stack(stack, scope):
    constructs = {
        'def': [EList, EBlock, EId],
        'set': [Expr, EId],
    }

    for op, p in constructs.items():
        if match_stack(stack, p):
            if op == 'set':
                name = stack.pop()
                value = stack.pop()

                if name.v in scope and scope[name.v]['is_callable']:
                    yield from gen_call(name, value, scope)
                else:
                    yield from gen_set(name, value, scope)

            elif op == 'def':
                name = stack.pop()
                block = stack.pop()
                args = stack.pop()

                yield from gen_def(name, args, block, scope)

    while True:
        try:
            stack.pop()
        except IndexError:
            break


def match_stack(stack, parts):
    for i, item in enumerate(stack):
        if isinstance(item, parts[i]):
            return len(stack) == len(parts)
    return False


def resolve_value(value, scope):
    if isinstance(value, EId):
        return ast.Name(id=value.v, ctx=ast.Load())
    elif isinstance(value, (EInt,)):
        return ast.Num(n=value.v)


def gen_expr(**kwargs):
    node = ast.Expr(**kwargs)
    node = ast.fix_missing_locations(node)
    return node


def gen_call(name, value, scope):
    yield gen_expr(value=ast.Call(func=ast.Name(id=name.v, ctx=ast.Load()),
                   args=[resolve_value(value, scope)],
                   keywords=[]))


def gen_set(name, value, scope):
    yield gen_expr(targets=[
        ast.Name(id=name.v, ctx=ast.Store())
    ], value=resolve_value(value, scope))


def gen_def(name, args, body, scope):
    scope[name.v] = {'is_callable': True}
    args = [ast.arg(arg=a, annotation=None) for a in args.v]
    yield ast.fix_missing_locations(ast.FunctionDef(
        name=name.v,
        args=ast.arguments(
            args=args, kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=list(parse(body.v)),
        decorator_list=[]))


def run(txt):
    body = list(parse(txt))
    wrapper = ast.Module(body=body)
    co = compile(wrapper, '<ast>', 'exec')
    exec(co, {})


run('(a,) [ a print ] foo. 2 foo')
