echo "Getting files from NCBI..."
wget ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz
wget ftp://ftp.ncbi.nih.gov/pub/taxonomy/gi_taxid_nucl.dmp.gz
wget ftp://ftp.ncbi.nih.gov/pub/taxonomy/gi_taxid_prot.dmp.gz
echo "Unzipping untarring..."
gunzip -c taxdump.tar.gz | tar xvf -
gunzip gi_taxid_nucl.dmp.gz
gunzip gi_taxid_prot.dmp.gz
cat gi_taxid_nucl.dmp gi_taxid_prot.dmp > gi_taxid_all.dmp
echo "Sorting gi2tax files..."
sort -n -k 1 gi_taxid_all.dmp > gi_taxid_sorted.txt
rm gi_taxid_nucl.dmp gi_taxid_prot.dmp gi_taxid_all.dmp
echo "Removing parenthesis from names.dmp"
cat names.dmp | sed s/[\(\)\'\"]/_/g > names.temporary
mv names.dmp names.dmp.orig
mv names.temporary names.dmp 


