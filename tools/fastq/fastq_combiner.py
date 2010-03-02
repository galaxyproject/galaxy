#Dan Blankenberg
import sys, os, shutil
from galaxy_utils.sequence.fastq import fastqWriter, fastqSequencingRead, fastqCombiner, fastqFakeFastaScoreReader
from galaxy_utils.sequence.fasta import fastaReader, fastaNamedReader

def main():
    #Read command line arguments
    fasta_filename = sys.argv[1]
    fasta_type = sys.argv[2] or 'fasta' #should always be fasta or csfasta? what if txt?
    qual_filename = sys.argv[3]
    qual_type = sys.argv[4] or 'qualsanger' #qual454 qualsolid
    output_filename = sys.argv[5]
    force_quality_encoding = sys.argv[6]
    if force_quality_encoding == 'None':
        force_quality_encoding = None
    
    format = 'sanger'
    if fasta_type == 'csfasta' or qual_type == 'qualsolid':
        format = 'cssanger'
    elif qual_type == 'qualsolexa':
        format = 'solexa'
    elif qual_type == 'qualillumina':
        format = 'illumina'
    
    out = fastqWriter( open( output_filename, 'wb' ), format = format, force_quality_encoding = force_quality_encoding )
    if qual_filename == 'None':
        qual_input = fastqFakeFastaScoreReader( format, quality_encoding = force_quality_encoding )
    else:
        qual_input = fastaNamedReader( open( qual_filename, 'rb' )  )
    
    fastq_combiner = fastqCombiner( format )
    i = None
    skip_count = 0
    for i, sequence in enumerate( fastaReader( open( fasta_filename, 'rb' ) ) ):
        quality = qual_input.get( sequence )
        if quality:
            fastq_read = fastq_combiner.combine( sequence, quality )
            out.write( fastq_read )
        else:
            skip_count += 1
    out.close()
    if i is None:
        print "Your file contains no valid FASTA sequences."
    else:
        print qual_input.has_data()
        print 'Combined %s of %s sequences with quality scores (%.2f%%).' % ( i - skip_count + 1, i + 1, float( i - skip_count + 1 ) / float( i + 1 ) * 100.0 )

if __name__ == "__main__":
    main()
