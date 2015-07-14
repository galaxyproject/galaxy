#!/usr/bin/env python
import sys

def main():
    inFile = open(sys.argv[1], 'r')
    outFile = open(sys.argv[2], 'w')

    eno = 0
    reset = 1
    exon_check = 0
    for line in inFile:

        # skip comment lines that start with the '#' character
        if line[0] != '#':
            # split line into columns by tab
            data = line.strip().split('\t')
            
            ti = ''
            gi = ''
            gn = ''

            if data[2] == "mRNA":
                data[2] = "transcript"

            if data[2] == "exon" or data[2] == "gene" or data[2] == "transcript" or data[2] == "CDS":
                tr = "transcript"
                if data[2] == "gene":
                    reset = 1
                    eno = 0
                    gi = data[-1].split('GeneID:')[-1].split(',')[0].split(';')[0]
                    ID = data[-1].split('ID=')[-1].split(';')[0]
                    # pid = data[-1].split('Parent=')[-1].split(';')[0]
                    # print data[-1].split('GeneID:')[-1]
                    gn = data[-1].split('gene=')[-1].split(';')[0]
                    data[-1] = 'gene_id ' + '"' + gi + '"; ' + 'gene_version "1"; ' + tr + '_id ' + '"' + ID + '"; ' + tr + '_version "1"; ' + 'gene_source "ncbi"; ' + 'gene_name ' + '"' + gn + '"; '
                  
            else:
                t = "protein"

                if data[2] == "exon":
                    
                    eno = eno + 1
                    t = "exon"
                    tr = "transcript"
                  
            
                # ID = data[-1].split('ID=')[-1].split(';')[0]
                pid = data[-1].split('Parent=')[-1].split(';')[0]
                gi = data[-1].split('GeneID:')[-1].split(',')[0].split(';')[0]
                gn = data[-1].split('gene=')[-1].split(';')[0]
                ti = data[-1].split('transcript_id=')[-1].split(';')[0]
                pi = data[-1].split('protein_id=')[-1].split(';')[0]

                if ti.find("=") != -1:
                    ti = pi
              
                if data[2] == "CDS":
                    if reset == 1:
                        eno = 0
                        eset = 0

                eno = eno + 1

            data[-1] =  'gene_id ' + '"' + gi +  '"; ' + 'gene_version "1"; ' + tr + '_id ' + '"' + pid + '"; ' + tr + '_version "1"; ' + 'exon_number ' + '"' + str(eno) + '"; ' + 'gene_source "ncbi"; ' + 'gene_name ' + '"' + gn + '"; ' + t + '_id "' + ti + '"; ' + t + '_version "1";'
            if data[2] == "transcript":
                tr = "transcript"
                data[-1] =  'gene_id ' + '"' + gi +  '"; ' + 'gene_version "1"; ' + tr + '_id ' + '"' + pid + '"; ' + tr + '_version "1"; ' + 'exon_number ' + '"' + str(eno) + '"; ' + 'gene_source "ncbi"; ' + 'gene_name ' + '"' + gn + '"; '

            # print out this new GTF line
            outFile.write('\t'.join(data))
            outFile.write('\n')

if __name__ == '__main__':
    main()