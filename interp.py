from collections import namedtuple


Expr = namedtuple('Expr', ['t', 'v'])


class EId(Expr): pass
class EBlock(Expr): pass
class EInt(Expr): pass
class EStr(Expr): pass
class EList(Expr): pass


def parse(txt):
    stack = []
    scope = __builtins__.__dict__

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
                run_stack(stack, scope)
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

    run_stack(stack, scope)


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

                if name.v in scope and callable(scope[name.v]):
                    scope[name.v](resolve_value(value, scope))
                else:
                    scope[name.v] = resolve_value(value, scope)

            elif op == 'def':
                name = stack.pop()
                block = stack.pop()
                args = stack.pop()

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
        return scope.get(value.v)
    else:
        return value.v


parse('(a,) [ 1 print ] a.')
