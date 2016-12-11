# Dan Blankenberg
from __future__ import print_function

import sys
from optparse import OptionParser

import bx.align.maf
import galaxy_utils.sequence.vcf
from six import Iterator

UNKNOWN_NUCLEOTIDE = '*'


class PopulationVCFParser( Iterator ):
    def __init__( self, reader, name ):
        self.reader = reader
        self.name = name
        self.counter = 0

    def __next__( self ):
        rval = []
        vc = next(self.reader)
        for i, allele in enumerate( vc.alt ):
            rval.append( ( '%s_%i.%i' % ( self.name, i + 1, self.counter + 1 ), allele ) )
        self.counter += 1
        return ( vc, rval )

    def __iter__( self ):
        while True:
            yield next(self)


class SampleVCFParser( Iterator ):
    def __init__( self, reader ):
        self.reader = reader
        self.counter = 0

    def __next__( self ):
        rval = []
        vc = next(self.reader)
        alleles = [ vc.ref ] + vc.alt

        if 'GT' in vc.format:
            gt_index = vc.format.index( 'GT' )
            for sample_name, sample_value in zip( vc.sample_names, vc.sample_values ):
                gt_indexes = []
                for i in sample_value[ gt_index ].replace( '|', '/' ).replace( '\\', '/' ).split( '/' ):  # Do we need to consider phase here?
                    try:
                        gt_indexes.append( int( i ) )
                    except:
                        gt_indexes.append( None )
                for i, allele_i in enumerate( gt_indexes ):
                    if allele_i is not None:
                        rval.append( ( '%s_%i.%i' % ( sample_name, i + 1, self.counter + 1 ), alleles[ allele_i ] ) )
        self.counter += 1
        return ( vc, rval )

    def __iter__( self ):
        while True:
            yield next(self)


def main():
    usage = "usage: %prog [options] output_file dbkey inputfile pop_name"
    parser = OptionParser( usage=usage )
    parser.add_option( "-p", "--population", action="store_true", dest="population", default=False, help="Create MAF on a per population basis")
    parser.add_option( "-s", "--sample", action="store_true", dest="sample", default=False, help="Create MAF on a per sample basis")
    parser.add_option( "-n", "--name", dest="name", default='Unknown Custom Track', help="Name for Custom Track")
    parser.add_option( "-g", "--galaxy", action="store_true", dest="galaxy", default=False, help="Tool is being executed by Galaxy (adds extra error messaging).")
    ( options, args ) = parser.parse_args()

    if len( args ) < 3:
        if options.galaxy:
            print("It appears that you forgot to specify an input VCF file, click 'Add new VCF...' to add at least input.\n", file=sys.stderr)
        parser.error( "Need to specify an output file, a dbkey and at least one input file" )

    if not ( options.population ^ options.sample ):
        parser.error( 'You must specify either a per population conversion or a per sample conversion, but not both' )

    out = open( args.pop(0), 'wb' )
    out.write( 'track name="%s" visibility=pack\n' % options.name.replace( "\"", "'" ) )

    maf_writer = bx.align.maf.Writer( out )

    dbkey = args.pop(0)

    vcf_files = []
    if options.population:
        i = 0
        while args:
            filename = args.pop( 0 )
            pop_name = args.pop( 0 ).replace( ' ', '_' )
            if not pop_name:
                pop_name = 'population_%i' % ( i + 1 )
            vcf_files.append( PopulationVCFParser( galaxy_utils.sequence.vcf.Reader( open( filename ) ), pop_name  ) )
            i += 1
    else:
        while args:
            filename = args.pop( 0 )
            vcf_files.append( SampleVCFParser( galaxy_utils.sequence.vcf.Reader( open( filename ) ) ) )

    non_spec_skipped = 0
    for vcf_file in vcf_files:
        for vc, variants in vcf_file:
            num_ins = 0
            num_dels = 0
            for variant_name, variant_text in variants:
                if 'D' in variant_text:
                    num_dels = max( num_dels, int( variant_text[1:] ) )
                elif 'I' in variant_text:
                    num_ins = max( num_ins, len( variant_text ) - 1 )

            alignment = bx.align.maf.Alignment()
            ref_text = vc.ref + '-' * num_ins + UNKNOWN_NUCLEOTIDE * ( num_dels - len( vc.ref ) )
            start_pos = vc.pos - 1
            if num_dels and start_pos:
                ref_text = UNKNOWN_NUCLEOTIDE + ref_text
                start_pos -= 1
            alignment.add_component( bx.align.maf.Component(
                src='%s.%s%s' % ( dbkey, ("chr" if not vc.chrom.startswith("chr") else ""), vc.chrom ),
                start=start_pos, size=len( ref_text.replace( '-', '' ) ),
                strand='+', src_size=start_pos + len( ref_text ),
                text=ref_text ) )
            for variant_name, variant_text in variants:
                # FIXME:
                # skip non-spec. compliant data, see: http://1000genomes.org/wiki/doku.php?id=1000_genomes:analysis:vcf3.3 for format spec
                # this check is due to data having indels not represented in the published format spec,
                # e.g. 1000 genomes pilot 1 indel data: ftp://ftp-trace.ncbi.nih.gov/1000genomes/ftp/pilot_data/release/2010_03/pilot1/indels/CEU.SRP000031.2010_03.indels.sites.vcf.gz
                if variant_text and variant_text[0] in [ '-', '+' ]:
                    non_spec_skipped += 1
                    continue

                # do we need a left padding unknown nucleotide (do we have deletions)?
                if num_dels and start_pos:
                    var_text = UNKNOWN_NUCLEOTIDE
                else:
                    var_text = ''
                if 'D' in variant_text:
                    cur_num_del = int( variant_text[1:] )
                    pre_del = min( len( vc.ref ), cur_num_del )
                    post_del = cur_num_del - pre_del
                    var_text = var_text + '-' * pre_del + '-' * num_ins + '-' * post_del
                    var_text = var_text + UNKNOWN_NUCLEOTIDE * ( len( ref_text ) - len( var_text ) )
                elif 'I' in variant_text:
                    cur_num_ins = len( variant_text ) - 1
                    var_text = var_text + vc.ref + variant_text[1:] + '-' * ( num_ins - cur_num_ins ) + UNKNOWN_NUCLEOTIDE * max( 0, ( num_dels - 1 ) )
                else:
                    var_text = var_text + variant_text + '-' * num_ins + UNKNOWN_NUCLEOTIDE * ( num_dels - len( vc.ref ) )
                alignment.add_component( bx.align.maf.Component(
                    src=variant_name, start=0,
                    size=len( var_text.replace( '-', '' ) ), strand='+',
                    src_size=len( var_text.replace( '-', '' ) ),
                    text=var_text ) )
            maf_writer.write( alignment )

    maf_writer.close()

    if non_spec_skipped:
        print('Skipped %i non-specification compliant indels.' % non_spec_skipped)


if __name__ == "__main__":
    main()
