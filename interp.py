def parse(txt):
    stack = []
    buf = None

    for c in txt:
        if buf is not None:
            buft, bufv = buf

            if c == ' ':
                stack.append(buf)
                buf = None
            elif buft == str and c == '"':
                stack.append(buf)
                buf = None
            elif buft == int and c == '.':
                buf = (float, bufv + c)
            else:
                buf = (buft, bufv + c)

        elif c == ' ':
            pass
        elif c == '"':
            buf = (str, "")
        elif c.isdigit():
            buf = (int, c)
        else:
            buf = (None, c)

    if buf is not None:
        stack.append(buf)

    print(stack)


parse('10 n')
