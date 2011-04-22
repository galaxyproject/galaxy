#!/usr/bin/env python
"""
Runs all available wrapped Picard tools.
usage: picard_wrapper.py [options]
"""

import optparse, os, sys, subprocess, tempfile, shutil
from galaxy import eggs

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def run_picard_cmd( base_cmd, jar_bin, picard_cmd, opts ):
    cmd = base_cmd % ( '', os.path.join( jar_bin, picard_cmd ), opts )
    tmp_dir = tempfile.mkdtemp()
    try:
        # Sort alignments by leftmost coordinates. File <out.prefix>.bam will be created. This command
        # may also create temporary files <out.prefix>.%d.bam when the whole alignment cannot be fitted
        # into memory ( controlled by option -m ).
        tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
        tmp_stderr = open( tmp, 'wb' )
        proc = subprocess.Popen( args=cmd, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
        returncode = proc.wait()
        tmp_stderr.close()
        # get stderr, allowing for case where it's very large
        tmp_stderr = open( tmp, 'rb' )
        stderr = ''
        buffsize = 1048576
        try:
            while True:
                stderr += tmp_stderr.read( buffsize )
                if not stderr or len( stderr ) % buffsize != 0:
                    break
        except OverflowError:
            pass
        tmp_stderr.close()
        if returncode != 0:
            raise Exception, stderr
    except Exception, e:
        #clean up temp files
        if os.path.exists( tmp_dir ):
            shutil.rmtree( tmp_dir )
        stop_err( 'Error : %s' % str( e ) )

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    # All tools
    parser.add_option( '', '--picard-cmd', dest='picard_cmd', help='The Picard command (jar name, basically) to use' )
    parser.add_option( '', '--output-format', dest='output_format', help='Primary output file format' )
    parser.add_option( '-j', '--jar_bin' )
    parser.add_option( '', '--picard-jar', dest='picard_jar', help='' )
    # Many tools
    parser.add_option( '', '--input', dest='input', help='Input SAM or BAM file' )
    parser.add_option( '', '--output-txt', dest='output_txt', help='Output file in text format' )
    parser.add_option( '', '--output-sam', dest='output_sam', help='Output file in SAM or BAM format' )
    parser.add_option( '', '--bai-file', dest='bai_file', help='The path to the index file for the input bam file' )
    parser.add_option( '', '--ref', dest='ref', help='Built-in reference with fasta and dict file' )
    # CreateSequenceDictionary
    parser.add_option( '', '--ref-file', dest='ref_file', help='Fasta to use as reference' )
    parser.add_option( '', '--species-name', dest='species_name', help='Species name to use in creating dict file from fasta file' )
    parser.add_option( '', '--build-name', dest='build_name', help='Name of genome assembly to use in creating dict file from fasta file' )
    parser.add_option( '', '--trunc-names', dest='trunc_names', help='Truncate sequence names at first whitespace from fasta file' )
    # MarkDuplicates
    parser.add_option( '', '--remove-dups', dest='remove_dups', help='Remove duplicates from output file' )
    parser.add_option( '', '--read-regex', dest='read_regex', help='If true assume input data are already sorted (most Galaxy sam/bam should be)' )
    parser.add_option( '', '--opt-dup-dist', dest='opt_dup_dist', help='The maximum offset between two duplicte clusters in order to consider them optical duplicates.' )
    # AddOrReplaceReadGroups
    parser.add_option( '', '--rg-opts', dest='rg_opts', help='Specify extra (optional) arguments with full, otherwise preSet' )
    parser.add_option( '', '--rg-lb', dest='rg_library', help='Read Group Library' )
    parser.add_option( '', '--rg-pl', dest='rg_platform', help='Read Group platform (e.g. illumina, solid)' )
    parser.add_option( '', '--rg-pu', dest='rg_plat_unit', help='Read Group platform unit (eg. run barcode) ' )
    parser.add_option( '', '--rg-sm', dest='rg_sample', help='Read Group sample name' )
    parser.add_option( '', '--rg-id', dest='rg_id', help='Read Group ID' )
    parser.add_option( '', '--rg-cn', dest='rg_seq_center', help='Read Group sequencing center name' )
    parser.add_option( '', '--rg-ds', dest='rg_desc', help='Read Group description' )
    # ReorderSam
    parser.add_option( '', '--allow-inc-dict-concord', dest='allow_inc_dict_concord', help='Allow incomplete dict concordance' )
    parser.add_option( '', '--allow-contig-len-discord', dest='allow_contig_len_discord', help='Allow contig length discordance' )
    # ReplaceSamHeader
    parser.add_option( '', '--header-file', dest='header_file', help='sam or bam file from which header will be read' )
    (options, args) = parser.parse_args()

    # need to add
    # output version # of tool


    tmp_dir = tempfile.mkdtemp()
    base_cmd = 'java %s -jar %s.jar %s'  # % ( jvm-args, PicardCommand, opts )

    # specify sam or bam file with extension
    if options.output_format == 'sam' or options.output_format == 'bam':
        tmp_out_fd, tmp_out_name = tempfile.mkstemp( suffix='.%s'%options.output_format )
        tmp_out = os.fdopen( tmp_out_fd, 'wb' )
        tmp_out.close()

    # set ref and dict files to use (create if necessary)
    if options.ref_file:
        tmp_ref_fd, tmp_ref_name = tempfile.mkstemp( dir=tmp_dir )#, suffix='.fa' )
        ref_file_name = '%s.fa' % tmp_ref_name
        # build dict
        ## need to change name of fasta to have fasta ext
        dict_file_name = ref_file_name.replace( '.fa', '.dict' )
        os.symlink( options.ref_file, ref_file_name )
        opts = ' REFERENCE=%s OUTPUT=%s URI=%s TRUNCATE_NAMES_AT_WHITESPACE=%s' % ( ref_file_name, dict_file_name, os.path.split( ref_file_name )[-1], options.trunc_names )
        if options.species_name:
            opts += ' SPECIES=%s' % options.species_name
        if options.build_name:
            opts += ' GENOME_ASSEMBLY=%s' % options.build_name
        run_picard_cmd( base_cmd, options.jar_bin, 'CreateSequenceDictionary', opts )
    elif options.ref:
        ref_file_name = options.ref

    # run relevant command(s)

    opts = 'VALIDATION_STRINGENCY=LENIENT'

    if options.picard_cmd == 'AddOrReplaceReadGroups':
        # sort order to match Galaxy's default
        opts += ' SORT_ORDER=coordinate'
        # input
        opts += ' INPUT=%s' % options.input
        # outputs
        opts += ' OUTPUT=%s' % tmp_out_name
        # required read groups
        opts += ' RGLB="%s"' % options.rg_library
        opts += ' RGPL="%s"' % options.rg_platform
        opts += ' RGPU="%s"' % options.rg_plat_unit
        opts += ' RGSM="%s"' % options.rg_sample
        # optional read groups
        if options.rg_opts == 'full':
            if options.rg_id:
                opts += ' RGID="%s"' % options.rg_id
            if options.rg_seq_center:
                opts += ' RGCN="%s"' % options.rg_seq_center
            if options.rg_desc:
                opts += ' RGDS="%s"' % options.rg_desc
        run_picard_cmd( base_cmd, options.jar_bin, options.picard_cmd, opts )
        shutil.move( tmp_out_name, options.output_sam )

    if options.picard_cmd == 'BamIndexStats':
        tmp_fd, tmp_name = tempfile.mkstemp( dir=tmp_dir )
        tmp_bam_name = '%s.bam' % tmp_name
        tmp_bai_name = '%s.bai' % tmp_bam_name
        os.symlink( options.input, tmp_bam_name )
        os.symlink( options.bai_file, tmp_bai_name )
        opts += ' INPUT=%s > %s' % ( tmp_bam_name, options.output_txt )
        run_picard_cmd( base_cmd, options.jar_bin, options.picard_cmd, opts )

    if options.picard_cmd == 'MarkDuplicates':
        # assume sorted even if header says otherwise
        opts += ' ASSUME_SORTED=true'
        # input
        opts += ' INPUT=%s' % options.input
        # outputs
        opts += ' OUTPUT=%s METRICS_FILE=%s' % ( tmp_out_name, options.output_txt )
        # remove or mark duplicates
        opts += ' REMOVE_DUPLICATES=%s' % options.remove_dups
        # the regular expression to be used to parse reads in incoming SAM file
        opts += ' READ_NAME_REGEX="%s"' % options.read_regex
        # maximum offset between two duplicate clusters
        try:
            opts += ' OPTICAL_DUPLICATE_PIXEL_DISTANCE=%i' % int( options.opt_dup_dist )
        except ValueError:
            stop_err( 'Make sure that the maximum offset is an integer: %s' % str( e ) )
        run_picard_cmd( base_cmd, options.jar_bin, options.picard_cmd, opts )
        shutil.move( tmp_out_name, options.output_sam )

    if options.picard_cmd == 'ReorderSam':
        # input
        opts += ' INPUT=%s' % options.input
        # output
        opts += ' OUTPUT=%s' % tmp_out_name
        # reference
        opts += ' REFERENCE=%s' % ref_file_name
        # incomplete dict concordance
        if options.allow_inc_dict_concord == 'true':
            opts += ' ALLOW_INCOMPLETE_DICT_CONCORDANCE=%s'
        # contig length discordance
        if options.allow_contig_len_discord == 'true':
            opts += ' ALLOW_CONTIG_LENGTH_DISCORDANCE=%s'
        run_picard_cmd( base_cmd, options.jar_bin, options.picard_cmd, opts )
        shutil.move( tmp_out_name, options.output_sam )

    if options.picard_cmd == 'ReplaceSamHeader':
        opts += ' INPUT=%s OUTPUT=%s' % ( options.input, tmp_out_name )
        opts += ' HEADER=%s' % options.header_file
        run_picard_cmd( base_cmd, options.jar_bin, options.picard_cmd, opts )
        shutil.move( tmp_out_name, options.output_sam )

    # clean up temp dir
    if os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )

if __name__=="__main__": __main__()
