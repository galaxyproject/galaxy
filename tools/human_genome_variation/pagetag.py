#!/usr/bin/env python

"""
This accepts as input a file of the following format:

    Site   Sample   Allele1   Allele2

for example:

    000834   D001    G       G
    000834   D002    G       G
    000834   D003    G       G
    000834   D004    G       G
    000834   D005    N       N
    000834   E001    G       G
    000834   E002    G       G
    000834   E003    G       G
    000834   E004    G       G
    000834   E005    G       G
    000963   D001    T       T
    000963   D002    T       T
    000963   D003    T       T
    000963   D004    T       T
    000963   D005    N       N
    000963   E001    T       T
    000963   E002    N       N
    000963   E003    G       T
    000963   E004    G       G
    000963   E005    G       T

and a rsquare threshold and outputs two files: 

a) a file of input snps (one on each line). A SNP is identified by the "Site"
column in the input file

b) a file where each line has the following:
    SNP     list
where SNP is one of  the SNPs and the "list" is a comma separated list of SNPs 
that exceed the rsquare threshold with the first SNP.
"""

from sys import argv, stderr, exit
from getopt import getopt, GetoptError

__author__ = "Aakrosh Ratan"
__email__  = "ratan@bx.psu.edu"

# do we want the debug information to be printed?
debug_flag = False

# denote different combos of alleles in code
HOMC  = str(1)
HOMR  = str(2)
HETE  = str(3)
OTHER = str(4)

indexcalculator = {(HOMC,HOMC) : 0,
                   (HOMC,HOMR) : 1,
                   (HOMC,HETE) : 2,
                   (HOMR,HOMC) : 3,
                   (HOMR,HOMR) : 4,
                   (HOMR,HETE) : 5,
                   (HETE,HOMC) : 6,
                   (HETE,HOMR) : 7,
                   (HETE,HETE) : 8}

def read_inputfile(filename, samples):
    input = {}

    file = open(filename, "r")

    for line in file:
        position,sample,allele1,allele2 = line.split()

        # if the user specified a list of samples, then only use those samples
        if samples != None and sample not in samples: continue
            
        if position in input:
            v = input[position]
            v[sample] = (allele1,allele2)
        else:
            v = {sample : (allele1, allele2)}
            input[position] = v

    file.close()
    return input

def annotate_locus(input, minorallelefrequency, snpsfile):
    locus = {}
    for k,v in input.items():
        genotypes = [x for x in v.values()]
        alleles   = [y for x in genotypes for y in x]
        alleleset = list(set(alleles))
        alleleset = list(set(alleles) - set(["N","X"]))

        if len(alleleset) == 2:
            genotypevec = ""
            num1 = len([x for x in alleles if x == alleleset[0]])
            num2 = len([x for x in alleles if x == alleleset[1]])
 
            if num1 > num2: 
                major = alleleset[0]    
                minor = alleleset[1]
                minorfreq = (num2 * 1.0)/(num1 + num2)
            else:
                major = alleleset[1] 
                minor = alleleset[0]
                minorfreq = (num1 * 1.0)/(num1 + num2)

            if minorfreq < minorallelefrequency: continue
               
            for gen in genotypes:
                if gen == (major,major):
                    genotypevec += HOMC 
                elif gen == (minor,minor):
                    genotypevec += HOMR
                elif gen == (major, minor) or gen == (minor, major):
                    genotypevec += HETE
                else:  
                    genotypevec += OTHER

            locus[k] = genotypevec,minorfreq
        elif len(alleleset) > 2:
            print >> snpsfile, k
    return locus

def calculateLD(loci, rsqthreshold):
    snps = list(loci)
    rsquare = {}

    for index,loc1 in enumerate(snps):
        for loc2 in snps[index + 1:]:
            matrix = [0]*9

            vec1 = loci[loc1][0]
            vec2 = loci[loc2][0]

            for gen in zip(vec1,vec2):
                if gen[0] == OTHER or gen[1] == OTHER: continue
                matrix[indexcalculator[gen]] += 1

            n   = sum(matrix)
            x11 = 2*matrix[0] + matrix[2] + matrix[6]
            x12 = 2*matrix[1] + matrix[2] + matrix[7]
            x21 = 2*matrix[3] + matrix[6] + matrix[5]
            x22 = 2*matrix[4] + matrix[6] + matrix[5]

            p   = (x11 + x12 + matrix[8] * 1.0) / (2 * n)
            q   = (x11 + x21 + matrix[8] * 1.0) / (2 * n)
     
            p11    = p * q

            oldp11 = p11
            range  = 0.0
            converged         = False
            convergentcounter = 0
            if p11 > 0.0:
                while converged == False and convergentcounter < 100:
                    if (1.0 - p - q + p11) != 0.0 and oldp11 != 0.0:    
                        num = matrix[8] * p11 * (1.0 - p - q + p11)
                        den = p11 * (1.0 - p - q + p11) + (p - p11)*(q - p11)
                        p11 = (x11 + (num/den))/(2.0*n)
                        range = p11/oldp11
                        if range >= 0.9999 and range <= 1.001:
                            converged = True
                        oldp11 = p11
                        convergentcounter += 1 
                    else:
                        converged = True
 
            dvalue = 0.0
            if converged == True:
                dvalue = p11 - (p * q)
    
            if dvalue != 0.0:
                rsq = (dvalue**2)/(p*q*(1-p)*(1-q))
                if rsq >= rsqthreshold:
                    rsquare["%s %s" % (loc1,loc2)] = rsq

    return rsquare

def main(inputfile, snpsfile, neigborhoodfile, \
         rsquare, minorallelefrequency, samples):
    # read the input file
    input = read_inputfile(inputfile, samples)     
    print >> stderr, "Read %d locations" % len(input)

    # open the snpsfile to print
    file = open(snpsfile, "w")

    # annotate the inputs, remove the abnormal loci (which do not have 2 alleles
    # and add the major and minor allele to each loci
    loci = annotate_locus(input, minorallelefrequency, file)
    print >> stderr, "Read %d interesting locations" % len(loci)
        
    # print all the interesting loci as candidate snps
    for k in loci.keys(): print >> file, k
    file.close() 
    print >> stderr, "Finished creating the snpsfile"

    # calculate the LD values and store it if it exceeds the threshold
    lds = calculateLD(loci, rsquare)
    print >> stderr, "Calculated all the LD values"

    # create a list of SNPs   
    snps   = {}
    ldvals = {}
    for k,v in lds.items():
        s1,s2 = k.split()
        if s1 in snps: snps[s1].append(s2)
        else         : snps[s1] = [s2]    
        if s2 in snps: snps[s2].append(s1)
        else         : snps[s2] = [s1]    

        if s1 in ldvals: ldvals[s1].append(str(v))
        else           : ldvals[s1] = [str(v)]
        if s2 in ldvals: ldvals[s2].append(str(v))
        else           : ldvals[s2] = [str(v)]
           
    # print the snps to the output file
    file = open(neigborhoodfile, "w")

    for k,v in snps.items():
        ldv = ldvals[k]
        if debug_flag == True:
            print >> file, "%s\t%s\t%s" % (k, ",".join(v), ",".join(ldv))
        else:            
            print >> file, "%s\t%s" % (k, ",".join(v))

    file.close()
 

def read_list(filename):
    file = open(filename, "r")
    list = {}    

    for line in file:
        list[line.strip()] = 1

    file.close()
    return list

def usage():
    f = stderr
    print >> f, "usage:"
    print >> f, "pagetag [options] input.txt snps.txt neighborhood.txt"
    print >> f, "where input.txt is the prettybase file"
    print >> f, "where snps.txt is the first output file with the snps"
    print >> f, "where neighborhood.txt is the output neighborhood file"
    print >> f, "where the options are:"
    print >> f, "-h,--help : print usage and quit"
    print >> f, "-d,--debug: print debug information"
    print >> f, "-r,--rsquare: the rsquare threshold (default : 0.64)"
    print >> f, "-f,--freq : the minimum MAF required (default: 0.0)"
    print >> f, "-s,--sample : a list of samples to be clustered"   

if __name__ == "__main__":
    try:
        opts, args = getopt(argv[1:], "hds:r:f:",\
                    ["help", "debug", "rsquare=","freq=", "sample="])
    except GetoptError, err:
        print str(err)
        usage()
        exit(2) 

    rsquare = 0.64
    minorallelefrequency = 0.0
    samples = None

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            exit()
        elif o in ("-d", "--debug"):
            debug_flag = True
        elif o in ("-r", "--rsquare"):
            rsquare = float(a)
        elif o in ("-f", "--freq"):
            minorallelefrequency = float(a)
        elif o in ("-s", "--sample"):
            samples = read_list(a)
        else:
            assert False, "unhandled option"

    if rsquare < 0.00 or rsquare > 1.00: 
        print >> stderr, "input value of rsquare should be in [0.00, 1.00]"
        exit(3)

    if minorallelefrequency < 0.0 or minorallelefrequency > 0.5:
        print >> stderr, "input value of MAF should be (0.00,0.50]"
        exit(4)

    if len(args) != 3:
        usage()
        exit(5)

    main(args[0], args[1], args[2], rsquare, minorallelefrequency, samples)
