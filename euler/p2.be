(a,b,s) [
    (a + b) n.

    n <= 4_000_000 [
        n % 2 == 0 [ (s + n) s ] [].
        solve', b, n, s, tail.
    ] [
        s
    ]

] solve.

0, 1, 0, solve, print.
