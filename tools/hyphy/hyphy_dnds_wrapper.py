#Guru
#takes fasta alignments, a distance metric and builds neighbor joining trees
import os, sys
from galaxy import eggs
from galaxy.tools.util import hyphy_util

# Directory to be used when creating temporary files
tmp_file_dir = sys.argv.pop()
#Retrieve hyphy path, this will need to be the same across the cluster
tool_data = sys.argv.pop()
HYPHY_PATH = os.path.join( tool_data, "HYPHY" )
HYPHY_EXECUTABLE = os.path.join( HYPHY_PATH, "HYPHY" )

#Read command line arguments
input_filename = os.path.abspath(sys.argv[1].strip())
output_filename = os.path.abspath(sys.argv[2].strip())
tree_contents = sys.argv[3].strip()
nuc_model = sys.argv[4].strip()
analysis = sys.argv[5].strip()

if tree_contents == "":
    print >> sys.stderr, "Please specify a valid tree definition."
    sys.exit()
        
tree_filename = hyphy_util.get_filled_temp_filename( tree_contents, directory=tmp_file_dir )

if analysis == "local":
    fitter_filename = hyphy_util.get_filled_temp_filename( hyphy_util.SimpleLocalFitter, directory=tmp_file_dir )
else:
    fitter_filename = hyphy_util.get_filled_temp_filename( hyphy_util.SimpleGlobalFitter, directory=tmp_file_dir )

tabwriter_filename = hyphy_util.get_filled_temp_filename( hyphy_util.TabWriter, directory=tmp_file_dir )
FastaReader_filename = hyphy_util.get_filled_temp_filename( hyphy_util.FastaReader, directory=tmp_file_dir )
#setup Config file
config_filename = hyphy_util.get_dnds_config_filename(fitter_filename, tabwriter_filename, "Universal", tree_filename, input_filename, nuc_model, output_filename, FastaReader_filename)

#Run Hyphy
hyphy_cmd = "%s BASEPATH=%s USEPATH=/dev/null %s" % (HYPHY_EXECUTABLE, HYPHY_PATH, config_filename)
hyphy = os.popen(hyphy_cmd, 'r')
#print hyphy.read()
hyphy.close()

#remove temporary files
os.unlink(fitter_filename)
os.unlink(tabwriter_filename)
os.unlink(tree_filename)
os.unlink(FastaReader_filename)
os.unlink(config_filename)

if nuc_model == "000000":
    model = "F81"
elif nuc_model == "010010":
    model = "HKY85"
else:
    model = "REV"
    
print "Analysis: %s; Model: %s; Tree: %s" %(analysis, model, tree_contents)
