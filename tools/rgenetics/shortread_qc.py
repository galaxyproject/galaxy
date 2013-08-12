import os
import optparse
import shutil
import glob
from subprocess import Popen
from rgutils import RRun

'''
shortread_qc.py -i $input_file -t $input_file.ext

This script must:

1) Take the input file and the file extension and pass it to shortread_qc.r
2) Run shortread_qc.r
3) Get the output html, images and css files and put it on output_dir
4) Subsitute links to "./image/*.*" for "*.*" in the html file.
'''

HTML_PAGE = 'index.html'
CSS_FILE = 'QA.css'

R_SCRIPT_NAME = 'shortread_qc.r'

R_SCRIPT = '''
library('ShortRead')
qa_data = qa('%s', '%s', '%s')
report(qa_data, dest='%s')
'''

def run_r(Rstring, script_file, log_file, output_dir, *args):
    outfile = open(script_file, 'w')
    outfile.write(Rstring)
    outfile.close()
    standard_fd = open(log_file, 'w')
    process = Popen(' '.join(['R', '--vanilla --slave', '<', script_file]), shell=True,
                    stderr=standard_fd, stdout=standard_fd, cwd=output_dir)
    return_value = process.wait()
    standard_fd.close()


    

if __name__ == '__main__':
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-o', '--html-output', default=None)
    op.add_option('-d', '--output-dir', default="/tmp/shortread")
    op.add_option('-t', '--file-ext', default='fastq')
    op.add_option('-l', '--log', default='log.log')
    op.add_option('-n', '--namejob', default='ShortReadQC')
    opts, args = op.parse_args()
    opts.input_dir, opts.input_file = os.path.dirname(opts.input), os.path.basename(opts.input)
    opts.log_file = opts.log or os.path.join(opts.output_dir, opts.input_file + '.log')
    ext = opts.file_ext
    if ext == 'fastqsanger':
	ext = 'fastq'
    elif ext == 'bwa':
        ext = 'Bowtie'
    # Create output folder and save our R script in there.
    if not os.path.exists(opts.output_dir): 
        os.makedirs(opts.output_dir)
    r_script_file = os.path.join(opts.output_dir, R_SCRIPT_NAME)
    r_script = R_SCRIPT % ( opts.input_dir, opts.input_file, ext, opts.output_dir)
    #run_r(R_SCRIPT % ( opts.input_dir, opts.input_file, ext, opts.output_dir),r_script_file,opts.log_file,opts.output_dir)
    rlog,flist = RRun(rcmd=r_script,outdir=opts.output_dir,title=opts.namejob,tidy=True)
    # Get file contents.
    index_file_name = os.path.join(opts.output_dir, HTML_PAGE)
    try:
        index_file = open(index_file_name)
        index_contents = index_file.read()
        index_file.close()
    except:
        index_contents = '## error - is the Bioconductor shortreadqc package installed? ##\n'
    # Substitute contents in memory. A regexp looking for actual links
    # would be more correct, but a straight substitution seems ok for
    # our cases.
    index_contents = index_contents.replace('./image/', '')
    index_contents = index_contents.replace('</body>','<hr><h2>Log from R</h2>\n<pre>%s</pre>\n</body>' % ''.join(rlog))
    # Rewrite index.html in the output file
    new_index = open(opts.html_output, 'w')
    new_index.write(index_contents)
    new_index.close()

    # Move all files on 'image' to the root of the output folder
    for f in glob.glob(os.path.join(opts.output_dir, 'image', '*')):
        try:
            shutil.move(f, os.path.join(opts.output_dir, os.path.basename(f)))
        except IOError:
            print '!! WARNING !!: There was an IOError trying to shutil.move(%s, %s)' % (f, os.path.join(opts.output_dir, os.path.basename(f)))




    

        


    

    
    
