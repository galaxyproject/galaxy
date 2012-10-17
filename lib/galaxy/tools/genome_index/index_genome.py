#!/usr/bin/env python
"""
Export a history to an archive file using attribute files.

usage: %prog history_attrs dataset_attrs job_attrs out_file
    -G, --gzip: gzip archive file
"""
from __future__ import with_statement

import optparse, sys, os, tempfile, time, subprocess, shlex, tarfile, shutil

import pkg_resources
pkg_resources.require("simplejson")
import simplejson

class ManagedIndexer():
    def __init__( self, output_file, infile, workingdir, rsync_url, tooldata ):
        self.tooldatapath = os.path.abspath( tooldata )
        self.workingdir = os.path.abspath( workingdir )
        self.outfile = open( os.path.abspath( output_file ), 'w' )
        self.basedir = os.path.split( self.workingdir )[0]
        self.fasta = os.path.abspath( infile )
        self.locations = dict( nt=[], cs=[] )
        self.log = []
        self.rsync_opts = '-aclSzq'
        self.rsync_url = rsync_url
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
        self.genome = os.path.splitext( self.fafile )[0]
        with WithChDir( self.basedir ):
            if indexer not in self.indexers:
                sys.stderr.write( 'The requested indexing function does not exist' )
                exit(127)
            else:
                with WithChDir( self.workingdir ):
                    self._log( 'Running indexer %s.' % indexer )
                    result = getattr( self, self.indexers[ indexer ] )()
                if result in [ None, False ]:
                    sys.stderr.write( 'Error running indexer %s, %s' % ( indexer, result ) )
                    self._flush_files()
                    exit(1)
                else:
                    self._log( self.locations )
                    self._log( 'Indexer %s completed successfully.' % indexer )
                    self._flush_files()
                    exit(0)
                
    def _check_link( self ):
        self._log( 'Checking symlink to %s' % self.fafile )
        if not os.path.exists( self.fafile ):
            self._log( 'Symlink not found, creating' )
            os.symlink( os.path.relpath( self.fapath ), self.fafile )
    
    def _do_rsync( self, idxpath ):
        self._log( 'Trying rsync at %s/%s%s' % ( self.rsync_url, self.genome, idxpath ) )
        result = subprocess.call( shlex.split( 'rsync %s %s/%s%s .' % ( self.rsync_opts, self.rsync_url, self.genome, idxpath ) ), stderr=self.logfile )
        if result != 0:
            self._log( 'Rsync failed or index not found. Generating.' )
        else:
            self._log( 'Rsync succeeded.' )
        return result
    
    def _flush_files( self ):
        simplejson.dump( self.locations, self.outfile )
        self.outfile.close()
        self.logfile.close()
    
    def _log( self, stuff ):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S %z')
        self.logfile.write( "[%s] %s\n" % (timestamp, stuff) )
        
    def _bwa( self ):
        result = self._do_rsync( '/bwa_index/' )
        if result == 0:
            self.locations[ 'nt' ].append( self.fafile )
            return self._bwa_cs()
        else:
            self._check_link()
            command = shlex.split( 'bwa index -a bwtsw %s' % self.fafile )
            result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
            if result != 0:
                newcommand = shlex.split( 'bwa index -c %s' % self.fafile )
                result = call( newcommand, stderr=self.logfile, stdout=self.logfile )
            if result == 0:
                self.locations[ 'nt' ].append( self.fafile )
                os.remove( self.fafile )
                return self._bwa_cs()
            else:
                self._log( 'BWA (base) exited with code %s' % result )
                return False
    
    def _bwa_cs( self ):
        if not os.path.exists( os.path.join( self.workingdir, 'cs' ) ):
            os.makedirs( 'cs' )
            with WithChDir( 'cs' ):
                self._check_link()
                command = shlex.split( 'bwa index -a bwtsw -c %s' % self.fafile )
                result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
                if result != 0:
                    newcommand = shlex.split( 'bwa index -c %s' % self.fafile )
                    result = call( newcommand, stderr=self.logfile, stdout=self.logfile )
                    if result == 0:
                        self.locations[ 'cs' ].append( self.fafile )
                        os.remove( self.fafile )
                    else:
                        self._log( 'BWA (color) exited with code %s' % result )
                        return False
                else:
                    self.locations[ 'cs' ].append( self.fafile )
                    os.remove( self.fafile )
        else:
            self.locations[ 'cs' ].append( self.fafile )
        temptar = tarfile.open( 'cs.tar', 'w' )
        temptar.add( 'cs' )
        temptar.close()
        shutil.rmtree( 'cs' )
        return True
        
    
    def _bowtie( self ):
        result = self._do_rsync( '/bowtie_index/' )
        if result == 0:
            self.locations[ 'nt' ].append( self.genome )
            return self._bowtie_cs()
        else:
            self._check_link()
            command = shlex.split( 'bowtie-build -f %s %s' % ( self.fafile, self.genome ) )
            result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
            if result == 0:
                self.locations[ 'nt' ].append( self.genome )
                os.remove( self.fafile )
                return self._bowtie_cs()
            else:
                self._log( 'Bowtie (base) exited with code %s' % result )
                return False
            
    def _bowtie_cs( self ):
        indexdir = os.path.join( os.getcwd(), 'cs' )
        if not ( os.path.exists( indexdir ) ):
            os.makedirs( indexdir )
            with WithChDir( indexdir ):
                self._check_link()
                command = shlex.split( 'bowtie-build -C -f %s %s' % ( self.fafile, self.genome ) )
                result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
                if result == 0:
                    self.locations[ 'cs' ].append( self.genome )
                else:
                    self._log( 'Bowtie (color) exited with code %s' % result )
                    return False
            os.remove( os.path.join( indexdir, self.fafile ) )
        else:
            self.locations[ 'cs' ].append( self.genome )
        temptar = tarfile.open( 'cs.tar', 'w' )
        temptar.add( 'cs' )
        temptar.close()
        shutil.rmtree( 'cs' )    
        return True

    
    def _bowtie2( self ):
        result = self._do_rsync( '/bowtie2_index/' )
        if result == 0:
            self.locations[ 'nt' ].append( self.fafile )
            return True
        ref_base = os.path.splitext(self.fafile)[0]
        self._check_link()
        command = shlex.split( 'bowtie2-build %s %s' % ( self.fafile, ref_base ) )
        result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
        if result == 0:
            self.locations[ 'nt' ].append( ref_base )
            os.remove( self.fafile )
            return True
        else:
            self._log( 'Bowtie2 exited with code %s' % result )
            return False
    
    def _twobit( self ):
        """Index reference files using 2bit for random access.
        """
        result = self._do_rsync( '/seq/%s.2bit' % self.genome )
        if result == 0:
            self.locations['nt'].append( "%s.2bit" % self.genome )
            return True
        else:
            out_file = "%s.2bit" % self.genome
            self._check_link()
            command = shlex.split( 'faToTwoBit %s %s' % ( self.fafile, out_file ) )
            result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
            if result == 0:
                self.locations['nt'].append( out_file )
                os.remove( self.fafile )
                return True
            else:
                self._log( 'faToTwoBit exited with code %s' % result )
                return False
    
    def _perm( self ):
        result = self._do_rsync( '/perm_index/' )
        self._check_link()
        genome = self.genome
        read_length = 50
        for seed in [ 'F3', 'F4' ]:
            key = '%s_%s_%s' % (self.genome, seed, read_length)
            desc = '%s: seed=%s, read length=%s' % (self.genome, seed, read_length)
            index = "%s_base_%s_%s.index" % (self.genome, seed, read_length)
            if not os.path.exists( index ):
                command = shlex.split("PerM %s %s --readFormat fastq --seed %s -m -s %s" % (self.fafile, read_length, seed, index))
                result = subprocess.call( command )
                if result != 0:
                    self._log( 'PerM (base) exited with code %s' % result )
                    return False
            self.locations[ 'nt' ].append( [ key, desc, index ] )
        os.remove( self.fafile )
        return self._perm_cs()

    def _perm_cs( self ):
        genome = self.genome
        read_length = 50
        if not os.path.exists( 'cs' ):
            os.makedirs( 'cs' )
        with WithChDir( 'cs' ):
            self._check_link()
            for seed in [ 'F3', 'F4' ]:
                key = '%s_%s_%s' % (genome, seed, read_length)
                desc = '%s: seed=%s, read length=%s' % (genome, seed, read_length)
                index = "%s_color_%s_%s.index" % (genome, seed, read_length)
                if not os.path.exists( index ):
                    command = shlex.split("PerM %s %s --readFormat csfastq --seed %s -m -s %s" % (self.fafile, read_length, seed, index))
                    result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
                if result != 0:
                    self._log( 'PerM (color) exited with code %s' % result )
                    return False
                self.locations[ 'cs' ].append( [ key, desc, index ] )
            os.remove( self.fafile )
        temptar = tarfile.open( 'cs.tar', 'w' )
        temptar.add( 'cs' )
        temptar.close()
        shutil.rmtree( 'cs' )
        return True

    def _picard( self ):
        result = self._do_rsync( '/srma_index/' )
        if result == 0 and os.path.exists( '%s.dict' % self.genome):
            self.locations[ 'nt' ].append( self.fafile )
            return True
        local_ref = self.fafile
        srma = os.path.abspath( os.path.join( self.tooldatapath, 'shared/jars/picard/CreateSequenceDictionary.jar' ) )
        genome = os.path.splitext( self.fafile )[0]
        self._check_link()
        if not os.path.exists( '%s.fai' % self.fafile ) and not os.path.exists( '%s.fai' % self.genome ):
            command = shlex.split( 'samtools faidx %s' % self.fafile )
            subprocess.call( command, stderr=self.logfile  )
        command = shlex.split( "java -jar %s R=%s O=%s.dict URI=%s" \
                     % ( srma, local_ref, genome, local_ref ) )
        if not os.path.exists( '%s.dict' % self.genome ):
            result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
            self._log( ' '.join( command ) )
            if result != 0:
                self._log( 'Picard exited with code %s' % result )
                return False
        self.locations[ 'nt' ].append( self.fafile )
        os.remove( self.fafile )
        return True
    
    def _sam( self ):
        local_ref = self.fafile
        local_file = os.path.splitext( self.fafile )[ 0 ]
        print 'Trying rsync'
        result = self._do_rsync( '/sam_index/' )
        if result == 0 and ( os.path.exists( '%s.fai' % self.fafile ) or os.path.exists( '%s.fai' % self.genome ) ):
            self.locations[ 'nt' ].append( '%s.fai' % local_ref )
            return True
        self._check_link()
        print 'Trying indexer'
        command = shlex.split("samtools faidx %s" % local_ref)
        result = subprocess.call( command, stderr=self.logfile, stdout=self.logfile )
        if result != 0:
            self._log( 'SAM exited with code %s' % result )
            return False
        else:
            self.locations[ 'nt' ].append( '%s.fai' % local_ref )
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
    indexer, infile, outfile, working_dir, rsync_url, tooldata = args
    
    # Create archive.
    idxobj = ManagedIndexer( outfile, infile, working_dir, rsync_url, tooldata )
    returncode = idxobj.run_indexer( indexer )
    if not returncode:
        exit(1)
    exit(0)