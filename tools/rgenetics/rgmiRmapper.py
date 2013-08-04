"""
August 2011
mirdeep2 mapper.pl wrapper for Galaxy
mirdeep2 documentation shown below comes directly from http://www.mdc-berlin.de/en/research/research_teams/systems_biology_of_gene_regulatory_elements/projects/miRDeep/documentation.html
 
This wrapper just integrates all that hard work into the Galaxy framework
You must install mir2deep so it will run when this code calls it.
Please see the site http://www.mdc-berlin.de/en/research/research_teams/systems_biology_of_gene_regulatory_elements/projects/miRDeep/ 
for attribution of mir2deep itself.
This code only Copyright 2011 Ross lazarus
Released under the LGPL


========================
mapper.pl
description:
Processes reads and/or maps them to the reference genome.
input:
Default input is a file in fasta, seq.txt or qseq.txt format. More input can be given depending on the options used.
output:
The output depends on the options used (see below). Either a fasta file with processed reads or an arf file with with mapped reads, or both, are output.
options:
Read input file:
-a              input file is seq.txt format
-b              input file is qseq.txt format
-c              input file is fasta format
-e              input file is fastq format
-d              input file is a config file (see miRDeep2 documentation).
                options -a, -b or -c must be given with option -d.

Preprocessing/mapping:
-g              three-letter prefix for reads (by default 'seq')
-h              parse to fasta format
-i              convert rna to dna alphabet (to map against genome)
-j              remove all entries that have a sequence that contains letters
                other than a,c,g,t,u,n,A,C,G,T,U,N
-k seq          clip 3' adapter sequence
-l int          discard reads shorter than int nts
-m              collapse reads

-p genome       map to genome (must be indexed by bowtie-build). The 'genome'
                string must be the prefix of the bowtie index. For instance, if
                the first indexed file is called 'h_sapiens_37_asm.1.ebwt' then
                the prefix is 'h_sapiens_37_asm'.
-q              map with one mismatch in the seed (mapping takes longer)

-r int          a read is allowed to map up to this number of positions in the genome
                default is 5 

Output files:
-s file         print processed reads to this file
-t file         print read mappings to this file 

Other:
-u              do not remove directory with temporary files
-v              outputs progress report

-n              overwrite existing files
Examples:
The mapper module is designed as a tool to process deep sequencing reads and/or map them to the reference genome. The module works in sequence space, and can process or map data that is in sequence fasta format. A number of the functions of the mapper module are implemented specifically with Solexa/Illumina data in mind. For example on how to post-process mappings in color space, see example use 5:
Example use 1:
The user wishes to parse a file in qseq.txt format to fasta format, convert from RNA to DNA alphabet, remove entries with non-canonical letters (letters other than a,c,g,t,u,n,A,C,G,T,U,N), clip adapters, discard reads shorter than 18 nts and collapse the reads:
mapper.pl reads_qseq.txt -b -h -i -j -k TCGTATGCCGTCTTCTGCTTGT -l 18 -m -s reads_collapsed.fa
Example use 2:
The user wishes to map a fasta file against the reference genome. The genome has already been indexed by bowtie-build. The first of the indexed files is named genome.1.ebwt:
mapper.pl reads_collapsed.fa -c -p genome -t reads_collapsed_vs_genome.arf
Example use 3:
The user wishes to process the reads as in example use 1 and map the reads as in example use 2 in a single step, while observing the progress:
mapper.pl reads_qseq.txt -b -h -i -j -k TCGTATGCCGTCTTCTGCTTGT -l 18 -m -p genome -s reads_collapsed.fa -t reads_collapsed_vs_genome.arf -v
Example use 4:
The user wishes to parse a GEO file to fasta format and process it as in example use 1. The GEO file is in tabular format, with the first column showing the sequence and the second column showing the read counts:
geo2fasta.pl GSM.txt > reads.fa
mapper.pl reads.fa -c -h -i -j -k TCGTATGCCGTCTTCTGCTTGT -l 18 -m -s reads_collapsed.fa 
Example use 5:
The user has already removed 3' adapters in color space and has mapped the reads against the genome using the BWA tool. The BWA output file is named reads_vs_genome.sam. Notice that the BWA output contains extra fields that are not required for SAM format. Our converter requires these fields and thus may not work with all types of SAM files. The user wishes to generate 'reads_collapsed.fa' and 'reads_vs_genome.arf' to input to miRDeep2:
bwa_sam_converter.pl reads_vs_genome.sam reads.fa reads_vs_genome.arf

mapper.pl reads.fa -c -i -j -l 18 -m -s reads_collapsed.fa
Example use 6:
The user has sequencing data from different samples e.g. different cell-types. A config.txt file has to be created in which each line designates file locations and a unique 3 letter code. For instance:
sequencing_data_sample1.fa	sd1
sequencing_data_sample2.fa	sd2
sequencing_data_sample3.fa	sd3
The user wishes then to pool these files and use the generated files reads.fa and reads_vs_genome.fa for the miRDeep2 analysis.
mapper.pl config.txt -d -c -i -j -l 18 -m -p genome_index -s reads.fa -t reads_vs_genome.arf 
Since the reads_vs_genome.arf still contains the 3 letter code for each read mapped to genome the user can then later on dilute the contribution of the different samples to a predicted or known miRNA. It can also be used for example to define 'high confident' predictions if the results are filtered for miRNAs that have sequencing evidence from at least two samples.



"""
import optparse
import tempfile
import os
import sys
import subprocess
import time
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,getFileString

MIRDEEPWEB="http://www.mdc-berlin.de/en/research/research_teams/systems_biology_of_gene_regulatory_elements/projects/miRDeep/"

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


class mirdeep2:
    """Class = wrapper
    """
    
    def __init__(self,myName=None,opts=None):
        """
        """
        self.progname=myName
        self.opts = opts
        if not os.path.isdir(opts.output_dir):
            try:
                os.makedirs(opts.output_dir)
            except:
                print >> sys.stderr,'##Error: mir2deep mapper unable to create or find output directory %s. Stopping' % (opts.output_dir)
                sys.exit(1)
        cl = []
        a = cl.append  
        a('mapper.pl')
        a('%s' % opts.input)
        a('-g %s' % opts.prefix)
        a('-n') # write over existing Galaxy outputs
        if opts.formIn.startswith('fastq'):
            a('-e -h')
        elif opts.formIn == 'fasta':
            a('-c')
        else:
            a('-e')
        if opts.rna2dna:
            a('-i')
        if opts.clean:
            a('-j')
        if opts.clip3primeSequence:
            a('-k %s' % opts.clip3primeSequence)
        if opts.lengthMin:
            a('-l %s' % opts.lengthMin)
        if opts.collapse:
            a('-m')
        if opts.bowtieIndex:
            a('-p %s' % opts.bowtieIndex)
        if opts.outProcessedReads <> None:
            a('-s %s' % opts.outProcessedReads)
        if opts.printReadMappings <> None:
            a('-t %s' % opts.printReadMappings)
        if opts.misMatch:
            a('-q')
        self.cl = cl
     


    def run(self):
        """
        """       
        p = os.getenv('PATH')
        edir = self.opts.exeDir
        p = '%s:%s' % (edir,p)
        os.environ['PATH'] = p
        fplog,tlog = tempfile.mkstemp(prefix="mirdeep2_mapper_runner.log",dir=self.opts.output_dir)
        mapperlog = os.path.join(self.opts.output_dir,"mirdeep2_mapper.log")
        sto = open(tlog,'w')
        x = subprocess.Popen(' '.join(self.cl),shell=True,stdout=sto,stderr=sto,cwd=self.opts.output_dir,env=os.environ)
        retval = x.wait()
        sto.close()
        try:
            mlog = file(tlog,'r').readlines()
            os.unlink(tlog) # no longer needed
        except:
            mlog = '### %s Strange - no std out from mirdeep2 mapper.pl when running command line\n%s' % (timenow(),' '.join(cl))
        flist = os.listdir(self.opts.output_dir)
        flist.sort()
        flist = [os.path.join(self.opts.output_dir,x) for x in flist] # ugh
        html = [galhtmlprefix % self.progname,]
        html.append('<h3>See <a href="%s">%s</a> for documentation/attribution</h3>' % (MIRDEEPWEB,MIRDEEPWEB))
        html.append('<h1>Galaxy Outputs from mirdeep2 mapper.pl</h1>')
        html.append('CL=%s' % ' '.join(self.cl))
        if len(flist) > 0:
            html.append('<table>\n')
            for row in flist:
                fdir,fname = os.path.split(row)
                if not fname.startswith('.nfs'):
                     html.append('<tr><td><a href="%s">%s</a></td></tr>' % (fname,getFileString(fname,fdir)))
            html.append('</table>\n')
        else:
            html.append('<h2>### Error - mirdeep2 mapper.pl returned no files - please confirm that parameters are sane</h1>')
        html.append('<h3>mapper.pl log follows below</h3><hr><pre>\n')
        html += mlog
        html.append('</pre>\n')   
        html.append(galhtmlattr % (self.progname,timenow()))
        html.append(galhtmlpostfix)
        htmlf = file(self.opts.outhtml,'w')
        htmlf.write('\n'.join(html))
        htmlf.write('\n')
        htmlf.close()
        return retval

if __name__ == "__main__":
    """ 
-a              input file is seq.txt format
-b              input file is qseq.txt format
-c              input file is fasta format
-e              input file is fastq format
-g              three-letter prefix for reads (by default 'seq')
-h              parse to fasta format
-i              convert rna to dna alphabet (to map against genome)
-j              remove all entries that have a sequence that contains letters
                other than a,c,g,t,u,n,A,C,G,T,U,N
-k seq          clip 3' adapter sequence
-l int          discard reads shorter than int nts
-m              collapse reads
p genome       map to genome (must be indexed by bowtie-build). The 'genome'
                string must be the prefix of the bowtie index. For instance, if
                the first indexed file is called 'h_sapiens_37_asm.1.ebwt' then
                the prefix is 'h_sapiens_37_asm'.
-q              map with one mismatch in the seed (mapping takes longer)

-r int          a read is allowed to map up to this number of positions in the genome
                default is 5 

Output files:
-s file         print processed reads to this file
-t file         print read mappings to this file 

Other:
-u              do not remove directory with temporary files
-v              outputs progress report

-n              overwrite existing files


    called as:
      <command interpreter="python">
    rgmapper.py --formIn $input_file.ext --input "$input_file" --output_dir "$html_file.files_path" --outhtml "$html_file"
#if map.mapme=="yes"
-b "${ filter( lambda x: str( x[0] ) == str( $map.index ), $__app__.tool_data_tables[ 'bowtie_index' ].get_fields() )[0][-1] }" -o "$outProcessedReads"
#endif
    -p "$printReadMappings" --prefix "$prefix" 
#if int($lengthMin.value) > 0
-l "$lengthMin"
#endif
#if $clip3primeSequence
-k "$clip3primeSequence"
#endif
#if $misMatch
-q 
#endif
$clean $rna2dna $collapse $toFasta $misMatch
  </command>
    """
    op = optparse.OptionParser()
    a = op.add_option
    a('-i','--input',default=None)
    a('-e','--exeDir',default=None)
    a('--formIn',default='fastq')
    a('--prefix',default='seq')
    a('-r','--rna2dna',action="store_true",default=False) 
    a('-j','--clean',action="store_true",default=False)
    a('-k','--clip3primeSequence',default=None)
    a('-l','--lengthMin',default='35')
    a('-m','--collapse',action="store_true",default=False)
    a('-p','--bowtieIndex',default='hg19')
    a('-s','--outProcessedReads',default=None)
    a('-t','--printReadMappings',default=None)
    a('-q','--misMatch',action="store_true",default=False)
    a('--outhtml',default=None)
    a('--output_dir',default=None)
    opts, args = op.parse_args() 
    assert os.path.isfile(opts.input),'## mirdeep2 mapper runner unable to open supplied input file %s' % opts.input
    myName=os.path.split(sys.argv[0])[-1]
    m = mirdeep2(myName, opts=opts)
    retcode = m.run()
    if retcode:
        sys.exit(retcode) # indicate failure to job runner
    
    
