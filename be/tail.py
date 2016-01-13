import stackless

def tail(f, *args, **kwargs):
    def w(f, args, kwargs, result_ch):
        result_ch.send(f(*args, **kwargs))
    r = stackless.channel()
    stackless.tasklet(w)(f, args, kwargs, r)
    return r.receive()
