#!/usr/bin/python

import os.path
import sys
import optparse

import vcfClass
from vcfClass import *

import tools
from tools import *

if __name__ == "__main__":
  main()

# Check that the reference and alternate in the dbsnp vcf file match those
# from the input vcf file.
def checkRefAlt(vcfRef, vcfAlt, dbsnpRef, dbsnpAlt, ref, position, annotation):
  text = "WARNING: ref and alt alleles differ between vcf and " + annotation + " " + ref + ":" + str(position) + " vcf: " + \
         vcfRef + "/" + vcfAlt + ", dbsnp: " + dbsnpRef + "/" + dbsnpAlt

  allelesAgree = True
  if vcfRef.lower() != dbsnpRef.lower():
    if vcfRef.lower() != dbsnpAlt.lower():
      #print >> sys.stderr, text
      allelesAgree = False
  else:
    if vcfAlt.lower() != dbsnpAlt.lower():
      #print >> sys.stderr, text
      allelesAgree = False

  return allelesAgree

# Intersect two vcf files.  It is assumed that the two files are
# sorted by genomic coordinates and the reference sequences are
# in the same order.
def annotateVcf(v, d, outputFile, annotation):
  success1 = v.getRecord()
  success2 = d.getRecord()
  currentReferenceSequence = v.referenceSequence

# Finish when the end of the first file has been reached.
  while success1:

# If the end of the dbsnp vcf file is reached, write out the
# remaining records from the vcf file.
    if not success2:
      outputFile.write(v.record)
      success1 = v.getRecord()

    if v.referenceSequence == d.referenceSequence and v.referenceSequence == currentReferenceSequence:
      if v.position == d.position:
        allelesAgree = checkRefAlt(v.ref, v.alt, d.ref, d.alt, v.referenceSequence, v.position, annotation)
        if annotation == "dbsnp": v.rsid = d.getDbsnpInfo()
        elif annotation == "hapmap":
          if allelesAgree: v.info += ";HM3"
          else: v.info += ";HM3A"
        record = v.buildRecord(False)
        outputFile.write(record)

        success1 = v.getRecord()
        success2 = d.getRecord()
      elif d.position > v.position: success1 = v.parseVcf(d.referenceSequence, d.position, True, outputFile)
      elif v.position > d.position: success2 = d.parseVcf(v.referenceSequence, v.position, False, None)
    else:
      if v.referenceSequence == currentReferenceSequence: success1 = v.parseVcf(d.referenceSequence, d.position, True, outputFile)
      elif d.referenceSequence == currentReferenceSequence: success2 = d.parseVcf(v.referenceSequence, v.position, False, None)

# If the last record for a reference sequence is the same for both vcf
# files, they will both have referenceSequences different from the
# current reference sequence.  Change the reference sequence to reflect
# this and proceed.
      else:
        if v.referenceSequence != d.referenceSequence:
          print >> sys.stderr, "ERROR: Reference sequences for both files are unexpectedly different."
          print >> sys.stderr, "Check that both files contain records for the following reference sequences:"
          print >> sys.stderr, "\t", v.referenceSequence, " and ", d.referenceSequence
          exit(1)
      currentReferenceSequence = v.referenceSequence

def main():

# Parse the command line options
  usage = "Usage: vcfPytools.py annotate [options]"
  parser = optparse.OptionParser(usage = usage)
  parser.add_option("-i", "--in",
                    action="store", type="string",
                    dest="vcfFile", help="input vcf files")
  parser.add_option("-d", "--dbsnp",
                    action="store", type="string",
                    dest="dbsnpFile", help="input dbsnp vcf file")
  parser.add_option("-m", "--hapmap",
                    action="store", type="string",
                    dest="hapmapFile", help="input hapmap vcf file")
  parser.add_option("-o", "--out",
                    action="store", type="string",
                    dest="output", help="output vcf file")

  (options, args) = parser.parse_args()

# Check that a single  vcf file is given.
  if options.vcfFile == None:
    parser.print_help()
    print >> sys.stderr, "\nInput vcf file (--in, -i) is required for dbsnp annotation."
    exit(1)

# Check that either a hapmap or a dbsnp vcf file is included.
  if options.dbsnpFile == None and options.hapmapFile == None:
    parser.print_help()
    print >> sys.stderr, "\ndbSNP or hapmap vcf file is required (--dbsnp, -d, --hapmap, -h)."
    exit(1)
  elif options.dbsnpFile != None and options.hapmapFile != None:
    parser.print_help()
    print >> sys.stderr, "\ndbSNP or hapmap vcf file is required, not both (--dbsnp, -d, --hapmap, -h)."
    exit(1)

# Set the output file to stdout if no output file was specified.
  outputFile, writeOut = setOutput(options.output) # tools.py

  v = vcf() # Define vcf object.
  d = vcf() # Define dbsnp/hapmap vcf object.
  if options.dbsnpFile:
    d.dbsnpVcf = True
    annotationFile = options.dbsnpFile
    annotation = "dbsnp"
  elif options.hapmapFile:
    d.hapmapVcf = True
    annotationFile = options.hapmapFile
    annotation = "hapmap"

# Open the vcf files.
  v.openVcf(options.vcfFile)
  d.openVcf(annotationFile)

# Read in the header information.
  v.parseHeader(options.vcfFile, writeOut)
  d.parseHeader(annotationFile, writeOut)

# Add an extra line to the vcf header to indicate the file used for
# performing dbsnp annotation.
  taskDescriptor = "##vcfPytools=annotated vcf file with "
  if options.dbsnpFile: taskDescriptor += "dbSNP file " + options.dbsnpFile
  elif options.hapmapFile:
    taskDescriptor += "hapmap file " + options.hapmapFile
    v.infoHeaderString["HM3"] = "##INFO=<ID=HM3,Number=0,Type=Flag,Description=\"Hapmap3.2 membership determined from file " + \
                                options.hapmapFile + "\">"
    v.infoHeaderString["HM3A"] = "##INFO=<ID=HM3A,Number=0,Type=Flag,Description=\"Hapmap3.2 membership (with different alleles)" + \
                                 ", determined from file " + options.hapmapFile + "\">"
  writeHeader(outputFile, v, False, taskDescriptor) # tools.py

# Annotate the vcf file.
  annotateVcf(v, d, outputFile, annotation)

# Check that the input files had the same list of reference sequences.
# If not, it is possible that there were some problems.
  checkReferenceSequenceLists(v.referenceSequenceList, d.referenceSequenceList) # tools.py

# Close the vcf files.
  v.closeVcf(options.vcfFile)
  d.closeVcf(annotationFile)

# End the program.
  return 0
