#!/usr/bin/env python
# Dan Blankenberg
"""
Read text output from FIMO and create an interval file.
"""
import os
import shutil
import subprocess
import sys
import tempfile

from galaxy_utils.sequence.transform import DNA_reverse_complement

buffsize = 1048576


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def main():
    assert len(sys.argv) == 8, "Wrong number of arguments"
    sys.argv.pop(0)
    fimo_cmd = sys.argv.pop(0)
    html_path = sys.argv.pop(0)
    html_out = sys.argv.pop(0)
    interval_out = sys.argv.pop(0)
    txt_out = sys.argv.pop(0)
    xml_out = sys.argv.pop(0)
    gff_out = sys.argv.pop(0)

    # run fimo
    try:
        tmp_stderr = tempfile.NamedTemporaryFile()
        proc = subprocess.Popen(args=fimo_cmd, shell=True, stderr=tmp_stderr)
        returncode = proc.wait()
        tmp_stderr.seek(0)
        stderr = ""
        try:
            while True:
                stderr += tmp_stderr.read(buffsize)
                if not stderr or len(stderr) % buffsize != 0:
                    break
        except OverflowError:
            pass

        if returncode != 0:
            raise Exception(stderr)
    except Exception as e:
        raise Exception("Error running FIMO:\n" + str(e))

    shutil.move(os.path.join(html_path, "fimo.txt"), txt_out)
    shutil.move(os.path.join(html_path, "fimo.gff"), gff_out)
    shutil.move(os.path.join(html_path, "fimo.xml"), xml_out)
    shutil.move(os.path.join(html_path, "fimo.html"), html_out)

    out_file = open(interval_out, "wb")
    out_file.write(
        "#%s\n"
        % "\t".join(
            ("chr", "start", "end", "pattern name", "score", "strand", "matched sequence", "p-value", "q-value")
        )
    )
    for line in open(txt_out):
        if line.startswith("#"):
            continue
        fields = line.rstrip("\n\r").split("\t")
        start, end = int(fields[2]), int(fields[3])
        sequence = fields[7]
        if start > end:
            start, end = end, start  # flip start and end, and set strand
            strand = "-"
            sequence = DNA_reverse_complement(
                sequence
            )  # we want sequences relative to strand; FIMO always provides + stranded sequence
        else:
            strand = "+"
        start -= 1  # make 0-based start position
        out_file.write(
            "%s\n"
            % "\t".join((fields[1], str(start), str(end), fields[0], fields[4], strand, sequence, fields[5], fields[6]))
        )
    out_file.close()


if __name__ == "__main__":
    main()
