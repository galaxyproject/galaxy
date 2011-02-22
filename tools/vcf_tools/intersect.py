#!/usr/bin/python

import os.path
import sys
import optparse

import bedClass
from bedClass import *

import vcfClass
from vcfClass import *

import tools
from tools import *

if __name__ == "__main__":
  main()

# Intersect two vcf files.  It is assumed that the two files are
# sorted by genomic coordinates and the reference sequences are
# in the same order.
def intersectVcf(v1, v2, priority, outputFile):
  success1 = v1.getRecord()
  success2 = v2.getRecord()
  currentReferenceSequence = v1.referenceSequence

# As soon as the end of either file is reached, there can be no
# more intersecting SNPs, so terminate.
  while success1 and success2:
    if v1.referenceSequence == v2.referenceSequence and v1.referenceSequence == currentReferenceSequence:
      if v1.position == v2.position:
        writeVcfRecord(priority, v1, v2, outputFile)
        success1 = v1.getRecord()
        success2 = v2.getRecord()
      elif v2.position > v1.position: success1 = v1.parseVcf(v2.referenceSequence, v2.position, False, None)
      elif v1.position > v2.position: success2 = v2.parseVcf(v1.referenceSequence, v1.position, False, None)
    else:
      if v1.referenceSequence == currentReferenceSequence: success1 = v1.parseVcf(v2.referenceSequence, v2.position, False, None)
      elif v2.referenceSequence == currentReferenceSequence: success2 = v2.parseVcf(v1.referenceSequence, v1.position, False, None)

# If the last record for a reference sequence is the same for both vcf
# files, they will both have referenceSequences different from the
# current reference sequence.  Change the reference sequence to reflect
# this and proceed.
      else:
        if v1.referenceSequence != v2.referenceSequence:
          print >> sys.stderr, "ERROR: Reference sequences for both files are unexpectedly different."
          print >> sys.stderr, "Check that both files contain records for the following reference sequences:"
          print >> sys.stderr, "\t", v1.referenceSequence, " and ", v2.referenceSequence
          exit(1)
      currentReferenceSequence = v1.referenceSequence

# Intersect a vcf file and a bed file.  It is assumed that the 
# two files are sorted by genomic coordinates and the reference
# sequences are in the same order.
def intersectVcfBed(v, b, outputFile):
  successb = b.getRecord()
  successv = v.getRecord()
  currentReferenceSequence = v.referenceSequence

# As soon as the end of the first file is reached, there are no
# more intersections and the program can terminate.
  while successv:
    if v.referenceSequence == b.referenceSequence:
      if v.position < b.start: successv = v.parseVcf(b.referenceSequence, b.start, False, None)
      elif v.position > b.end: successb = b.parseBed(v.referenceSequence, v.position)
      else:
        outputFile.write(v.record)
        successv = v.getRecord()
    else:
      if v.referenceSequence == currentReferenceSequence: successv = v.parseVcf(b.referenceSequence, b.start, False, None)
      if b.referenceSequence == currentReferenceSequence: successb = b.parseBed(v.referenceSequence, v.position)
      currentReferenceSequence = v.referenceSequence

def main():

# Parse the command line options
  usage = "Usage: vcfPytools.py intersect [options]"
  parser = optparse.OptionParser(usage = usage)
  parser.add_option("-i", "--in",
                    action="append", type="string",
                    dest="vcfFiles", help="input vcf files")
  parser.add_option("-b", "--bed",
                    action="store", type="string",
                    dest="bedFile", help="input bed vcf file")
  parser.add_option("-o", "--out",
                    action="store", type="string",
                    dest="output", help="output vcf file")
  parser.add_option("-f", "--priority-file",
                    action="store", type="string",
                    dest="priorityFile", help="output records from this vcf file")

  (options, args) = parser.parse_args()

# Check that a single  vcf file is given.
  if options.vcfFiles == None:
    parser.print_help()
    print >> sys.stderr, "\nAt least one vcf file (--in, -i) is required for performing intersection."
    exit(1)
  elif len(options.vcfFiles) > 2:
    parser.print_help()
    print >> sys.stderr, "\nAt most, two vcf files (--in, -i) can be submitted for performing intersection."
    exit(1)
  elif len(options.vcfFiles) == 1 and not options.bedFile:
    parser.print_help()
    print >> sys.stderr, "\nIf only one vcf file (--in, -i) is specified, a bed file is also required for performing intersection."
    exit(1)

# Set the output file to stdout if no output file was specified.
  outputFile, writeOut = setOutput(options.output) # tools.py

# If intersecting with a bed file, call the bed intersection routine.
  if options.bedFile:
    v = vcf() # Define vcf object.
    b = bed() # Define bed object.

# Open the files.
    v.openVcf(options.vcfFiles[0])
    b.openBed(options.bedFile)

# Read in the header information.
    v.parseHeader(options.vcfFiles[0], writeOut)
    taskDescriptor = "##vcfPytools=intersect " + options.vcfFiles[0] + ", " + options.bedFile
    writeHeader(outputFile, v, False, taskDescriptor) # tools.py

# Intersect the vcf file with the bed file.
    intersectVcfBed(v, b, outputFile)

# Check that the input files had the same list of reference sequences.
# If not, it is possible that there were some problems.
    checkReferenceSequenceLists(v.referenceSequenceList, b.referenceSequenceList) # tools.py

# Close the files.
    v.closeVcf(options.vcfFiles[0])
    b.closeBed(options.bedFile)

  else:
    priority = setVcfPriority(options.priorityFile, options.vcfFiles)
    v1 = vcf() # Define vcf object.
    v2 = vcf() # Define vcf object.

# Open the vcf files.
    v1.openVcf(options.vcfFiles[0])
    v2.openVcf(options.vcfFiles[1])

# Read in the header information.
    v1.parseHeader(options.vcfFiles[0], writeOut)
    v2.parseHeader(options.vcfFiles[1], writeOut)
    if priority == 3:
      v3 = vcf() # Generate a new vcf object that will contain the header information of the new file.
      mergeHeaders(v1, v2, v3) # tools.py
      v1.processInfo = True
      v2.processInfo = True
    else: checkDataSets(v1, v2)
    
    #print v1.samplesList
    #print v2.samplesList

# Check that the header for the two files contain the same samples.
    if v1.samplesList != v2.samplesList:
      print >> sys.stderr, "vcf files contain different samples (or sample order)."
      exit(1)
    else:
      taskDescriptor = "##vcfPytools=intersect " + v1.filename + ", " + v2.filename
      if priority == 3: writeHeader(outputFile, v3, False, taskDescriptor)
      elif (priority == 2 and v2.hasHeader) or not v1.hasHeader: writeHeader(outputFile, v2, False, taskDescriptor) # tools.py
      else: writeHeader(outputFile, v1, False, taskDescriptor) # tools.py

# Intersect the two vcf files.
    intersectVcf(v1, v2, priority, outputFile)

# Check that the input files had the same list of reference sequences.
# If not, it is possible that there were some problems.
    checkReferenceSequenceLists(v1.referenceSequenceList, v2.referenceSequenceList) # tools.py

# Close the vcf files.
    v1.closeVcf(options.vcfFiles[0])
    v2.closeVcf(options.vcfFiles[1])

# End the program.
  return 0
