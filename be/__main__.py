import argparse

from . import interp


def get_args():
    parser = argparse.ArgumentParser(
        prog='python -m be', description='be: toy language')

    parser.add_argument('file', type=str, nargs=1)

    return parser.parse_args()


def run(args):
    with open(args.file[0], 'rb') as f:
        txt = f.read().decode('utf-8')
        interp.run(txt)


run(get_args())
