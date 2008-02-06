"""
    tax1_NodeParser.py <nodes_file>
    
    flattens NCBI taxonomy by printing list of children for every node
    nodes_file is created from nodes.dmp file using the following command:
    
    cat nodes.dmp | tr -s "\t" "|" | tr "|" "\t" | cut -f 1,2,3,5 > nodes.txt
    (nodes.dmp is downloaded from NCBI taxonomy FTP site)
    
    anton nekrutenko | anton@bx.psu.edu

"""

import sys
import string 

def findAll(L, value):
    hits = []
    i = 0
    for item in L:
        if item == value:
            hits.append(i)
        else:
            pass
        i += 1
    return hits

def makeLookup(L):
    D = {}
    i = 0
    for item in L:
        if item in D:
            D[item].append(i)
        else:
            D[item] = [i]
        i += 1
        
    return D
    
def addUnique(baseList, otherList):
    auxDict = dict.fromkeys(baseList)
    for item in otherList:
        if item not in auxDict:
            baseList.append(item)
            auxDict[item] = None
    return baseList


def main():

    taxId = []
    taxParentId = []
    name = []

    try:
        inFile  = sys.argv[1]
        nodeFile = open(inFile, 'r')
    except:
        sys.stderr.write('tax1_NodeParser.py <nodes_file>: No arguments or file does not exist\n')
        sys.exit(0)
        

    try:
        for line in nodeFile:
            field = string.split(line.rstrip(), '\t')
            taxId.append(int(field[0]))
            taxParentId.append(int(field[1]))
            name.append(field[2])
    finally:
        nodeFile.close()
    
    # Check data consistency
    
    if (len(taxId)+len(taxParentId)+len(name))/3 != len(taxId):
        sys.stderr.write('Arrays are of different length: Corrupted input file')
        sys.exit(0)
    else:
        pass
        
    parentLookUp = makeLookup(taxParentId) 

    i = 0
    children = []
    
    for taxon in taxId:
        try:
            children = parentLookUp[taxon] #findAll(taxParentId, taxon)

        except:
            pass
 
        for child in children:
            if len(children) > 0:
                if taxId[child] != taxParentId[child]:
                    try:
                        children = addUnique(children, parentLookUp[taxId[child]])
                    except:
                        pass
                    
                else:
                    pass
            
        if len(children) > 0:    
            for child in children: 
                outTmp = string.Template('$pId\t$pRank\t$cId\t$cRank')
                out = outTmp.substitute(pId = taxon, pRank = name[i], cId = taxId[child], cRank = name[child])
                print  out
        else:
            outTmp = string.Template('$pId\t$pRank\t0\tNone')
            out = outTmp.substitute(pId = taxon, pRank = name[i])
            print out
            
        children = []
        i += 1    
        

if __name__ == "__main__":
    main()      