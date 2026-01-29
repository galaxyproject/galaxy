echo "This will take several hours to finish due to the size of the databases (about 30GB)..." 
echo "Getting nt database from NCBI..."
wget ftp://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nt.gz
echo "Changing fasta title lines to >ginumber_seqlength..."
echo "Formatting nt database to chunks of 2GB each..."
gunzip -c nt.gz | python convert_title.py | formatdb -i stdin -p F -n "nt.chunk" -v 2000
echo "Remove the zip file, keep the formatted files."
rm nt.gz

echo "Getting wgs database from NCBI..."
wget ftp://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/wgs.gz
echo "Changing fasta title lines to >ginumber_seqlength..."
echo "Formatting wgs database to chunks of 2GB each..."
gunzip -c wgs.gz | python convert_title.py | formatdb -i stdin -p F -n "wgs.chunk" -v 2000
echo "Remove the zip file, keep the formatted files."
rm wgs.gz

echo "Job finished"
