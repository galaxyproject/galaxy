#!/usr/bin/env python

import optparse
import sqlite3
import string
import sys
import tempfile

import six


def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()


def solid2sanger( quality_string, min_qual=0 ):
    sanger = ""
    quality_string = quality_string.rstrip( " " )
    for qv in quality_string.split(" "):
        try:
            if int( qv ) < 0:
                qv = '0'
            if int( qv ) < min_qual:
                return False
                break
            sanger += chr( int( qv ) + 33 )
        except:
            pass
    return sanger


def Translator(frm='', to='', delete=''):
    if len(to) == 1:
        to = to * len(frm)
    if six.PY2:
        trans = string.maketrans(frm, to)
    else:
        trans = str.maketrans(frm, to)

    def callable(s):
        return s.translate(trans, delete)

    return callable


def merge_reads_qual( f_reads, f_qual, f_out, trim_name=False, out='fastq', double_encode=False, trim_first_base=False, pair_end_flag='', min_qual=0, table_name=None ):
    # Reads from two files f_csfasta (reads) and f_qual (quality values) and produces output in three formats depending on out parameter,
    # which can have three values: fastq, txt, and db
    # fastq = fastq format
    # txt = space delimited format with defline, reads, and qvs
    # dp = dump data into sqlite3 db.
    # IMPORTNAT! If out = db two optins must be provided:
    #   1. f_out must be a db connection object initialized with sqlite3.connect()
    #   2. table_name must be provided
    if out == 'db':
        cursor = f_out.cursor()
        sql = "create table %s (name varchar(50) not null, read blob, qv blob)" % table_name
        cursor.execute(sql)

    lines = []
    line = " "
    while line:
        for f in [ f_reads, f_qual ]:
            line = f.readline().rstrip( '\n\r' )
            while line.startswith( '#' ):
                line = f.readline().rstrip( '\n\r' )
            lines.append( line )

        if lines[0].startswith( '>' ) and lines[1].startswith( '>' ):
            if lines[0] != lines[1]:
                stop_err('Files reads and quality score files are out of sync and likely corrupted. Please, check your input data')

            defline = lines[0][1:]
            if trim_name and ( defline[ len(defline) - 3: ] == "_F3" or defline[ len(defline) - 3: ] == "_R3" ):
                defline = defline[ :len(defline) - 3 ]

        elif ( not lines[0].startswith( '>' ) and not lines[1].startswith( '>' ) and len( lines[0] ) > 0 and len( lines[1] ) > 0 ):
            if trim_first_base:
                lines[0] = lines[0][1:]
            if double_encode:
                de = Translator(frm="0123.", to="ACGTN")
                lines[0] = de(lines[0])
            qual = solid2sanger( lines[1], int( min_qual ) )
            if qual:
                if out == 'fastq':
                    f_out.write( "@%s%s\n%s\n+\n%s\n" % ( defline, pair_end_flag, lines[0], qual ) )
                if out == 'txt':
                    f_out.write( '%s %s %s\n' % (defline, lines[0], qual ) )
                if out == 'db':
                    cursor.execute('insert into %s values("%s","%s","%s")' % (table_name, defline, lines[0], qual ) )
        lines = []


def main():
    usage = "%prog --fr F3.csfasta --fq R3.csfasta --fout fastq_output_file [option]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        '--fr', '--f_reads',
        metavar="F3_CSFASTA_FILE",
        dest='fr',
        help='Name of F3 file with color space reads')
    parser.add_option(
        '--fq', '--f_qual',
        metavar="F3_QUAL_FILE",
        dest='fq',
        help='Name of F3 file with color quality values')
    parser.add_option(
        '--fout', '--f3_fastq_output',
        metavar="F3_OUTPUT",
        dest='fout',
        help='Name for F3 output file')
    parser.add_option(
        '--rr', '--r_reads',
        metavar="R3_CSFASTA_FILE",
        dest='rr',
        default=False,
        help='Name of R3 file with color space reads')
    parser.add_option(
        '--rq', '--r_qual',
        metavar="R3_QUAL_FILE",
        dest='rq',
        default=False,
        help='Name of R3 file with color quality values')
    parser.add_option(
        '--rout',
        metavar="R3_OUTPUT",
        dest='rout',
        help='Name for F3 output file')
    parser.add_option(
        '-q', '--min_qual',
        dest='min_qual',
        default='-1000',
        help='Minimum quality threshold for printing reads. If a read contains a single call with QV lower than this value, it will not be reported. Default is -1000')
    parser.add_option(
        '-t', '--trim_name',
        dest='trim_name',
        action='store_true',
        default=False,
        help='Trim _R3 and _F3 off read names. Default is False')
    parser.add_option(
        '-f', '--trim_first_base',
        dest='trim_first_base',
        action='store_true',
        default=False,
        help='Remove the first base of reads in color-space. Default is False')
    parser.add_option(
        '-d', '--double_encode',
        dest='de',
        action='store_true',
        default=False,
        help='Double encode color calls as nucleotides: 0123. becomes ACGTN. Default is False')

    options, args = parser.parse_args()

    if not ( options.fout and options.fr and options.fq ):
        parser.error("""
        One or more of the three required paremetrs is missing:
        (1) --fr F3.csfasta file
        (2) --fq F3.qual file
        (3) --fout name of output file
        Use --help for more info
        """)

    fr = open( options.fr, 'r' )
    fq = open( options.fq, 'r' )
    f_out = open( options.fout, 'w' )

    if options.rr and options.rq:
        rr = open( options.rr, 'r' )
        rq = open( options.rq, 'r' )
        if not options.rout:
            parser.error("Provide the name for f3 output using --rout option. Use --help for more info")
        r_out = open( options.rout, 'w' )

        db = tempfile.NamedTemporaryFile()

        try:
            con = sqlite3.connect(db.name)
            cur = con.cursor()
        except:
            stop_err('Cannot connect to %s\n') % db.name

        merge_reads_qual( fr, fq, con, trim_name=options.trim_name, out='db', double_encode=options.de, trim_first_base=options.trim_first_base, min_qual=options.min_qual, table_name="f3" )
        merge_reads_qual( rr, rq, con, trim_name=options.trim_name, out='db', double_encode=options.de, trim_first_base=options.trim_first_base, min_qual=options.min_qual, table_name="r3" )
        cur.execute('create index f3_name on f3( name )')
        cur.execute('create index r3_name on r3( name )')

        cur.execute('select * from f3,r3 where f3.name = r3.name')
        for item in cur:
            f_out.write( "@%s%s\n%s\n+\n%s\n" % (item[0], "/1", item[1], item[2]) )
            r_out.write( "@%s%s\n%s\n+\n%s\n" % (item[3], "/2", item[4], item[5]) )

    else:
        merge_reads_qual( fr, fq, f_out, trim_name=options.trim_name, out='fastq', double_encode=options.de, trim_first_base=options.trim_first_base, min_qual=options.min_qual )

    f_out.close()


if __name__ == "__main__":
    main()
