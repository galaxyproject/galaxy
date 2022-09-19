#!/usr/bin/env python
"""
Runs Ben's simulation.

usage: %prog [options]
   -i, --input=i: Input genome (FASTA format)
   -g, --genome=g: If built-in, the genome being used
   -l, --read_len=l: Read length
   -c, --avg_coverage=c: Average coverage
   -e, --error_rate=e: Error rate (0-1)
   -n, --num_sims=n: Number of simulations to run
   -p, --polymorphism=p: Frequency/ies for minor allele (comma-separate list of 0-1)
   -d, --detection_thresh=d: Detection thresholds (comma-separate list of 0-1)
   -p, --output_png=p: Plot output
   -s, --summary_out=s: Whether or not to output a file with summary of all simulations
   -m, --output_summary=m: File name for output summary of all simulations
   -f, --new_file_path=f: Directory for summary output files
"""
# removed output of all simulation results on request (not working)
#   -r, --sim_results=r: Output all tabular simulation results (number of polymorphisms times number of detection thresholds)
#   -o, --output=o: Base name for summary output for each run
from __future__ import print_function

import itertools
import os
import random
import sys
import tempfile

from bx.cookbook import doc_optparse
from rpy import r


def stop_err(msg):
    sys.stderr.write("%s\n" % msg)
    sys.exit()


def __main__():
    # Parse Command Line
    options, args = doc_optparse.parse(__doc__)
    # validate parameters
    error = ""
    try:
        read_len = int(options.read_len)
        if read_len <= 0:
            raise Exception(" greater than 0")
    except TypeError as e:
        error = ": %s" % str(e)
    if error:
        stop_err("Make sure your number of reads is an integer value%s" % error)
    error = ""
    try:
        avg_coverage = int(options.avg_coverage)
        if avg_coverage <= 0:
            raise Exception(" greater than 0")
    except Exception as e:
        error = ": %s" % str(e)
    if error:
        stop_err("Make sure your average coverage is an integer value%s" % error)
    error = ""
    try:
        error_rate = float(options.error_rate)
        if error_rate >= 1.0:
            error_rate = 10 ** (-error_rate / 10.0)
        elif error_rate < 0:
            raise Exception(" between 0 and 1")
    except Exception as e:
        error = ": %s" % str(e)
    if error:
        stop_err("Make sure the error rate is a decimal value%s or the quality score is at least 1" % error)
    try:
        num_sims = int(options.num_sims)
    except TypeError as e:
        stop_err("Make sure the number of simulations is an integer value: %s" % str(e))
    if options.polymorphism != "None":
        polymorphisms = [float(p) for p in options.polymorphism.split(",")]
    else:
        stop_err("Select at least one polymorphism value to use")
    if options.detection_thresh != "None":
        detection_threshes = [float(dt) for dt in options.detection_thresh.split(",")]
    else:
        stop_err("Select at least one detection threshold to use")

    # mutation dictionaries
    hp_dict = {"A": "G", "G": "A", "C": "T", "T": "C", "N": "N"}  # heteroplasmy dictionary
    mt_dict = {"A": "C", "C": "A", "G": "T", "T": "G", "N": "N"}  # misread dictionary

    # read fasta file to seq string
    all_lines = open(options.input, "rb").readlines()
    seq = ""
    for line in all_lines:
        line = line.rstrip()
        if line.startswith(">"):
            pass
        else:
            seq += line.upper()
    seq_len = len(seq)

    # output file name template
    # removed output of all simulation results on request (not working)
    #    if options.sim_results == "true":
    #        out_name_template = os.path.join( options.new_file_path, 'primary_output%s_' + options.output + '_visible_tabular' )
    #    else:
    #        out_name_template = tempfile.NamedTemporaryFile().name + '_%s'
    out_name_template = tempfile.NamedTemporaryFile().name + "_%s"
    print("out_name_template:", out_name_template)

    # set up output files
    outputs = {}
    i = 1
    for p in polymorphisms:
        outputs[p] = {}
        for d in detection_threshes:
            outputs[p][d] = out_name_template % i
            i += 1

    # run sims
    for polymorphism in polymorphisms:
        for detection_thresh in detection_threshes:
            output = open(outputs[polymorphism][detection_thresh], "wb")
            output.write("FP\tFN\tGENOMESIZE=%s\n" % seq_len)
            sim_count = 0
            while sim_count < num_sims:
                # randomly pick heteroplasmic base index
                hbase = random.randrange(seq_len)
                # hbase = seq_len/2#random.randrange( 0, seq_len )
                # create 2D quasispecies list
                qspec = [[] for _ in range(seq_len)]
                # simulate read indices and assign to quasispecies
                i = 0
                while i < (avg_coverage * (seq_len / read_len)):  # number of reads (approximates coverage)
                    start = random.randrange(seq_len)
                    if random.random() < 0.5:  # positive sense read
                        end = start + read_len  # assign read end
                        if end > seq_len:  # overshooting origin
                            read = itertools.chain(range(start, seq_len), range(0, end - seq_len))
                        else:  # regular read
                            read = range(start, end)
                    else:  # negative sense read
                        end = start - read_len  # assign read end
                        if end < -1:  # overshooting origin
                            read = itertools.chain(range(start, -1, -1), range(seq_len - 1, seq_len + end, -1))
                        else:  # regular read
                            read = range(start, end, -1)
                    # assign read to quasispecies list by index
                    for j in read:
                        if j == hbase and random.random() < polymorphism:  # heteroplasmic base is variant with p = het
                            ref = hp_dict[seq[j]]
                        else:  # ref is the verbatim reference nucleotide (all positions)
                            ref = seq[j]
                        if random.random() < error_rate:  # base in read is misread with p = err
                            qspec[j].append(mt_dict[ref])
                        else:  # otherwise we carry ref through to the end
                            qspec[j].append(ref)
                    # last but not least
                    i += 1
                bases, fpos, fneg = {}, 0, 0  # last two will be outputted to summary file later
                for i, nuc in enumerate(seq):
                    cov = len(qspec[i])
                    bases["A"] = qspec[i].count("A")
                    bases["C"] = qspec[i].count("C")
                    bases["G"] = qspec[i].count("G")
                    bases["T"] = qspec[i].count("T")
                    # calculate max NON-REF deviation
                    del bases[nuc]
                    maxdev = float(max(bases.values())) / cov
                    # deal with non-het sites
                    if i != hbase:
                        if maxdev >= detection_thresh:  # greater than detection threshold = false positive
                            fpos += 1
                    # deal with het sites
                    if i == hbase:
                        hnuc = hp_dict[nuc]  # let's recover het variant
                        if (
                            float(bases[hnuc]) / cov
                        ) < detection_thresh:  # less than detection threshold = false negative
                            fneg += 1
                        del bases[hnuc]  # ignore het variant
                        maxdev = float(max(bases.values())) / cov  # check other non-ref bases at het site
                        if maxdev >= detection_thresh:  # greater than detection threshold = false positive (possible)
                            fpos += 1
                # output error sums and genome size to summary file
                output.write("%d\t%d\n" % (fpos, fneg))
                sim_count += 1
            # close output up
            output.close()

    # Parameters (heteroplasmy, error threshold, colours)
    r(
        """
    het=c(%s)
    err=c(%s)
    grade = (0:32)/32
    hues = rev(gray(grade))
    """
        % (",".join(str(p) for p in polymorphisms), ",".join(str(d) for d in detection_threshes))
    )

    # Suppress warnings
    r("options(warn=-1)")

    # Create allsum (for FP) and allneg (for FN) objects
    r("allsum <- data.frame()")
    for polymorphism in polymorphisms:
        for detection_thresh in detection_threshes:
            output = outputs[polymorphism][detection_thresh]
            cmd = """
                  ngsum = read.delim('%s', header=T)
                  ngsum$fprate <- ngsum$FP/%s
                  ngsum$hetcol <- %s
                  ngsum$errcol <- %s
                  allsum <- rbind(allsum, ngsum)
                  """ % (
                output,
                seq_len,
                polymorphism,
                detection_thresh,
            )
            r(cmd)

    if os.path.getsize(output) == 0:
        for p in outputs.keys():
            for d in outputs[p].keys():
                sys.stderr.write(outputs[p][d] + " " + str(os.path.getsize(outputs[p][d])) + "\n")

    if options.summary_out == "true":
        r('write.table(summary(ngsum), file="%s", quote=FALSE, sep="\t", row.names=FALSE)' % options.output_summary)

    # Summary objects (these could be printed)
    r(
        """
    tr_pos <- tapply(allsum$fprate,list(allsum$hetcol,allsum$errcol), mean)
    tr_neg <- tapply(allsum$FN,list(allsum$hetcol,allsum$errcol), mean)
    cat('\nFalse Positive Rate Summary\n\t', file='%s', append=T, sep='\t')
    write.table(format(tr_pos, digits=4), file='%s', append=T, quote=F, sep='\t')
    cat('\nFalse Negative Rate Summary\n\t', file='%s', append=T, sep='\t')
    write.table(format(tr_neg, digits=4), file='%s', append=T, quote=F, sep='\t')
    """
        % tuple([options.output_summary] * 4)
    )

    # Setup graphs
    r(
        """
    png('%s', width=800, height=500, units='px', res=250)
    layout(matrix(data=c(1,2,1,3,1,4), nrow=2, ncol=3), widths=c(4,6,2), heights=c(1,10,10))
    """
        % options.output_png
    )

    # Main title
    genome = ""
    if options.genome:
        genome = "%s: " % options.genome
    r(
        """
    par(mar=c(0,0,0,0))
    plot(1, type='n', axes=F, xlab='', ylab='')
    text(1,1,paste('%sVariation in False Positives and Negatives (', %s, ' simulations, coverage ', %s,')', sep=''), font=2, family='sans', cex=0.7)
    """
        % (genome, options.num_sims, options.avg_coverage)
    )

    # False positive boxplot
    r(
        """
    par(mar=c(5,4,2,2), las=1, cex=0.35)
    boxplot(allsum$fprate ~ allsum$errcol, horizontal=T, ylim=rev(range(allsum$fprate)), cex.axis=0.85)
    title(main='False Positives', xlab='false positive rate', ylab='')
    """
    )

    # False negative heatmap (note zlim command!)
    num_polys = len(polymorphisms)
    num_dets = len(detection_threshes)
    r(
        """
    par(mar=c(5,4,2,1), las=1, cex=0.35)
    image(1:%s, 1:%s, tr_neg, zlim=c(0,1), col=hues, xlab='', ylab='', axes=F, border=1)
    axis(1, at=1:%s, labels=rownames(tr_neg), lwd=1, cex.axis=0.85, axs='i')
    axis(2, at=1:%s, labels=colnames(tr_neg), lwd=1, cex.axis=0.85)
    title(main='False Negatives', xlab='minor allele frequency', ylab='detection threshold')
    """
        % (num_polys, num_dets, num_polys, num_dets)
    )

    # Scale alongside
    r(
        """
    par(mar=c(2,2,2,3), las=1)
    image(1, grade, matrix(grade, ncol=length(grade), nrow=1), col=hues, xlab='', ylab='', xaxt='n', las=1, cex.axis=0.85)
    title(main='Key', cex=0.35)
    mtext('false negative rate', side=1, cex=0.35)
    """
    )

    # Close graphics
    r(
        """
    layout(1)
    dev.off()
    """
    )


if __name__ == "__main__":
    __main__()
