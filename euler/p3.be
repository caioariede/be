(n,f,m) [
    f > n [ m ] [
        n % f == 0 [
            solve', n / f, f, f, tail
        ] [ 
            solve', n, f + 1, m, tail
        ]
    ]
] solve.

600851475143, 2, 2, solve, print.
