"""
    Sorts tabular data on one or more columns. All comments of the file are collected
    and placed at the beginning of the sorted output file.
"""
# 03/05/2013 guerler

import argparse
import subprocess
import sys


def stop_err(msg):
    sys.exit(msg)


def main():
    # define options
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", type=argparse.FileType("r"), help="Tabular file to be sorted")
    parser.add_argument("-o", "--output", type=argparse.FileType("w"), help="Sorted output file")
    parser.add_argument("-k", "--key", action="append", help="Key (see manual for bash/sort)")
    parser.add_argument("-H", "--header_lines", type=int, help="Number of header lines to ignore")

    # parse
    args = parser.parse_args()

    try:
        # retrieve options
        input_fh = args.input
        output_fh = args.output
        header_lines = args.header_lines
        key_args = []
        for k in args.key:
            key_args.extend(["-k", k])

        # sed header
        if header_lines > 0:
            sed_header = ["sed", "-n", f"1,{header_lines:d}p"]
            subprocess.check_call(sed_header, stdin=input_fh, stdout=output_fh)
            input_fh.seek(0)

        # grep comments
        grep_comments = ["grep", "^#"]
        exit_code = subprocess.call(grep_comments, stdout=output_fh)
        if exit_code not in [0, 1]:
            stop_err("Searching for comment lines failed")

        # grep and sort columns
        if header_lines > 0:
            sed_cmd = ["sed", f"1,{header_lines:d}d"]
            sed_header_restore = subprocess.Popen(sed_cmd, stdin=input_fh, stdout=subprocess.PIPE)
            pipe_stdin = sed_header_restore.stdout
        else:
            pipe_stdin = input_fh
        grep = subprocess.Popen(["grep", "^[^#]"], stdin=pipe_stdin, stdout=subprocess.PIPE)
        sort = subprocess.Popen(["sort", "-f", "-t", "\t"] + key_args, stdin=grep.stdout, stdout=output_fh)
        # wait for commands to complete
        sort.communicate()
        assert sort.returncode == 0, f"sort pipeline exited with non-zero exit code: {sort.returncode:d}"

    except Exception as ex:
        stop_err("Error running sorter.py\n" + str(ex))

    # exit
    sys.exit(0)


if __name__ == "__main__":
    main()
