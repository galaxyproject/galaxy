PYTHONPATH="../../lib:../../eggs:../../eggs/`../check_python_ucs.py`"
export PYTHONPATH
echo "Getting files from NCBI..."
wget ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz
wget ftp://ftp.ncbi.nih.gov/pub/taxonomy/gi_taxid_nucl.dmp.gz
wget ftp://ftp.ncbi.nih.gov/pub/taxonomy/gi_taxid_prot.dmp.gz
echo "Unzipping untarring..."
gunzip -c taxdump.tar.gz | tar xvf -
gunzip gi_taxid_nucl.dmp.gz
gunzip gi_taxid_prot.dmp.gz
cat gi_taxid_nucl.dmp gi_taxid_prot.dmp > gi_taxid_all.dmp
rm gi_taxid_nucl.dmp gi_taxid_prot.dmp
echo "Parsing nodes.dmp..."
cat nodes.dmp | tr -s "\t" "|" | tr "|" "\t" | cut -f 1,2,3,5 > nodes.txt
echo "Collapsing taxonomy. This will take several hours..."
python tax1_NodeParser.py nodes.txt > node2child.txt
echo "Parsing names.dmg"
cat names.dmp | cut -f 1,2,4 -d "|" | tr -s "\t" "|"  | tr "|" "\t" | sed s/\"//g > names.txt
echo "Running tax2_Node2Name.py"
python tax2_Node2Name.py node2child.txt names.txt taxonomy.db
echo "Running tax3_gi2tax.py"
python tax3_gi2tax.py taxonomy.db gi_taxid_all.dmp
echo "Done!.."

