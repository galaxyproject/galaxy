#!/usr/bin/env python
# Guruprasad Ananda
# MAQ mapper for SOLiD colourspace-reads
from __future__ import print_function

import os
import subprocess
import sys
import tempfile


def stop_err(msg):
    sys.stderr.write("%s\n" % msg)
    sys.exit()


def __main__():
    out_fname = sys.argv[1].strip()
    out_f2 = open(sys.argv[2].strip(), "r+")
    ref_fname = sys.argv[3].strip()
    f3_read_fname = sys.argv[4].strip()
    f3_qual_fname = sys.argv[5].strip()
    paired = sys.argv[6]
    if paired == "yes":
        r3_read_fname = sys.argv[7].strip()
        r3_qual_fname = sys.argv[8].strip()
    min_mapqual = int(sys.argv[9].strip())
    max_mismatch = int(sys.argv[10].strip())
    out_f3name = sys.argv[11].strip()
    subprocess_dict = {}

    ref_csfa = tempfile.NamedTemporaryFile()
    ref_bfa = tempfile.NamedTemporaryFile()
    ref_csbfa = tempfile.NamedTemporaryFile()
    cmd2_1 = "maq fasta2csfa %s > %s 2>&1" % (ref_fname, ref_csfa.name)
    cmd2_2 = "maq fasta2bfa %s %s 2>&1" % (ref_csfa.name, ref_csbfa.name)
    cmd2_3 = "maq fasta2bfa %s %s 2>&1" % (ref_fname, ref_bfa.name)
    try:
        os.system(cmd2_1)
        os.system(cmd2_2)
        os.system(cmd2_3)
    except Exception as erf:
        stop_err(str(erf) + "Error processing reference sequence")

    if paired == "yes":  # paired end reads
        tmpf = tempfile.NamedTemporaryFile()  # forward reads
        tmpr = tempfile.NamedTemporaryFile()  # reverse reads
        tmps = tempfile.NamedTemporaryFile()  # single reads
        tmpffastq = tempfile.NamedTemporaryFile()
        tmprfastq = tempfile.NamedTemporaryFile()
        tmpsfastq = tempfile.NamedTemporaryFile()

        cmd1 = "solid2fastq_modified.pl 'yes' %s %s %s %s %s %s %s 2>&1" % (
            tmpf.name,
            tmpr.name,
            tmps.name,
            f3_read_fname,
            f3_qual_fname,
            r3_read_fname,
            r3_qual_fname,
        )
        try:
            os.system(cmd1)
            os.system("gunzip -c %s >> %s" % (tmpf.name, tmpffastq.name))
            os.system("gunzip -c %s >> %s" % (tmpr.name, tmprfastq.name))
            os.system("gunzip -c %s >> %s" % (tmps.name, tmpsfastq.name))

        except Exception as eq:
            stop_err("Error converting data to fastq format." + str(eq))

        # Make a temp directory where the split fastq files will be stored
        try:
            split_dir = tempfile.mkdtemp()
            split_file_prefix_f = tempfile.mktemp(dir=split_dir)
            split_file_prefix_r = tempfile.mktemp(dir=split_dir)
            splitcmd_f = "split -a 2 -l %d %s %s" % (
                32000000,
                tmpffastq.name,
                split_file_prefix_f,
            )  # 32M lines correspond to 8M reads
            splitcmd_r = "split -a 2 -l %d %s %s" % (
                32000000,
                tmprfastq.name,
                split_file_prefix_r,
            )  # 32M lines correspond to 8M reads

            os.system(splitcmd_f)
            os.system(splitcmd_r)
            os.chdir(split_dir)
            ii = 0
            for fastq in os.listdir(split_dir):
                if not fastq.startswith(split_file_prefix_f.split("/")[-1]):
                    continue
                fastq_r = (
                    split_file_prefix_r + fastq.split(split_file_prefix_f.split("/")[-1])[1]
                )  # find the reverse strand fastq corresponding to forward strand fastq
                tmpbfq_f = tempfile.NamedTemporaryFile()
                tmpbfq_r = tempfile.NamedTemporaryFile()
                cmd3 = (
                    "maq fastq2bfq %s %s 2>&1; maq fastq2bfq %s %s 2>&1; maq map -c %s.csmap %s %s %s 1>/dev/null 2>&1; maq mapview %s.csmap > %s.txt"
                    % (
                        fastq,
                        tmpbfq_f.name,
                        fastq_r,
                        tmpbfq_r.name,
                        fastq,
                        ref_csbfa.name,
                        tmpbfq_f.name,
                        tmpbfq_r.name,
                        fastq,
                        fastq,
                    )
                )
                subprocess_dict["sp" + str(ii + 1)] = subprocess.Popen([cmd3], shell=True, stdout=subprocess.PIPE)
                ii += 1
            while True:
                all_done = True
                for j in range(len(subprocess_dict)):
                    if subprocess_dict["sp" + str(j + 1)].wait() != 0:
                        err = subprocess_dict["sp" + str(j + 1)].communicate()[1]
                        if err is not None:
                            stop_err("Mapping error: %s" % err)
                        all_done = False
                if all_done:
                    break
            cmdout = "for map in *.txt; do cat $map >> %s; done" % (out_fname)
            os.system(cmdout)

            tmpcsmap = tempfile.NamedTemporaryFile()
            cmd_cat_csmap = "for csmap in *.csmap; do cat $csmap >> %s; done" % (tmpcsmap.name)
            os.system(cmd_cat_csmap)

            tmppileup = tempfile.NamedTemporaryFile()
            cmdpileup = "maq pileup -m %s -q %s %s %s > %s" % (
                max_mismatch,
                min_mapqual,
                ref_bfa.name,
                tmpcsmap.name,
                tmppileup.name,
            )
            os.system(cmdpileup)
            tmppileup.seek(0)
            print("#chr\tposition\tref_nt\tcoverage\tSNP_count\tA_count\tT_count\tG_count\tC_count", file=out_f2)
            for line in open(tmppileup.name):
                elems = line.strip().split()
                ref_nt = elems[2].capitalize()
                read_nt = elems[4]
                coverage = int(elems[3])
                a, t, g, c = 0, 0, 0, 0
                ref_nt_count = 0
                for ch in read_nt:
                    ch = ch.capitalize()
                    if ch not in ["A", "T", "G", "C", ",", "."]:
                        continue
                    if ch in [",", "."]:
                        ch = ref_nt
                        ref_nt_count += 1
                    try:
                        nt_ind = ["A", "T", "G", "C"].index(ch)
                        if nt_ind == 0:
                            a += 1
                        elif nt_ind == 1:
                            t += 1
                        elif nt_ind == 2:
                            g += 1
                        else:
                            c += 1
                    except ValueError as we:
                        print(we, file=sys.stderr)
                print(
                    "%s\t%s\t%s\t%s\t%s\t%s" % ("\t".join(elems[:4]), coverage - ref_nt_count, a, t, g, c), file=out_f2
                )
        except Exception as er2:
            stop_err("Encountered error while mapping: %s" % (str(er2)))

    else:  # single end reads
        tmpf = tempfile.NamedTemporaryFile()
        tmpfastq = tempfile.NamedTemporaryFile()
        cmd1 = "solid2fastq_modified.pl 'no' %s %s %s %s %s %s %s 2>&1" % (
            tmpf.name,
            None,
            None,
            f3_read_fname,
            f3_qual_fname,
            None,
            None,
        )
        try:
            os.system(cmd1)
            os.system("gunzip -c %s >> %s" % (tmpf.name, tmpfastq.name))
            tmpf.close()
        except Exception:
            stop_err("Error converting data to fastq format.")

        # Make a temp directory where the split fastq files will be stored
        try:
            split_dir = tempfile.mkdtemp()
            split_file_prefix = tempfile.mktemp(dir=split_dir)
            splitcmd = "split -a 2 -l %d %s %s" % (
                32000000,
                tmpfastq.name,
                split_file_prefix,
            )  # 32M lines correspond to 8M reads
            os.system(splitcmd)
            os.chdir(split_dir)
            for i, fastq in enumerate(os.listdir(split_dir)):
                tmpbfq = tempfile.NamedTemporaryFile()
                cmd3 = (
                    "maq fastq2bfq %s %s 2>&1; maq map -c %s.csmap %s %s  1>/dev/null 2>&1; maq mapview %s.csmap > %s.txt"
                    % (fastq, tmpbfq.name, fastq, ref_csbfa.name, tmpbfq.name, fastq, fastq)
                )
                subprocess_dict["sp" + str(i + 1)] = subprocess.Popen([cmd3], shell=True, stdout=subprocess.PIPE)

            while True:
                all_done = True
                for j in range(len(subprocess_dict)):
                    if subprocess_dict["sp" + str(j + 1)].wait() != 0:
                        err = subprocess_dict["sp" + str(j + 1)].communicate()[1]
                        if err is not None:
                            stop_err("Mapping error: %s" % err)
                        all_done = False
                if all_done:
                    break

            cmdout = "for map in *.txt; do cat $map >> %s; done" % (out_fname)
            os.system(cmdout)

            tmpcsmap = tempfile.NamedTemporaryFile()
            cmd_cat_csmap = "for csmap in *.csmap; do cat $csmap >> %s; done" % (tmpcsmap.name)
            os.system(cmd_cat_csmap)

            tmppileup = tempfile.NamedTemporaryFile()
            cmdpileup = "maq pileup -m %s -q %s %s %s > %s" % (
                max_mismatch,
                min_mapqual,
                ref_bfa.name,
                tmpcsmap.name,
                tmppileup.name,
            )
            os.system(cmdpileup)
            tmppileup.seek(0)
            print("#chr\tposition\tref_nt\tcoverage\tSNP_count\tA_count\tT_count\tG_count\tC_count", file=out_f2)
            for line in open(tmppileup.name):
                elems = line.strip().split()
                ref_nt = elems[2].capitalize()
                read_nt = elems[4]
                coverage = int(elems[3])
                a, t, g, c = 0, 0, 0, 0
                ref_nt_count = 0
                for ch in read_nt:
                    ch = ch.capitalize()
                    if ch not in ["A", "T", "G", "C", ",", "."]:
                        continue
                    if ch in [",", "."]:
                        ch = ref_nt
                        ref_nt_count += 1
                    try:
                        nt_ind = ["A", "T", "G", "C"].index(ch)
                        if nt_ind == 0:
                            a += 1
                        elif nt_ind == 1:
                            t += 1
                        elif nt_ind == 2:
                            g += 1
                        else:
                            c += 1
                    except Exception:
                        pass
                print(
                    "%s\t%s\t%s\t%s\t%s\t%s" % ("\t".join(elems[:4]), coverage - ref_nt_count, a, t, g, c), file=out_f2
                )
        except Exception as er2:
            stop_err("Encountered error while mapping: %s" % (str(er2)))

    # Build custom track from pileup
    chr_list = []
    out_f2.seek(0)
    fcov = tempfile.NamedTemporaryFile()
    fout_a = tempfile.NamedTemporaryFile()
    fout_t = tempfile.NamedTemporaryFile()
    fout_g = tempfile.NamedTemporaryFile()
    fout_c = tempfile.NamedTemporaryFile()
    fcov.write(
        """track type=wiggle_0 name="Coverage track" description="Coverage track (from Galaxy)" color=0,0,0 visibility=2\n"""
    )
    fout_a.write(
        """track type=wiggle_0 name="Track A" description="Track A (from Galaxy)" color=255,0,0 visibility=2\n"""
    )
    fout_t.write(
        """track type=wiggle_0 name="Track T" description="Track T (from Galaxy)" color=0,255,0 visibility=2\n"""
    )
    fout_g.write(
        """track type=wiggle_0 name="Track G" description="Track G (from Galaxy)" color=0,0,255 visibility=2\n"""
    )
    fout_c.write(
        """track type=wiggle_0 name="Track C" description="Track C (from Galaxy)" color=255,0,255 visibility=2\n"""
    )

    for line in out_f2:
        if line.startswith("#"):
            continue
        elems = line.split()
        chr = elems[0]

        if chr not in chr_list:
            chr_list.append(chr)
            if not (chr.startswith("chr") or chr.startswith("scaffold")):
                chr = "chr"
            header = "variableStep chrom=%s" % (chr)
            fcov.write("%s\n" % (header))
            fout_a.write("%s\n" % (header))
            fout_t.write("%s\n" % (header))
            fout_g.write("%s\n" % (header))
            fout_c.write("%s\n" % (header))
        try:
            pos = int(elems[1])
            cov = int(elems[3])
            a = int(elems[5])
            t = int(elems[6])
            g = int(elems[7])
            c = int(elems[8])
        except Exception:
            continue
        fcov.write("%s\t%s\n" % (pos, cov))
        try:
            a_freq = a * 100.0 / cov
            t_freq = t * 100.0 / cov
            g_freq = g * 100.0 / cov
            c_freq = c * 100.0 / cov
        except ZeroDivisionError:
            a_freq = t_freq = g_freq = c_freq = 0
        fout_a.write("%s\t%s\n" % (pos, a_freq))
        fout_t.write("%s\t%s\n" % (pos, t_freq))
        fout_g.write("%s\t%s\n" % (pos, g_freq))
        fout_c.write("%s\t%s\n" % (pos, c_freq))

    fcov.seek(0)
    fout_a.seek(0)
    fout_g.seek(0)
    fout_t.seek(0)
    fout_c.seek(0)
    os.system(
        "cat %s %s %s %s %s | cat > %s" % (fcov.name, fout_a.name, fout_t.name, fout_g.name, fout_c.name, out_f3name)
    )


if __name__ == "__main__":
    __main__()
