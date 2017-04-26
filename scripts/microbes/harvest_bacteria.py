#!/usr/bin/env python
# Dan Blankenberg

# Harvest Bacteria
# Connects to NCBI's Microbial Genome Projects website and scrapes it for information.
# Downloads and converts annotations for each Genome
import os
import sys
import time
from ftplib import FTP
from urllib2 import urlopen
from urllib import urlretrieve

from BeautifulSoup import BeautifulSoup
from util import get_bed_from_genbank, get_bed_from_glimmer3, get_bed_from_GeneMarkHMM, get_bed_from_GeneMark

assert sys.version_info[:2] >= ( 2, 4 )

# this defines the types of ftp files we are interested in, and how to process/convert them to a form for our use
desired_ftp_files = {'GeneMark': {'ext': 'GeneMark-2.5f', 'parser': 'process_GeneMark'},
                    'GeneMarkHMM': {'ext': 'GeneMarkHMM-2.6m', 'parser': 'process_GeneMarkHMM'},
                    'Glimmer3': {'ext': 'Glimmer3', 'parser': 'process_Glimmer3'},
                    'fna': {'ext': 'fna', 'parser': 'process_FASTA'},
                    'gbk': {'ext': 'gbk', 'parser': 'process_Genbank'} }


# number, name, chroms, kingdom, group, genbank, refseq, info_url, ftp_url
def iter_genome_projects( url="http://www.ncbi.nlm.nih.gov/genomes/lproks.cgi?view=1", info_url_base="http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?db=genomeprj&cmd=Retrieve&dopt=Overview&list_uids=" ):
    for row in BeautifulSoup( urlopen( url ) ).findAll( name='tr', bgcolor=["#EEFFDD", "#E8E8DD"] ):
        row = str( row ).replace( "\n", "" ).replace( "\r", "" )

        fields = row.split( "</td>" )

        org_num = fields[0].split( "list_uids=" )[-1].split( "\"" )[0]

        name = fields[1].split( "\">" )[-1].split( "<" )[0]

        kingdom = "archaea"
        if "<td class=\"bacteria\" align=\"center\">B" in fields[2]:
            kingdom = "bacteria"

        group = fields[3].split( ">" )[-1]

        info_url = "%s%s" % ( info_url_base, org_num )

        org_genbank = fields[7].split( "\">" )[-1].split( "<" )[0].split( "." )[0]
        org_refseq = fields[8].split( "\">" )[-1].split( "<" )[0].split( "." )[0]

        # seems some things donot have an ftp url, try and except it here:
        try:
            ftp_url = fields[22].split( "href=\"" )[1].split( "\"" )[0]
        except:
            print "FAILED TO AQUIRE FTP ADDRESS:", org_num, info_url
            ftp_url = None

        chroms = get_chroms_by_project_id( org_num )

        yield org_num, name, chroms, kingdom, group, org_genbank, org_refseq, info_url, ftp_url


def get_chroms_by_project_id( org_num, base_url="http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?db=genomeprj&cmd=Retrieve&dopt=Overview&list_uids=" ):
    html_count = 0
    html = None
    while html_count < 500 and html is None:
        html_count += 1
        url = "%s%s" % ( base_url, org_num )
        try:
            html = urlopen( url )
        except:
            print "GENOME PROJECT FAILED:", html_count, "org:", org_num, url
            html = None
            time.sleep( 1 )  # Throttle Connection
    if html is None:
        "GENOME PROJECT COMPLETELY FAILED TO LOAD", "org:", org_num, "http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?db=genomeprj&cmd=Retrieve&dopt=Overview&list_uids=" + org_num
        return None

    chroms = []
    for chr_row in BeautifulSoup( html ).findAll( "tr", { "class": "vvv" } ):
        chr_row = str( chr_row ).replace( "\n", "" ).replace( "\r", "" )
        fields2 = chr_row.split( "</td>" )
        refseq = fields2[1].split( "</a>" )[0].split( ">" )[-1]
        # genbank = fields2[2].split( "</a>" )[0].split( ">" )[-1]
        chroms.append( refseq )

    return chroms


def get_ftp_contents( ftp_url ):
    ftp_count = 0
    ftp_contents = None
    while ftp_count < 500 and ftp_contents is None:
        ftp_count += 1
        try:
            ftp = FTP( ftp_url.split("/")[2] )
            ftp.login()
            ftp.cwd( ftp_url.split( ftp_url.split( "/" )[2] )[-1] )
            ftp_contents = ftp.nlst()
            ftp.close()
        except:
            ftp_contents = None
            time.sleep( 1 )  # Throttle Connection
    return ftp_contents


def scrape_ftp( ftp_contents, org_dir, org_num, refseq, ftp_url ):
    for file_type, items in desired_ftp_files.items():
        ext = items['ext']
        ftp_filename = "%s.%s" % ( refseq, ext )
        target_filename = os.path.join( org_dir, "%s.%s" % ( refseq, ext ) )
        if ftp_filename in ftp_contents:
            url_count = 0
            url = "%s/%s" % ( ftp_url, ftp_filename )
            results = None
            while url_count < 500 and results is None:
                url_count += 1
                try:
                    results = urlretrieve( url, target_filename )
                except:
                    results = None
                    time.sleep(1)  # Throttle Connection
            if results is None:
                "URL COMPLETELY FAILED TO LOAD:", url
                return

            # do special processing for each file type:
            if items['parser'] is not None:
                globals()[items['parser']]( target_filename, org_num, refseq )
        else:
            print "FTP filetype:", file_type, "not found for", org_num, refseq
    # FTP Files have been Loaded


def process_FASTA( filename, org_num, refseq ):
    fasta = []
    fasta = [line.strip() for line in open( filename, 'rb' ).readlines()]
    fasta_header = fasta.pop( 0 )[1:]
    fasta_header_split = fasta_header.split( "|" )
    chr_name = fasta_header_split.pop( -1 ).strip()
    accesions = {fasta_header_split[0]: fasta_header_split[1], fasta_header_split[2]: fasta_header_split[3]}
    fasta = "".join( fasta )

    # Create Chrom Info File:
    chrom_info_file = open( os.path.join( os.path.split( filename )[0], "%s.info" % refseq ), 'wb+' )
    chrom_info_file.write( "chromosome=%s\nname=%s\nlength=%s\norganism=%s\n" % ( refseq, chr_name, len( fasta ), org_num ) )
    try:
        chrom_info_file.write( "gi=%s\n" % accesions['gi'] )
    except:
        chrom_info_file.write( "gi=None\n" )
    try:
        chrom_info_file.write( "gb=%s\n" % accesions['gb'] )
    except:
        chrom_info_file.write( "gb=None\n" )
    try:
        chrom_info_file.write( "refseq=%s\n" % refseq )
    except:
        chrom_info_file.write( "refseq=None\n" )
    chrom_info_file.close()


def process_Genbank( filename, org_num, refseq ):
    # extracts 'CDS', 'tRNA', 'rRNA' features from genbank file
    features = get_bed_from_genbank( filename, refseq, ['CDS', 'tRNA', 'rRNA'] )
    for feature in features.keys():
        feature_file = open( os.path.join( os.path.split( filename )[0], "%s.%s.bed" % ( refseq, feature ) ), 'wb+' )
        feature_file.write( '\n'.join( features[feature] ) )
        feature_file.close()
    print "Genbank extraction finished for chrom:", refseq, "file:", filename


def process_Glimmer3( filename, org_num, refseq ):
    try:
        glimmer3_bed = get_bed_from_glimmer3( filename, refseq )
    except Exception as e:
        print "Converting Glimmer3 to bed FAILED! For chrom:", refseq, "file:", filename, e
        glimmer3_bed = []
    glimmer3_bed_file = open( os.path.join( os.path.split( filename )[0], "%s.Glimmer3.bed" % refseq ), 'wb+' )
    glimmer3_bed_file.write( '\n'.join( glimmer3_bed ) )
    glimmer3_bed_file.close()


def process_GeneMarkHMM( filename, org_num, refseq ):
    try:
        geneMarkHMM_bed = get_bed_from_GeneMarkHMM( filename, refseq )
    except Exception as e:
        print "Converting GeneMarkHMM to bed FAILED! For chrom:", refseq, "file:", filename, e
        geneMarkHMM_bed = []
    geneMarkHMM_bed_bed_file = open( os.path.join( os.path.split( filename )[0], "%s.GeneMarkHMM.bed" % refseq ), 'wb+' )
    geneMarkHMM_bed_bed_file.write( '\n'.join( geneMarkHMM_bed ) )
    geneMarkHMM_bed_bed_file.close()


def process_GeneMark( filename, org_num, refseq ):
    try:
        geneMark_bed = get_bed_from_GeneMark( filename, refseq )
    except Exception as e:
        print "Converting GeneMark to bed FAILED! For chrom:", refseq, "file:", filename, e
        geneMark_bed = []
    geneMark_bed_bed_file = open( os.path.join( os.path.split( filename )[0], "%s.GeneMark.bed" % refseq ), 'wb+' )
    geneMark_bed_bed_file.write( '\n'.join( geneMark_bed ) )
    geneMark_bed_bed_file.close()


def __main__():
    start_time = time.time()
    base_dir = os.path.join( os.getcwd(), "bacteria" )
    try:
        base_dir = sys.argv[1]
    except:
        print "using default base_dir:", base_dir

    try:
        os.mkdir( base_dir )
        print "path '%s' has been created" % base_dir
    except:
        print "path '%s' seems to already exist" % base_dir

    for org_num, name, chroms, kingdom, group, org_genbank, org_refseq, info_url, ftp_url in iter_genome_projects():
        if chroms is None:
            continue  # No chrom information, we can't really do anything with this organism
        # Create org directory, if exists, assume it is done and complete --> skip it
        try:
            org_dir = os.path.join( base_dir, org_num )
            os.mkdir( org_dir )
        except:
            print "Organism %s already exists on disk, skipping" % org_num
            continue

        # get ftp contents
        ftp_contents = get_ftp_contents( ftp_url )
        if ftp_contents is None:
            "FTP COMPLETELY FAILED TO LOAD", "org:", org_num, "ftp:", ftp_url
        else:
            for refseq in chroms:
                scrape_ftp( ftp_contents, org_dir, org_num, refseq, ftp_url )
                # FTP Files have been Loaded
                print "Org:", org_num, "chrom:", refseq, "[", time.time() - start_time, "seconds elapsed. ]"

        # Create org info file
        info_file = open( os.path.join( org_dir, "%s.info" % org_num ), 'wb+' )
        info_file.write("genome project id=%s\n" % org_num )
        info_file.write("name=%s\n" % name )
        info_file.write("kingdom=%s\n" % kingdom )
        info_file.write("group=%s\n" % group )
        info_file.write("chromosomes=%s\n" % ",".join( chroms ) )
        info_file.write("info url=%s\n" % info_url )
        info_file.write("ftp url=%s\n" % ftp_url )
        info_file.close()

    print "Finished Harvesting", "[", time.time() - start_time, "seconds elapsed. ]"
    print "[", ( time.time() - start_time ) / 60, "minutes. ]"
    print "[", ( time.time() - start_time ) / 60 / 60, "hours. ]"


if __name__ == "__main__":
    __main__()
