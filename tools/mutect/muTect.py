#!/usr/bin/env python
# taken from an original script by Kyle Ellrott at UCSC

import sys
import re
import os
import shutil
import subprocess
import tempfile
import vcf
import argparse
import logging
from string import Template
from multiprocessing import Pool

#break the fasta index file into chunks to be worked on by each MuTect instance: faidx - an index enabling random access to FASTA files
def fai_chunk(path, blocksize):
    #get the lines in the index file and create a map of reference chromossome/contig/sequence name to reference chromosome/contig/sequence length in bases
    seq_map = {}
    with open( path ) as handle:
        for line in handle:
            tmp = line.split("\t")
            seq_map[tmp[0]] = long(tmp[1])
   
    #return the chromosome/contig/sequence name and start and end range in chunks of maximum blocksize chunks
    for seq in seq_map:
        l = seq_map[seq]
        for i in xrange(1, l, blocksize):
            yield (seq, i, min(i+blocksize-1, l))

#run a MuTect instance and report errors to calling process stderr and return error code
def cmd_caller(cmd):
    logging.info("RUNNING: %s" % (cmd))
    print "running", cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if len(stderr):
        print stderr
    return p.returncode

# run muTect instances on a pool of CPUs
def cmds_runner(cmds, cpus):
    p = Pool(cpus)
    values = p.map(cmd_caller, cmds, 1)

def call_cmd_iter(java, mutect, ref_seq, block_size, tumor_bam, normal_bam, output_base, cosmic, dbsnp, contamination):

    """
    --cosmic $args.cosmic
    --dbsnp $args.dbsnp
    """

    contamination_line = ""
    if contamination is not None:
        contamination_line = "--fraction_contamination %s" % (contamination)

    template = Template("""
${JAVA}
-Xmx2g -XX:ParallelGCThreads=2 -jar ${MUTECT}
--analysis_type MuTect
--reference_sequence ${REF_SEQ}
--intervals ${INTERVAL}
--input_file:normal ${NORMAL_BAM}
--input_file:tumor ${TUMOR_BAM}
--out ${OUTPUT_BASE}.${BLOCK_NUM}.out
${COSMIC_LINE}
${DBSNP_LINE}
${CONTAMINATION_LINE}
--coverage_file ${OUTPUT_BASE}.${BLOCK_NUM}.coverage
--vcf ${OUTPUT_BASE}.${BLOCK_NUM}.vcf
""".replace("\n", " "))

    #create a mutect command call for each block of bases of size blocksize or smaller from the reference sequence bam file
    for i, block in enumerate(fai_chunk( ref_seq + ".fai", block_size ) ):
        cosmic_line = ""
#        if cosmic is not None:
        if cosmic != 'None':     # using this test because test 'if cosmic is not None:' does not work on python version 2.7.6
            cosmic_line = "--cosmic %s" % (cosmic)
        dbsnp_line = ""
#        if dbsnp is not None:
        if dbsnp != 'None':     # using this test because test 'if dbsnp is not None:' does not work on python version 2.7.6
            dbsnp_line = "--dbsnp %s" % (dbsnp)

        cmd = template.substitute(
            dict(
                JAVA=java,
                REF_SEQ=ref_seq,
                BLOCK_NUM=i,
                INTERVAL="%s:%s-%s" % (block[0], block[1], block[2]) ),
                MUTECT=mutect,
                TUMOR_BAM=tumor_bam,
                NORMAL_BAM=normal_bam,
                OUTPUT_BASE=output_base,
                COSMIC_LINE=cosmic_line,
                DBSNP_LINE=dbsnp_line,
                CONTAMINATION_LINE=contamination_line
        )
        yield cmd, "%s.%s" % (output_base, i)



def run_mutect(args):
    sam_tools_exe_path = os.environ['SAMTOOLS_EXE_PATH']

    workdir = tempfile.mkdtemp(dir=args['workdir'], prefix="mutect_work_")
    print "workdir is" + workdir

    tumor_bam = os.path.join(workdir, "tumor.bam")
    normal_bam = os.path.join(workdir, "normal.bam")
    os.symlink(os.path.abspath(args["input_file:normal"]), normal_bam)
    os.symlink(os.path.abspath(args['input_file:tumor']),  tumor_bam)

    if args['input_file:index:normal'] is not None: 						#if there is a normal bam index file argument
        print "MuTect python script: index argument exists; creating symlink to normal bam index file"		
        os.symlink(os.path.abspath(args["input_file:index:normal"]), normal_bam + ".bai")       #create a symlink to the normal bam index file
    elif os.path.exists(os.path.abspath(args["input_file:normal"]) + ".bai"):                   #otherwise if there is a normal bam file and and index file is found there
        print "MuTect python script: using symlink to existing normal bam index file " + os.path.abspath(args["input_file:normal"]) + ".bai"   
        os.symlink(os.path.abspath(args["input_file:normal"]) + ".bai", normal_bam + ".bai")    #create a symlink to the normal bam index file
    else:
        print "MuTect python script: indexing normal bam"
        #otherwise call samtools to create an index file where the normal bam file is
        try:
            subprocess.check_call( [sam_tools_exe_path, "index", normal_bam] ) 
        except subprocess.CalledProcessError, e:
            print "!!!!!!!!!!!!MuTect python script: samtools index normal bam ERROR: stdout output:\n", e.output


    if args['input_file:index:tumor'] is not None:
        print "MuTect python script: index argument exists; creating symlink to tumor bam index file"		
        os.symlink(os.path.abspath(args["input_file:index:tumor"]), tumor_bam + ".bai")
    elif os.path.exists(os.path.abspath(args["input_file:tumor"]) + ".bai"):
        print "MuTect python script: using symlink to existing tumor bam index file " + os.path.abspath(args["input_file:tumor"]) + ".bai" 
        os.symlink(os.path.abspath(args["input_file:tumor"]) + ".bai", tumor_bam + ".bai")
    else:
        print "indexing tumor bam"
        try:  
           subprocess.check_call( [sam_tools_exe_path, "index", tumor_bam] )
        except subprocess.CalledProcessError, e:
            print "!!!!!!!!!!!!samtools index tumor bam ERROR: stdout output:\n", e.output

    ref_seq = os.path.join(workdir, "ref_genome.fasta")
    ref_dict = os.path.join(workdir, "ref_genome.dict")
    os.symlink(os.path.abspath(args['reference_sequence']), ref_seq)
    #use the faidx command in samtools to prepare the fasta index file. This file describes byte offsets in the fasta reference file for each contig, 
    #allowing us to compute exactly where a particular reference base at contig:pos is in the fasta filetext file 
    #with one record per line for each of the fasta contigs. Each record is of the: contig, size, location, basesPerLine, bytesPerLine.
    subprocess.check_call( [sam_tools_exe_path, "faidx", ref_seq] )
    subprocess.check_call( [args['java'], "-jar",
        args['dict_jar'],
        "R=%s" % (ref_seq),
        "O=%s" % (ref_dict)
    ])

    contamination = None
    if args["fraction_contamination"] is not None:
        contamination = args["fraction_contamination"]
    if args["fraction_contamination_file"] is not None:
        with open(args["fraction_contamination_file"]) as handle:
            line = handle.readline()
            contamination = line.split()[0]

    #create a list of MuTect commands for each chunk of a BAM file
    cmds = list(call_cmd_iter(ref_seq=ref_seq,
        java=args['java'],
        mutect=args['mutect'],
        block_size=args['b'],
        tumor_bam=tumor_bam,
        normal_bam=normal_bam,
        output_base=os.path.join(workdir, "output.file"),
        cosmic=args['cosmic'],
        dbsnp=args['dbsnp'],
        contamination = contamination
        )
    )

    #run each MuTech command from the list as a separate process
    rvals = cmds_runner(list(a[0] for a in cmds), args['ncpus'])

    #read the output vcf file for each block and write the data into one vcf output file
    vcf_writer = None
    for cmd, file in cmds:
        vcf_reader = vcf.Reader(filename=file + ".vcf")
        if vcf_writer is None:
            vcf_writer = vcf.Writer(open(os.path.join(args['vcf']), "w"), vcf_reader)
        for record in vcf_reader:
            vcf_writer.write_record(record)
    vcf_writer.close()

    if args['out'] is not None:
        with open(args['out'], "w") as handle:
            for cmd, file in cmds:
                with open(file + ".out") as ihandle:
                    for line in ihandle:
                        handle.write(line)

    #read the output coverage file for each block and write the data into one coverage output file
    first_file = True
    if args['coverage_file'] is not None:
        with open(args['coverage_file'], "w") as handle:
            for cmd, file in cmds:
                with open(file + ".coverage") as ihandle:
                    first_line = True
                    for line in ihandle:
                        if first_line:
                            if first_file:
                                handle.write(line)
                                first_line = False
                                first_file = False
                        else:
                            handle.write(line)


    if not args['no_clean']:
        shutil.rmtree(workdir)



if __name__ == "__main__":
    picard_path = os.environ['PICARD_PATH']
    mutect_jar_path = os.environ['MUTECT_JAR_PATH']

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mutect", help="Which Copy of Mutect", default=mutect_jar_path)

    parser.add_argument("--input_file:index:normal")
    parser.add_argument("--input_file:normal", required=True)
    parser.add_argument("--input_file:index:tumor")
    parser.add_argument("--input_file:tumor", required=True)
    parser.add_argument("--reference-sequence", required=True)
    parser.add_argument("--ncpus", type=int, default=8)
    parser.add_argument("--workdir", default="/tmp")
    parser.add_argument("--cosmic")
    parser.add_argument("--dbsnp")
    parser.add_argument("--out", default=None)
    parser.add_argument("--coverage_file", default=None)
    parser.add_argument("--fraction_contamination", default=None)
    parser.add_argument("--fraction_contamination-file", default=None)
    parser.add_argument("--vcf", required=True)
    parser.add_argument("--no-clean", action="store_true", default=True)
    parser.add_argument("--java", default="java")

    parser.add_argument("-b", type=long, help="Parallel Block Size", default=50000000)

    parser.add_argument("--dict-jar", default=picard_path + "/CreateSequenceDictionary.jar")

    args = parser.parse_args()
    run_mutect(vars(args))
