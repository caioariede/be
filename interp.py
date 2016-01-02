import ast
import astor
import operator
import itertools
import string

from collections import namedtuple


IDCHARS = string.ascii_letters + string.digits + '_-'


Expr = namedtuple('Expr', ['t', 'v'])


class EId(Expr): pass
class EBlock(Expr): pass
class EInt(Expr): pass
class EStr(Expr): pass
class EList(Expr): pass
class EOp(Expr): pass


def parse(txt):
    stack = []

    eat((c for c in txt), stack)

    print(stack)

    return
    stack = []

    scope = {
        k: {'is_callable': True, 'fn': v}
        for k, v in __builtins__.__dict__.items()
    }

    scope['+'] = {'is_callable': True, 'fn': operator.add}
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


def eat(rest, stack):
    expr, rest = eat_next(rest, stack)

    if expr:
        stack.append(expr)
        eat(rest, stack)


def eat_next(rest, stack):
    c = next(rest)

    if c in (' ', '\n', '\r'):
        return eat_next(rest, stack)

    elif c.isdigit():
        buf = [c]
        while True:
            c = next(rest)
            if not c.isdigit():
                break
            buf.append(c)
        buf2 = [c]
        if c == 'e':
            l = c = next(rest)
            if c == '+':
                buf2.append(c)
            if c.isdigit():
                buf2.append(c)
            elif l == '+':
                rest = reject(rest, buf2)
                buf2 = []
            if buf2:
                while True:
                    c = next(rest)
                    if not c.isdigit():
                        break
                    buf2.append(c)
                buf.extend(buf2)
        expr = EInt(int, int(''.join(buf)))
        return expr, rest

    elif c == '+':
        expr, rest = eat_next(rest, stack)
        if expr:
            expr = EOp(c, [stack.pop(), expr])
            return expr, rest

    elif c.isalpha() or c == '_':
        buf = [c]
        while True:
            c = next(rest)
            if c not in IDCHARS:
                rest = reject(rest, [c])
                break
            buf.append(c)
        expr = EId(None, ''.join(buf))
        return expr, rest

    return None, rest


def reject(rest, items):
    return itertools.chain(items, rest)


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
            print(stack)
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

1 + 2 print.

''')
