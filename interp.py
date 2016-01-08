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
class ECompare(Expr): pass


def parse(txt, scope):
    stack = []

    yield from eat((c for c in txt), stack, scope)


def eat(rest, stack, scope):
    expr, rest = eat_next(rest, stack)

    if expr:
        if expr == '.':
            yield from run_stack(stack, scope)

        elif expr == ',':
            buf = list(run_stack(stack, scope, noexpr=True))
            scope['stack'].extend(buf)

        else:
            stack.append(expr)

        if expr == ',':
            yield from run_stack(stack, scope)

        yield from eat(rest, stack, scope)

        if stack:
            yield from run_stack(stack, scope)


def eat_next(rest, stack):
    try:
        c = next(rest)
    except StopIteration:
        return None, stack

    if c in (' ', '\n', '\r'):
        return eat_next(rest, stack)

    elif c == '[':
        buf = []
        openb = 1
        while True:
            try:
                c = next(rest)
            except StopIteration:
                return None, stack

            if c == ']':
                openb -= 1
                if openb < 1:
                    break
            elif c == '[':
                openb += 1
            buf.append(c)
        return EBlock(None, buf), rest

    elif c == '(':
        is_list = False
        while True:
            expr, rest = eat_next(rest, stack)
            if expr == ')':
                if is_list:
                    items = []
                    while True:
                        try:
                            items.append(stack.pop(0))
                        except:
                            break
                    return EList(list, items), rest
                if not stack:
                    return EList(list, []), rest
                return stack.pop(), rest
            elif expr == ',':
                is_list = True
            else:
                stack.append(expr)

    elif c.isdigit():
        buf = [c]
        while True:
            c = next(rest)
            if c.isdigit():
                buf.append(c)
            elif c == '_':
                pass
            else:
                break
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
        else:
            rest = reject(rest, buf2)
        expr = EInt(int, int(''.join(buf)))
        return expr, rest

    elif c in ('+', '-', '*', '%', '/'):
        expr, rest = eat_next(rest, stack)
        if expr:
            expr = EOp(c, [stack.pop(), expr])
            return expr, rest

    elif c in ('<', '>'):
        n = next(rest)
        if n == '=':
            c += n
        else:
            rest = reject(rest, [n])
        expr, rest = eat_next(rest, stack)
        if expr:
            expr = ECompare(c, [stack.pop(), expr])
            return expr, rest

    elif c == '=':
        c2 = next(rest)
        if c2 == '=':
            expr, rest = eat_next(rest, stack)
            return ECompare('==', [stack.pop(), expr]), rest
        rest = reject(rest, [c2])
        return None, rest

    elif c.isalpha() or c == '_':
        buf = [c]
        while True:
            c = next(rest)
            if c not in IDCHARS:
                rest = reject(rest, [c])
                break
            buf.append(c)
        expr = EId(None, ''.join(buf))
        expr.is_safe = False
        c = next(rest)
        if c == '\'':
            expr.is_safe = True
        else:
            rest = reject(rest, [c])
        return expr, rest

    return c, rest


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


def run_stack(stack, scope, noexpr=False):
    constructs = [
        ('def', [EList, EBlock, EId]),
        ('set', [EId]),
        ('set', [Expr, EId]),
        ('if', [Expr, EBlock, EBlock]),
        ('expr', [Expr]),
    ]

    for op, p in constructs:
        if match_stack(stack, p):
            if op == 'expr':
                yield expr(value=resolve_value(stack.pop(), scope))

            elif op == 'set':
                name = stack.pop()

                if stack:
                    value = stack.pop()
                else:
                    value = None

                # 1,2,min result
                if isinstance(value, EId) and scope['stack']:
                    call = list(emit_call(value, [], scope, noexpr=True))[0]
                    yield from emit_set(name, call, scope)

                # 1 print
                elif not name.is_safe and name.v in scope['callables']:
                    args = []
                    if value:
                        args.append(value)
                    yield from emit_call(name, args, scope, noexpr=noexpr)

                # echo print
                elif isinstance(value, EId):
                    if value.v in scope['callables']:
                        scope['callables'][name.v] = scope['callables'][value.v]
                    value = resolve_value(value, scope)
                    yield from emit_set(name, value, scope)

                elif value:
                    value = resolve_value(value, scope)
                    yield from emit_set(name, value, scope)

                else:
                    yield resolve_value(name, scope)

            elif op == 'def':
                name = stack.pop()
                block = stack.pop()
                args = stack.pop()

                yield from emit_def(name, args, block, scope)

            elif op == 'if':
                elseb = stack.pop()
                ifb = stack.pop()
                cond = stack.pop()

                yield from emit_if(cond, ifb, elseb, scope)

            break

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
        if not isinstance(item, p):
            break
        return len(stack) == len(parts)
    return False


def resolve_value(value, scope):
    if isinstance(value, EId):
        node = ast.Name(id=value.v, ctx=ast.Load())
    elif isinstance(value, EInt):
        node = ast.Num(n=value.v)
    elif isinstance(value, EList):
        lst = [resolve_value(a, scope) for a in value.v]
        node = ast.List(elts=lst, ctx=ast.Load())
    elif isinstance(value, EOp):
        lft, rgt = value.v
        lft = resolve_value(lft, scope)
        rgt = resolve_value(rgt, scope)

        operators = {
            '+': ast.Add(),
            '-': ast.Sub(),
            '*': ast.Mult(),
            '/': ast.Div(),
            '%': ast.Mod(),
        }

        node = ast.BinOp(left=lft, right=rgt, op=operators[value.t])
    elif isinstance(value, ECompare):
        lft, rgt = value.v
        lft = resolve_value(lft, scope)
        rgt = resolve_value(rgt, scope)

        operators = {
            '<': ast.Lt(),
            '>': ast.Gt(),
            '<=': ast.LtE(),
            '>=': ast.GtE(),
            '==': ast.Eq(),
        }

        node = ast.Compare(left=lft, ops=[operators[value.t]],
                           comparators=[rgt])

    return ast.fix_missing_locations(node)


def expr(**kwargs):
    node = ast.Expr(**kwargs)
    node = ast.fix_missing_locations(node)
    return node


# id
# expr id
def emit_call(name, args, scope, noexpr=False):
    args2 = []

    if not args:
        stack = scope.pop('stack')

        for node in stack:
            if isinstance(node, ast.Expr):
                node = node.value
            args2.append(node)

        scope['stack'] = []

    args2.extend(resolve_value(a, scope) for a in args)

    call = ast.Call(func=ast.Name(id=name.v, ctx=ast.Load()),
                    args=args2,
                    kwargs=None,
                    starargs=None,
                    keywords=[])

    if not noexpr:
        call = expr(value=call)

    yield call


# id
# expr id
def emit_set(name, value, scope):
    yield ast.fix_missing_locations(ast.Assign(targets=[
        ast.Name(id=name.v, ctx=ast.Store())
    ], value=value))


# list body id
def emit_def(name, args, body, scope):
    scope['callables'][name.v] = None
    args = [ast.arg(arg=a.v, annotation=None) for a in args.v]
    args = ast.arguments(args=args, vararg=None, kwonlyargs=[], kw_defaults=[],
                         kwarg=None, defaults=[])

    body = list(eat((c for c in body.v), [], scope))

    if isinstance(body[-1], ast.If):
        body.append(ast.Return(value=ast.Name(id=',', ctx=ast.Load())))

    else:
        lastv = body.pop()

        if isinstance(lastv, ast.Expr):
            lastv = lastv.value

        body.append(ast.Return(value=lastv))

    yield ast.fix_missing_locations(ast.FunctionDef(
        name=name.v,
        args=args,
        body=body,
        decorator_list=[]))


def emit_if(cond, ifb, elseb, scope):
    cond = resolve_value(cond, scope)

    if ifb.v:
        ifb = list(eat(iter(ifb.v), [], scope))
        lastv = ifb.pop()
        if isinstance(lastv, ast.Expr):
            lastv = lastv.value
        if isinstance(lastv, ast.Assign):
            lastv.targets.append(ast.Name(id=',', ctx=ast.Store()))
            ifb.append(lastv)
        elif isinstance(lastv, ast.If):
            ifb.append(lastv)
        else:
            ifb.extend(emit_set(EId(None, ','), lastv, scope))
    else:
        ifb = [ast.Pass()]

    if elseb.v:
        elseb = list(eat(iter(elseb.v), [], scope))
        lastv = elseb.pop()
        if isinstance(lastv, ast.Expr):
            lastv = lastv.value
        if isinstance(lastv, ast.Assign):
            lastv.targets.append(ast.Name(id=',', ctx=ast.Store()))
            elseb.append(lastv)
        elif isinstance(lastv, ast.If):
            elseb.append(lastv)
        else:
            elseb.extend(emit_set(EId(None, ','), lastv, scope))
    else:
        elseb = [ast.Pass()]

    yield ast.fix_missing_locations(ast.If(cond, ifb, elseb))


def inject_tail(scope):
    scope['callables']['tail'] = None
    return astor.parsefile('tail.py').body


def run(txt):
    scope = {
        'callables': __builtins__.__dict__,
        'stack': [],
    }

    body = []
    body.extend(inject_tail(scope))
    body.extend(parse(txt, scope))

    wrapper = ast.Module(body=body)

    # print(astor.dump(wrapper))
    # print(astor.to_source(wrapper))

    co = compile(wrapper, '<ast>', 'exec')
    exec(co, {})


run('''

(n,) [

    n * (n + 1) / 2, 2, pow SquareOfSum.
    n * (n + 1) * ((2 * n) + 1) / 6 SumOfSquares.

    SquareOfSum - SumOfSquares, int.

] solve.

100 solve, print.

''')
