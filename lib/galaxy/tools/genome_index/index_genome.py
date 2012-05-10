#!/usr/bin/env python
"""
Export a history to an archive file using attribute files.

usage: %prog history_attrs dataset_attrs job_attrs out_file
    -G, --gzip: gzip archive file
"""
import optparse, sys, os, tempfile, time, subprocess, shlex, json, tarfile, shutil

class ManagedIndexer():
    def __init__( self, output_file, infile, workingdir ):
        self.workingdir = os.path.abspath( workingdir )
        self.outfile = open( os.path.abspath( output_file ), 'w' )
        self.basedir = os.path.split( self.workingdir )[0]
        self.fasta = os.path.abspath( infile )
        self.locations = dict( nt=[], cs=[] )
        self.log = []
        self.indexers = {
            'bwa': '_bwa',
            'bowtie': '_bowtie',
            'bowtie2': '_bowtie2',
            '2bit': '_twobit',
            'perm': '_perm',
            'bfast': '_bfast',
            'picard': '_picard',
            'sam': '_sam'
        }
        if not os.path.exists( self.workingdir ):
            os.makedirs( self.workingdir )
        self.logfile = open( os.path.join( self.workingdir, 'ManagedIndexer.log' ), 'w+' )
        
    def run_indexer( self, indexer ):
        self.fapath = self.fasta
        self.fafile = os.path.basename( self.fapath )
        with WithChDir( self.basedir ):
            if indexer not in self.indexers:
                raise KeyError, 'The requested indexing function does not exist'
            else:
                with WithChDir( self.workingdir ):
                    self._log( 'Running indexer %s.' % indexer )
                    result = getattr( self, self.indexers[ indexer ] )()
                if result is None:
                    self._log( 'Error running indexer %s.' % indexer )
                    self._flush_files()
                    raise Exception
                else:
                    self._log( 'Indexer %s completed successfully.' % indexer )
                    self._flush_files()
                
    def _flush_files( self ):
        json.dump( self.locations, self.outfile )
        self.outfile.close()
        self.logfile.close()
    
    def _log( self, stuff ):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S %z')
        self.logfile.write( "[%s] %s\n" % (timestamp, stuff) )
        
    def _bwa( self ):
        with WithChDir( self.workingdir ):
            if not os.path.exists( self.fafile ):
                os.symlink( os.path.relpath( self.fapath ), self.fafile )
            command = shlex.split( 'bwa index -a bwtsw %s' % self.fafile )
            result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
            if result != 0:
                newcommand = shlex.split( 'bwa index -c %s' % self.fafile )
                result = call( newcommand, stderr=self.logfile, stdout=self.logfile )
            if result == 0:
                self.locations[ 'nt' ].append( self.fafile )
                os.remove( self.fafile )
                os.makedirs( 'cs' )
                with WithChDir( 'cs' ):
                    if not os.path.exists( self.fafile ):
                        os.symlink( os.path.relpath( self.fapath ), self.fafile )
                    command = shlex.split( 'bwa index -a bwtsw -c %s' % self.fafile )
                    result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
                    if result != 0:
                        newcommand = shlex.split( 'bwa index -c %s' % self.fafile )
                        result = call( newcommand, stderr=self.logfile, stdout=self.logfile )
                        if result == 0:
                            self.locations[ 'cs' ].append( self.fafile )
                            os.remove( self.fafile )
                        else:
                            return False
                    else:
                        self.locations[ 'cs' ].append( self.fafile )
                        os.remove( self.fafile )
                temptar = tarfile.open( 'cs.tar', 'w' )
                temptar.add( 'cs' )
                temptar.close()
                shutil.rmtree( 'cs' )
                return True
            else:
                return False
    
    def _bowtie( self ):
        ref_base = os.path.splitext(self.fafile)[0]
        if not os.path.exists( self.fafile ):
            os.symlink( os.path.relpath( self.fapath ), self.fafile )
        command = shlex.split( 'bowtie-build -f %s %s' % ( self.fafile, ref_base ) )
        result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
        if result == 0:
            self.locations[ 'nt' ].append( ref_base )
            os.remove( self.fafile )
            indexdir = os.path.join( os.getcwd(), 'cs' )
            os.makedirs( indexdir )
            with WithChDir( indexdir ):
                ref_base = os.path.splitext(self.fafile)[0]
                if not os.path.exists( self.fafile ):
                    os.symlink( os.path.relpath( self.fapath ), self.fafile )
                command = shlex.split( 'bowtie-build -C -f %s %s' % ( self.fafile, ref_base ) )
                result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
                if result == 0:
                    self.locations[ 'cs' ].append( ref_base )
                else:
                    return False
            os.remove( os.path.join( indexdir, self.fafile ) )
            temptar = tarfile.open( 'cs.tar', 'w' )
            temptar.add( 'cs' )
            temptar.close()
            shutil.rmtree( 'cs' )
            return True
        else:
            return False
    
    def _bowtie2( self ):
        ref_base = os.path.splitext(self.fafile)[0]
        if not os.path.exists( self.fafile ):
            os.symlink( os.path.relpath( self.fapath ), self.fafile )
        command = shlex.split( 'bowtie2-build %s %s' % ( self.fafile, ref_base ) )
        result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
        if result == 0:
            self.locations[ 'nt' ].append( ref_base )
            os.remove( self.fafile )
            return True
        else:
            return False
    
    def _twobit( self ):
        """Index reference files using 2bit for random access.
        """
        ref_base = os.path.splitext(self.fafile)[0]
        out_file = "%s.2bit" % ref_base
        if not os.path.exists( self.fafile ):
            os.symlink( os.path.relpath( self.fapath ), self.fafile )
        command = shlex.split( 'faToTwoBit %s %s' % ( self.fafile, out_file ) )
        result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
        if result == 0:
            self.locations['nt'].append( out_file )
            os.remove( self.fafile )
            return True
        else:
            return False
    
    def _perm( self ):
        local_ref = self.fafile
        if not os.path.exists( local_ref ):
            os.symlink( os.path.relpath( self.fapath ), self.fafile )
        genome = os.path.splitext( local_ref )[0]
        read_length = 50
        for seed in [ 'F3', 'F4' ]:
            key = '%s_%s_%s' % (genome, seed, read_length)
            desc = '%s: seed=%s, read length=%s' % (genome, seed, read_length)
            index = "%s_base_%s_%s.index" % (genome, seed, read_length)
            command = shlex.split("PerM %s %s --readFormat fastq --seed %s -m -s %s" % (local_ref, read_length, seed, index))
            result = subprocess.call( command )
            if result == 0:
                self.locations[ 'nt' ].append( [ key, desc, index ] )
            else:
                return False
        os.remove( local_ref )
        os.makedirs( 'cs' )
        with WithChDir( 'cs' ):
            if not os.path.exists( local_ref ):
                os.symlink( os.path.relpath( self.fapath ), self.fafile )
            for seed in [ 'F3', 'F4' ]:
                key = '%s_%s_%s' % (genome, seed, read_length)
                desc = '%s: seed=%s, read length=%s' % (genome, seed, read_length)
                index = "%s_color_%s_%s.index" % (genome, seed, read_length)
                command = shlex.split("PerM %s %s --readFormat csfastq --seed %s -m -s %s" % (local_ref, read_length, seed, index))
                result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
                if result == 0:
                    self.locations[ 'cs' ].append( [ key, desc, index ] )
                else:
                    return False
            os.remove( local_ref )
        temptar = tarfile.open( 'cs.tar', 'w' )
        temptar.add( 'cs' )
        temptar.close()
        shutil.rmtree( 'cs' )
        return True
    
    def _bfast( self ):
        """Indexes bfast in color and nucleotide space for longer reads.
    
        This preps for 40+bp sized reads, which is bfast's strength.
        """
        dir_name_nt = 'nt'
        dir_name_cs = 'cs'
        window_size = 14
        bfast_nt_masks = [
            "1111111111111111111111",
            "1111101110111010100101011011111",
            "1011110101101001011000011010001111111",
            "10111001101001100100111101010001011111",
            "11111011011101111011111111",
            "111111100101001000101111101110111",
            "11110101110010100010101101010111111",
            "111101101011011001100000101101001011101",
            "1111011010001000110101100101100110100111",
            "1111010010110110101110010110111011",
        ]
        bfast_color_masks = [
            "1111111111111111111111",
            "111110100111110011111111111",
            "10111111011001100011111000111111",
            "1111111100101111000001100011111011",
            "111111110001111110011111111",
            "11111011010011000011000110011111111",
            "1111111111110011101111111",
            "111011000011111111001111011111",
            "1110110001011010011100101111101111",
            "111111001000110001011100110001100011111",
        ]
        local_ref = self.fafile
        os.makedirs( dir_name_nt )
        os.makedirs( dir_name_cs )
        if not os.path.exists( self.fafile ):
            os.symlink( os.path.relpath( self.fapath ), self.fafile )
        with WithChDir( dir_name_nt ):
            if not os.path.exists( self.fafile ):
                os.symlink( os.path.relpath( self.fapath ), self.fafile )
            # nucleotide space
            command = shlex.split( "bfast fasta2brg -f %s -A 0" % local_ref )
            result = subprocess.call( command, stderr=self.logfile  )
            for i, mask in enumerate( bfast_nt_masks ):
                command = shlex.split("bfast index -d 1 -n 4 -f %s -A 0 -m %s -w %s -i %s" %
                             ( local_ref, mask, window_size, i + 1 ) )
                result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
            os.remove( self.fafile )
            if result != 0:
                return False
            else:
                os.remove( self.fafile )
        with WithChDir( dir_name_cs ):
            if not os.path.exists( self.fafile ):
                os.symlink( os.path.relpath( self.fapath ), self.fafile )
            # colorspace
            command = shlex.split( "bfast fasta2brg -f %s -A 1" % local_ref )
            result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
            for i, mask in enumerate( bfast_color_masks ):
                command = shlex.split( "bfast index -d 1 -n 4 -f %s -A 1 -m %s -w %s -i %s" %
                             ( local_ref, mask, window_size, i + 1 ) )
                result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
            if result != 0:
                return False
            else:
                os.remove( self.fafile )
                self.locations = None
                return True
    
    def _picard( self ):
        local_ref = self.fafile
        srma = '/Users/dave/srma.jar'
        genome = os.path.splitext( self.fafile )[0]
        if not os.path.exists( self.fafile ):
            os.symlink( os.path.relpath( self.fapath ), self.fafile )
        command = shlex.split( 'samtools faidx %s' % self.fafile )
        subprocess.call( command, stderr=self.logfile  )
        os.rename( '%s.fai' % self.fafile, '%s.fai' % genome )
        command = shlex.split( "java -cp %s net.sf.picard.sam.CreateSequenceDictionary R=%s O=%s/%s.dict URI=%s" \
                     % ( srma, local_ref, os.curdir, genome, local_ref ) )
        result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
        if result != 0:
            return False
        else:
            self.locations[ 'nt' ].append( self.fafile )
            #os.remove( '%s.fai' % genome )
            os.remove( self.fafile )
            return True
    
    def _sam( self ):
        local_ref = self.fafile
        local_file = os.path.splitext( self.fafile )[ 0 ]
        if not os.path.exists( local_ref ):
            os.symlink( os.path.relpath( self.fapath ), self.fafile )
        command = shlex.split("samtools faidx %s" % local_ref)
        result = subprocess.call( command, stderr=self.logfile  )
        if result != 0:
            return False
        else:
            self.locations[ 'nt' ].append( local_ref )
            os.remove( local_ref )
            return True

class WithChDir():
    def __init__( self, target ):
        self.working = target
        self.previous = os.getcwd()
    def __enter__( self ):
        os.chdir( self.working )
    def __exit__( self, *args ):
        os.chdir( self.previous )
        
    
if __name__ == "__main__":
    # Parse command line.
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()    
    indexer, infile, outfile, working_dir = args
    
    # Create archive.
    idxobj = ManagedIndexer( outfile, infile, working_dir )
    idxobj.run_indexer( indexer )
    