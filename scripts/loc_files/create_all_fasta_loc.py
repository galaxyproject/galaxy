"""
Generates a loc file containing names of all the fasta files that match the
name of the genome subdirectory they're in.
Assumptions:
    - fasta files should be named the same as the genome subdirectory they're
      in, with the possible addition of a recognized variant (canon, full, etc.)
    - for "variants" (like full, canon[ical], chrM, etc.) the naming needs to be
      consistent and specific:
        - <genome_name><variant>, like hg19canon, hg19full, or hg19chrM
Normal usage:
create_all_fasta_loc.py -f unmatching_fasta.txt -i seq

usage: %prog [options]
   -d, --data-table-xml=d: The name of the data table configuration file to get format of loc file
   -t, --data-table=t: The name of the data table listed in the data table XML file
   -g, --genome-dir=g: Genome directory to look in
   -e, --exemptions=e: Comma-separated list of genome dir subdirectories to not look in
   -i, --inspect-dirs=i: Comma-separated list of subdirectories inside genome dirs to look in (default is all)
   -x, --fasta-exts=x: Comma-separated list of all fasta extensions to list
   -s, --loc-sample=s: The name of the sample loc file (to copy text into top of output loc file)
   -f, --unmatching-fasta=f: Name of file to output non-matching fasta files to, if included
   -v, --variants=v: Comma-separated list of recognized variants of fasta file names
   -a, --append=a: Append to existing all_fasta.loc file rather than create new
   -p, --sample-text=p: Copy over text from all_fasta.loc.sample file (false if set to append)
"""
import optparse
import os
import sys
from xml.etree.ElementTree import parse

DEFAULT_TOOL_DATA_TABLE_CONF = 'tool_data_table_conf.xml'
DEFAULT_ALL_FASTA_LOC_BASE = 'all_fasta'
DEFAULT_BASE_GENOME_DIR = '/afs/bx.psu.edu/depot/data/genome'
EXEMPTIONS = 'bin,tmp,lengths,equCab2_chrM,microbes'
INSPECT_DIR = None
FASTA_EXTS = '.fa,.fasta,.fna'
VARIANTS = 'chrM,chr21,full,canon,female,male,haps,nohaps'

VARIANT_EXCLUSIONS = ':full'

DBKEY_DESCRIPTION_MAP = { 'AaegL1': 'Mosquito (Aedes aegypti): AaegL1',
                          'AgamP3': 'Mosquito (Anopheles gambiae): AgamP3',
                          'anoCar1': 'Lizard (Anolis carolinensis): anoCar1',
                          'anoGam1': 'Mosquito (Anopheles gambiae): anoGam1',
                          'apiMel1': 'Honeybee (Apis mellifera): apiMel1',
                          'apiMel2': 'Honeybee (Apis mellifera): apiMel2',
                          'apiMel3': 'Honeybee (Apis mellifera): apiMel3',
                          'Arabidopsis_thaliana_TAIR9': '',
                          'borEut13': 'Boreoeutherian: borEut13',
                          'bosTau2': 'Cow (Bos taurus): bosTau2',
                          'bosTau3': 'Cow (Bos taurus): bosTau3',
                          'bosTau4': 'Cow (Bos taurus): bosTau4',
                          'bosTauMd3': 'Cow (Bos taurus): bosTauMd3',
                          'calJac1': 'Marmoset (Callithrix jacchus): calJac1',
                          'canFam1': 'Dog (Canis lupus familiaris): canFam1',
                          'canFam2': 'Dog (Canis lupus familiaris): canFam2',
                          'cavPor3': 'Guinea Pig (Cavia porcellus): cavPor3',
                          'ce2': 'Caenorhabditis elegans: ce2',
                          'ce4': 'Caenorhabditis elegans: ce4',
                          'ce5': 'Caenorhabditis elegans: ce5',
                          'ce6': 'Caenorhabditis elegans: ce6',
                          'CpipJ1': 'Mosquito (Culex quinquefasciatus): CpipJ1',
                          'danRer2': 'Zebrafish (Danio rerio): danRer2',
                          'danRer3': 'Zebrafish (Danio rerio): danRer3',
                          'danRer4': 'Zebrafish (Danio rerio): danRer4',
                          'danRer5': 'Zebrafish (Danio rerio): danRer5',
                          'danRer6': 'Zebrafish (Danio rerio): danRer6',
                          'dm1': 'Fruit Fly (Drosophila melanogaster): dm1',
                          'dm2': 'Fruit Fly (Drosophila melanogaster): dm2',
                          'dm3': 'Fruit Fly (Drosophila melanogaster): dm3',
                          'dm4': 'Fruit Fly (Drosophila melanogaster): dm',
                          'dp3': 'Fruit Fly (Drosophila pseudoobscura): dp3',
                          'dp4': 'Fruit Fly (Drosophila pseudoobscura): dp4',
                          'droAna1': 'Fruit Fly (Drosophila ananassae): droAna1',
                          'droAna2': 'Fruit Fly (Drosophila ananassae): droAna2',
                          'droAna3': 'Fruit Fly (Drosophila ananassae): droAna3',
                          'droEre1': 'Fruit Fly (Drosophila erecta): droEre1',
                          'droEre2': 'Fruit Fly (Drosophila erecta): droEre2',
                          'droGri1': 'Fruit Fly (Drosophila grimshawi): droGri1',
                          'droGri2': 'Fruit Fly (Drosophila grimshawi): droGri2',
                          'droMoj1': 'Fruit Fly (Drosophila mojavensis): droMoj1',
                          'droMoj2': 'Fruit Fly (Drosophila mojavensis): droMoj2',
                          'droMoj3': 'Fruit Fly (Drosophila mojavensis): droMoj3',
                          'droPer1': 'Fruit Fly (Drosophila persimilis): droPer1',
                          'droSec1': 'Fruit Fly (Drosophila sechellia): droSec1',
                          'droSim1': 'Fruit Fly (Drosophila simulans): droSim1',
                          'droVir1': 'Fruit Fly (Drosophila virilis): droVir1',
                          'droVir2': 'Fruit Fly (Drosophila virilis): droVir2',
                          'droVir3': 'Fruit Fly (Drosophila virilis): droVir3',
                          'droYak1': 'Fruit Fly (Drosophila yakuba): droYak1',
                          'droYak2': 'Fruit Fly (Drosophila yakuba): droYak2',
                          'echTel1': 'Tenrec (Echinops telfairi): echTel1',
                          'equCab1': 'Horse (Equus caballus): equCab1',
                          'equCab2': 'Horse (Equus caballus): equCab2',
                          'eriEur1': 'Hedgehog (Erinaceus europaeus): eriEur1',
                          'felCat3': 'Cat (Felis catus): felCat3',
                          'fr1': 'Fugu (Takifugu rubripes): fr1',
                          'fr2': 'Fugu (Takifugu rubripes): fr2',
                          'galGal2': 'Chicken (Gallus gallus): galGal2',
                          'galGal3': 'Chicken (Gallus gallus): galGal3',
                          'gasAcu1': 'Stickleback (Gasterosteus aculeatus): gasAcu1',
                          'hg16': 'Human (Homo sapiens): hg16',
                          'hg17': 'Human (Homo sapiens): hg17',
                          'hg18': 'Human (Homo sapiens): hg18',
                          'hg19': 'Human (Homo sapiens): hg19',
                          'IscaW1': 'Deer Tick (Ixodes scapularis): IscaW1',
                          'lMaj5': 'Leishmania major: lMaj5',
                          'mm5': 'Mouse (Mus musculus): mm5',
                          'mm6': 'Mouse (Mus musculus): mm6',
                          'mm7': 'Mouse (Mus musculus): mm7',
                          'mm8': 'Mouse (Mus musculus): mm8',
                          'mm9': 'Mouse (Mus musculus): mm9',
                          'monDom4': 'Opossum (Monodelphis domestica): monDom4',
                          'monDom5': 'Opossum (Monodelphis domestica): monDom5',
                          'ornAna1': 'Platypus (Ornithorhynchus anatinus): ornAna1',
                          'oryCun1': 'Rabbit (Oryctolagus cuniculus): oryCun1',
                          'oryLat1': 'Medaka (Oryzias latipes): oryLat1',
                          'oryLat2': 'Medaka (Oryzias latipes): oryLat2',
                          'oryza_sativa_japonica_nipponbare_IRGSP4.0': 'Rice (Oryza sativa L. ssp. japonica var. Nipponbare): IRGSP4.0',
                          'otoGar1': 'Bushbaby (Otolemur garnetti): otoGar1',
                          'panTro1': 'Chimpanzee (Pan troglodytes): panTro1',
                          'panTro2': 'Chimpanzee (Pan troglodytes): panTro2',
                          'petMar1': 'Lamprey (Petromyzon marinus): petMar1',
                          'phiX': 'phiX174 (AF176034)',
                          'PhumU1': 'Head Louse (Pediculus humanus): PhumU1',
                          'ponAbe2': 'Orangutan (Pongo pygmaeus abelii): ponAbe2',
                          'pUC18': 'pUC18 (L09136)',
                          'rheMac2': 'Rhesus Macaque (Macaca mulatta): rheMac2',
                          'rn3': 'Rat (Rattus norvegicus): rn3',
                          'rn4': 'Rat (Rattus norvegicus): rn4',
                          'sacCer1': 'Yeast (Saccharomyces cerevisiae): sacCer1',
                          'sacCer2': 'Yeast (Saccharomyces cerevisiae): sacCer2',
                          'sorAra1': 'Common Shrew (Sorex araneus): sorAra1',
                          'Sscrofa9.58': 'Pig (Sus scrofa): Sscrofa9.58',
                          'strPur2': 'Purple Sea Urchin (Strongylocentrotus purpuratus): strPur2',
                          'susScr2': 'Pig (Sus scrofa): susScr2',
                          'taeGut1': 'Zebra Finch (Taeniopygia guttata): taeGut1',
                          'tetNig1': 'Tetraodon (Tetraodon nigroviridis): tetNig1',
                          'tetNig2': 'Tetraodon (Tetraodon nigroviridis): tetNig2',
                          'tupBel1': 'Tree Shrew (Tupaia belangeri): tupBel1',
                          'venter1': 'Human (J. Craig Venter): venter1',
                          'xenTro2': 'Frog (Xenopus tropicalis): xenTro2' }

VARIANT_MAP = { 'canon': 'Canonical',
               'full': 'Full',
               'female': 'Female',
               'male': 'Male' }


# alphabetize ignoring case
def caseless_compare( a, b ):
    au = a.upper()
    bu = b.upper()
    if au > bu:
        return 1
    elif au == bu:
        return 0
    elif au < bu:
        return -1


def __main__():
    # command line variables
    parser = optparse.OptionParser()
    parser.add_option( '-d', '--data-table-xml', dest='data_table_xml', type='string', default=DEFAULT_TOOL_DATA_TABLE_CONF, help='The name of the data table configuration file to get format of loc file' )
    parser.add_option( '-t', '--data-table', dest='data_table_name', type='string', default=DEFAULT_ALL_FASTA_LOC_BASE, help='The name of the data table listed in the data table XML file' )
    parser.add_option( '-g', '--genome_dir', dest='genome_dir', type='string', default=DEFAULT_BASE_GENOME_DIR, help='Genome directory to look in' )
    parser.add_option( '-e', '--exemptions', dest='exemptions', type='string', default=EXEMPTIONS, help='Comma-separated list of subdirectories in genome dir to not look in' )
    parser.add_option( '-i', '--inspect-dir', dest='inspect_dir', type='string', default=INSPECT_DIR, help='Comma-separated list of subdirectories inside genome dirs to look in (default is all)' )
    parser.add_option( '-x', '--fasta_exts', dest='fasta_exts', type='string', default=FASTA_EXTS, help='Comma-separated list of all fasta extensions to list' )
    parser.add_option( '-s', '--loc-sample', dest='loc_sample_name', type='string', help='The name of the sample loc file (to copy text into top of output loc file)' )
    parser.add_option( '-f', '--unmatching-fasta', dest='unmatching_fasta', type='string', default=None, help='Name of file to output non-matching fasta files to' )
    parser.add_option( '-v', '--variants', dest='variants', type='string', default=VARIANTS, help='Comma-separated list of recognized variants of fasta file names' )
    parser.add_option( '-n', '--variant-exclusions', dest='variant_exclusions', type='string', default=VARIANT_EXCLUSIONS, help="List of files to exclude because they're duplicated by a variants; of the format: '<variant_to_keep_1>:<variant_to_remove_1>[,<variant_to_remove_2>[,...]][;<variant_to_keep_2>:<variant_to_remove_1>[,<variant_to_remove_2>[,...]]]'; default ':(full)' (if non-variant version present (like 'hg19'), full version (like 'hg19full') will be thrown out)" )
    parser.add_option( '-a', '--append', dest='append', action='store_true', default=False, help='Append to existing all_fasta.loc file rather than create new' )
    parser.add_option( '-p', '--sample-text', dest='sample_text', action='store_true', default='True', help='Copy over text from all_fasta.loc.sample file (false if set to append)' )
    (options, args) = parser.parse_args()

    exemptions = [ e.strip() for e in options.exemptions.split( ',' ) ]
    fasta_exts = [ x.strip() for x in options.fasta_exts.split( ',' ) ]
    variants = [ v.strip() for v in options.variants.split( ',' ) ]
    variant_exclusions = {}
    try:
        for ve in options.variant_exclusions.split( ';' ):
            v, e = ve.split( ':' )
            variant_exclusions[ v ] = e.split( ',' )
    except:
        sys.stderr.write( 'Problem parsing the variant exclusion parameter (-n/--variant-exclusion). Make sure it follows the expected format\n' )
        sys.exit( 1 )
    if options.append:
        sample_text = False
    else:
        sample_text = options.sample_text

    # all paths to look in
    if options.inspect_dir:
        paths_to_look_in = [ os.path.join( options.genome_dir, '%s', id ) for id in options.inspect_dir.split( ',' ) ]
    else:
        paths_to_look_in = [os.path.join( options.genome_dir, '%s' )]

    # say what we're looking in
    print '\nLooking in:\n\t%s' % '\n\t'.join( [ p % '<build_name>' for p in paths_to_look_in ] )
    poss_names = [ '<build_name>%s' % _ for _ in variants ]
    print 'for files that are named %s' % ', '.join( poss_names[:-1] ),
    if len( poss_names ) > 1:
        print 'or %s' % poss_names[-1],
    if len( options.fasta_exts ) == 1:
        print 'with the extension %s.' % ', '.join( fasta_exts[:-1] )
    else:
        print 'with the extension %s or %s.' % ( ', '.join( fasta_exts[:-1] ), fasta_exts[-1] )
    print '\nSkipping the following:\n\t%s' % '\n\t'.join( exemptions )

    # get column names
    col_values = []
    loc_path = None
    tree = parse( options.data_table_xml )
    tables = tree.getroot()
    for table in tables.getiterator():
        name = table.attrib.get( 'name' )
        if name == options.data_table_name:
            cols = None
            for node in table.getiterator():
                if node.tag == 'columns':
                    cols = node.text
                elif node.tag == 'file':
                    loc_path = node.attrib.get( 'path' )
            if cols:
                col_values = [ col.strip() for col in cols.split( ',' ) ]
    if not col_values or not loc_path:
        raise Exception( 'No columns can be found for this data table (%s) in %s' % ( options.data_table, options.data_table_xml ) )

    # get all fasta paths under genome directory
    fasta_locs = {}
    unmatching_fasta_paths = []
    genome_subdirs = [ dr for dr in os.listdir( options.genome_dir ) if dr not in exemptions ]
    for genome_subdir in genome_subdirs:
        possible_names = [ genome_subdir ]
        possible_names.extend( [ '%s%s' % ( genome_subdir, _ ) for _ in variants ] )
        # get paths to all fasta files
        for path_to_look_in in paths_to_look_in:
            for dirpath, dirnames, filenames in os.walk( path_to_look_in % genome_subdir ):
                for fn in filenames:
                    ext = os.path.splitext( fn )[-1]
                    fasta_base = os.path.splitext( fn )[0]
                    if ext in fasta_exts:
                        if fasta_base in possible_names:
                            if fasta_base == genome_subdir:
                                name = DBKEY_DESCRIPTION_MAP[ genome_subdir ]
                            else:
                                try:
                                    name = '%s %s' % ( DBKEY_DESCRIPTION_MAP[ genome_subdir ], VARIANT_MAP[ fasta_base.replace( genome_subdir, '' ) ] )
                                except KeyError:
                                    name = '%s %s' % ( DBKEY_DESCRIPTION_MAP[ genome_subdir ], fasta_base.replace( genome_subdir, '' ) )
                            fasta_locs[ fasta_base ] = { 'value': fasta_base, 'dbkey': genome_subdir, 'name': name, 'path': os.path.join( dirpath, fn ) }
                        else:
                            unmatching_fasta_paths.append( os.path.join( dirpath, fn ) )
        # remove redundant fasta files
        if variant_exclusions.keys():
            for k in variant_exclusions.keys():
                leave_in = '%s%s' % ( genome_subdir, k )
                if leave_in in fasta_locs:
                    to_remove = [ '%s%s' % ( genome_subdir, k ) for k in variant_exclusions[ k ] ]
                    for tr in to_remove:
                        if tr in fasta_locs:
                            del fasta_locs[ tr ]

    # output results
    print '\nThere were %s fasta files found that were not included because they did not have the expected file names.' % len( unmatching_fasta_paths )
    print '%s fasta files were found and listed.\n' % len( fasta_locs.keys() )

    # output unmatching fasta files
    if options.unmatching_fasta and unmatching_fasta_paths:
        open( options.unmatching_fasta, 'wb' ).write( '%s\n' % '\n'.join( unmatching_fasta_paths ) )

    # output loc file
    if options.append:
        all_fasta_loc = open( loc_path, 'ab' )
    else:
        all_fasta_loc = open( loc_path, 'wb' )
    # put sample loc file text at top of file if appropriate
    if sample_text:
        if options.loc_sample_name:
            all_fasta_loc.write( '%s\n' % open( options.loc_sample_name, 'rb' ).read().strip() )
        else:
            all_fasta_loc.write( '%s\n' % open( '%s.sample' % loc_path, 'rb' ).read().strip() )
    # output list of fasta files in alphabetical order
    fasta_bases = fasta_locs.keys()
    fasta_bases.sort( caseless_compare )
    for fb in fasta_bases:
        out_line = []
        for col in col_values:
            try:
                out_line.append( fasta_locs[ fb ][ col ] )
            except KeyError:
                raise Exception( 'Unexpected column (%s) encountered' % col )
        if out_line:
            all_fasta_loc.write( '%s\n' % '\t'.join( out_line ) )
    # close up output loc file
    all_fasta_loc.close()


if __name__ == '__main__':
    __main__()
