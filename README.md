# be
Toy language :)

You can see some examples in the [euler directory](https://github.com/caioariede/be/tree/master/euler).

## Data Types

#### Int

    1
    1_000_000

#### Float

    1.0
    1.0e+1
    1_000.0

#### String

    "Hello world"

#### List

    [1,2,3]

### Tuple

    (1,2,3)
    

## Mini Tutorial

### Variables

##### Format

    <expr> <id>

##### Examples

    1n
    1 n
    (1 + 1) n


### Calling functions

##### Format

    <expr> id

##### Examples

    1 print
    1, 1, add, print


### Functions

##### Format

    <tuple> <block> <id>

##### Examples

    (n,) [ n print ] echo
    (a,b) [ a + b ] add
