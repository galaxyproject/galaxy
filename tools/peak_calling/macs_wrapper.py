import sys, subprocess, tempfile, shutil, glob, os, os.path, gzip
from galaxy import eggs
import pkg_resources
pkg_resources.require( "simplejson" )
import simplejson

CHUNK_SIZE = 1024

def gunzip_cat_glob_path( glob_path, target_filename, delete = False ):
    out = open( target_filename, 'wb' )
    for filename in glob.glob( glob_path ):
        fh = gzip.open( filename, 'rb' )
        while True:
            data = fh.read( CHUNK_SIZE )
            if data:
                out.write( data )
            else:
                break
        fh.close()
        if delete:
            os.unlink( filename )
    out.close()

def xls_to_interval( xls_file, interval_file, header = None ):
    out = open( interval_file, 'wb' )
    if header:
        out.write( '#%s\n' % header )
    wrote_header = False
    #From macs readme: Coordinates in XLS is 1-based which is different with BED format.
    for line in open( xls_file ):
        #keep all existing comment lines
        if line.startswith( '#' ):
            out.write( line )
        elif not wrote_header:
            out.write( '#%s' % line )
            wrote_header = True
        else:
            fields = line.split( '\t' )
            if len( fields ) > 1:
                fields[1] = str( int( fields[1] ) - 1 )
            out.write( '\t'.join( fields ) )
    out.close()

def main():
    options = simplejson.load( open( sys.argv[1] ) )
    output_bed = sys.argv[2]
    output_extra_html = sys.argv[3]
    output_extra_path = sys.argv[4]
    
    experiment_name = '_'.join( options['experiment_name'].split() ) #save experiment name here, it will be used by macs for filenames (gzip of wig files will fail with spaces - macs doesn't properly escape them)..need to replace all whitespace, split makes this easier
    cmdline = "macs -t %s" % ",".join( options['input_chipseq'] )
    if options['input_control']:
        cmdline = "%s -c %s" % ( cmdline, ",".join( options['input_control'] ) )
    cmdline = "%s --format='%s' --name='%s' --gsize='%s' --tsize='%s' --bw='%s' --pvalue='%s' --mfold='%s' %s --lambdaset='%s' %s" % ( cmdline, options['format'], experiment_name, options['gsize'], options['tsize'], options['bw'], options['pvalue'], options['mfold'], options['nolambda'], options['lambdaset'], options['futurefdr'] )
    if 'wig' in options:
        wigextend = int( options['wig']['wigextend']  )
        if wigextend >= 0:
            wigextend = "--wigextend='%s'" % wigextend
        else:
            wigextend = ''
        cmdline = "%s --wig %s --space='%s'" % ( cmdline, wigextend, options['wig']['space'] )
    if 'nomodel' in options:
        cmdline = "%s --nomodel --shiftsize='%s'" % ( cmdline, options['nomodel'] )
    if 'diag' in options:
        cmdline = "%s --diag --fe-min='%s' --fe-max='%s' --fe-step='%s'" % ( cmdline, options['diag']['fe-min'], options['diag']['fe-max'], options['diag']['fe-step'] )
    
    tmp_dir = tempfile.mkdtemp() #macs makes very messy output, need to contain it into a temp dir, then provide to user
    stderr_name = tempfile.NamedTemporaryFile().name # redirect stderr here, macs provides lots of info via stderr, make it into a report
    proc = subprocess.Popen( args=cmdline, shell=True, cwd=tmp_dir, stderr=open( stderr_name, 'wb' ) )
    proc.wait()
    #We don't want to set tool run to error state if only warnings or info, e.g. mfold could be decreased to improve model, but let user view macs log
    #Do not terminate if error code, allow dataset (e.g. log) creation and cleanup
    if proc.returncode:
        stderr_f = open( stderr_name )
        while True:
            chunk = stderr_f.read( CHUNK_SIZE )
            if not chunk:
                stderr_f.close()
                break
            sys.stderr.write( chunk )
    
    #run R to create pdf from model script
    if os.path.exists( os.path.join( tmp_dir, "%s_model.r" % experiment_name ) ):
        cmdline = 'R --vanilla --slave < "%s_model.r" > "%s_model.r.log"' % ( experiment_name, experiment_name )
        proc = subprocess.Popen( args=cmdline, shell=True, cwd=tmp_dir )
        proc.wait()
    
    
    #move bed out to proper output file
    created_bed_name =  os.path.join( tmp_dir, "%s_peaks.bed" % experiment_name )
    if os.path.exists( created_bed_name ):
        shutil.move( created_bed_name, output_bed )
    
    #parse xls files to interval files as needed
    if options['xls_to_interval']:
        create_peak_xls_file = os.path.join( tmp_dir, '%s_peaks.xls' % experiment_name )
        if os.path.exists( create_peak_xls_file ):
            xls_to_interval( create_peak_xls_file, options['xls_to_interval']['peaks_file'], header = 'peaks file' )
        create_peak_xls_file = os.path.join( tmp_dir, '%s_negative_peaks.xls' % experiment_name )
        if os.path.exists( create_peak_xls_file ):
            xls_to_interval( create_peak_xls_file, options['xls_to_interval']['negative_peaks_file'], header = 'negative peaks file' )
    
    #merge and move wig files as needed, delete gz'd files and remove emptied dirs
    if 'wig' in options:
        wig_base_dir = os.path.join( tmp_dir, "%s_MACS_wiggle" % experiment_name )
        if os.path.exists( wig_base_dir ):
            #treatment
            treatment_dir = os.path.join( wig_base_dir, "treat" )
            if os.path.exists( treatment_dir ):
                gunzip_cat_glob_path( os.path.join( treatment_dir, "*.wig.gz" ), options['wig']['output_treatment_file'], delete = True )
                os.rmdir( treatment_dir )
                #control
                if options['input_control']:
                    control_dir = os.path.join( wig_base_dir, "control" )
                    if os.path.exists( control_dir ):
                        gunzip_cat_glob_path( os.path.join( control_dir, "*.wig.gz" ), options['wig']['output_control_file'], delete = True )
                        os.rmdir( control_dir )
            os.rmdir( wig_base_dir )
    
    #move all remaining files to extra files path of html file output to allow user download
    out_html = open( output_extra_html, 'wb' )
    out_html.write( '<html><head><title>Additional output created by MACS (%s)</title></head><body><h3>Additional Files:</h3><p><ul>\n' % experiment_name )
    os.mkdir( output_extra_path )
    for filename in sorted( os.listdir( tmp_dir ) ):
        shutil.move( os.path.join( tmp_dir, filename ), os.path.join( output_extra_path, filename ) )
        out_html.write( '<li><a href="%s">%s</a></li>\n' % ( filename, filename ) )
    out_html.write( '</ul></p>\n' )
    out_html.write( '<h3>Messages from MACS:</h3>\n<p><pre>%s</pre></p>\n' % open( stderr_name, 'rb' ).read() )
    out_html.write( '</body></html>\n' )
    out_html.close()
    
    os.unlink( stderr_name )
    os.rmdir( tmp_dir )

if __name__ == "__main__": main()
