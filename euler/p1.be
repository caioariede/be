(n,s) [
    n - 1 n.
    n % 3 == 0 [ s + n s ] [
        n % 5 == 0 [ s + n s ] [ s ]
    ].
    n < 1 [ s ] [ solve', n, s, tail ].
] solve.

1000, 0, solve, print.
