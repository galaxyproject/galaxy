import sys

import galaxy.eggs  # NOQA


def main():
    with open(sys.argv[1], "w") as f:
        f.write("out_file1")


if __name__ == '__main__':
    main()
