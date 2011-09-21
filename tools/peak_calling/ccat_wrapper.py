import sys, subprocess, tempfile, shutil, os.path

CCAT_BINARY = "CCAT"

def get_top_count( filename ):
    for line in open( filename ):
        if line.startswith( 'outputNum' ):
            return int( line.split()[-1].strip() ) 

def stop_err( tmp_dir, exception ):
    print >> sys.stderr, "Error running CCAT."
    shutil.rmtree( tmp_dir ) #some error has occurred, provide info and remove possibly non-empty temp directory
    raise exception

def main():
    input_tag_file = sys.argv[1]
    input_control_file = sys.argv[2]
    chrom_info_file = sys.argv[3]
    input_config_file = sys.argv[4]
    project_name = sys.argv[5]
    output_peak_file = sys.argv[6]
    output_region_file = sys.argv[7]
    output_top_file = sys.argv[8]
    output_log_file = sys.argv[9]
    
    tmp_dir = tempfile.mkdtemp()
    try:
        assert os.path.exists( chrom_info_file ), "The required chromosome length file does not exist."
        proc = subprocess.Popen( args="%s %s > %s" % ( CCAT_BINARY, " ".join( map( lambda x: "'%s'" % x, [ input_tag_file, input_control_file, chrom_info_file, input_config_file, project_name ] ) ), output_log_file ), shell=True, cwd=tmp_dir )
        proc.wait()
        if proc.returncode:
            raise Exception( "Error code: %i" % proc.returncode )
        output_num = get_top_count( input_config_file )
        shutil.move( os.path.join( tmp_dir, "%s.significant.peak" % project_name ), output_peak_file )
        shutil.move( os.path.join( tmp_dir, "%s.significant.region" % project_name ), output_region_file )
        shutil.move( os.path.join( tmp_dir, "%s.top%i.peak" % ( project_name, output_num ) ), output_top_file )
    except Exception, e:
        return stop_err( tmp_dir, e )
    os.rmdir( tmp_dir ) #clean up empty temp working directory

if __name__ == "__main__": main()
