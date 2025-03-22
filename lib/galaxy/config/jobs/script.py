import sys

from .arg_parsing import config_args
from .generate import build_job_config


def main(argv=None):
    argv = argv or sys.argv[1:]
    config_str = build_job_config(config_args(argv))
    print(config_str)


if __name__ == "__main__":
    main()
