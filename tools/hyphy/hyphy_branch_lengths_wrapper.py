#Dan Blankenberg
#takes commandline tree def and input multiple fasta alignment file and runs the branch length ananlysis
import os, sys
import hyphy_util

#Retrieve hard coded hyphy path, this will need to be the same across the cluster
HYPHY_PATH = hyphy_util.HYPHY_PATH
HYPHY_EXECUTABLE = hyphy_util.HYPHY_EXECUTABLE

#Read command line arguments
input_filename = os.path.abspath(sys.argv[1].strip())
output_filename = os.path.abspath(sys.argv[2].strip())
tree_contents = sys.argv[3].strip()
nuc_model = sys.argv[4].strip()
base_freq = sys.argv[5].strip()
model_options = sys.argv[6].strip()

#Set up Temporary files for hyphy run
#set up tree file
tree_filename = hyphy_util.get_filled_temp_filename(tree_contents)

#Guess if this is a single or multiple FASTA input file
found_blank = False
is_multiple = False
for line in open(input_filename):
    line = line.strip()
    if line == "": found_blank = True
    elif line.startswith(">") and found_blank:
        is_multiple = True
        break
    else: found_blank = False

#set up BranchLengths file
BranchLengths_filename = hyphy_util.get_filled_temp_filename(hyphy_util.BranchLengths)
if is_multiple: 
    os.unlink(BranchLengths_filename)
    BranchLengths_filename = hyphy_util.get_filled_temp_filename(hyphy_util.BranchLengthsMF)
    print "Multiple Alignment Analyses"
else: print "Single Alignment Analyses"

#setup Config file
config_filename = hyphy_util.get_branch_lengths_config_filename(input_filename, nuc_model, model_options, base_freq, tree_filename, output_filename, BranchLengths_filename)

#Run Hyphy
hyphy_cmd = "%s BASEPATH=%s USEPATH=/dev/null %s" % (HYPHY_EXECUTABLE, HYPHY_PATH, config_filename)
hyphy = os.popen(hyphy_cmd, 'r')
#print hyphy.read()
hyphy.close()

#remove temporary files
os.unlink(BranchLengths_filename)
os.unlink(tree_filename)
os.unlink(config_filename)
