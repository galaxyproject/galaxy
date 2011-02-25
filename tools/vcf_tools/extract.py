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

def main():

# Parse the command line options
  usage = "Usage: vcfPytools.py extract [options]"
  parser = optparse.OptionParser(usage = usage)
  parser.add_option("-i", "--in",
                    action="store", type="string",
                    dest="vcfFile", help="input vcf file (stdin for piped vcf)")
  parser.add_option("-o", "--out",
                    action="store", type="string",
                    dest="output", help="output validation file")
  parser.add_option("-s", "--reference-sequence",
                    action="store", type="string",
                    dest="referenceSequence", help="extract records from this reference sequence")
  parser.add_option("-r", "--region",
                    action="store", type="string",
                    dest="region", help="extract records from this region")
  parser.add_option("-q", "--keep-quality",
                    action="append", type="string", nargs=2,
                    dest="keepQuality", help="keep records containing this quality")
  parser.add_option("-k", "--keep-info",
                    action="append", type="string",
                    dest="infoKeep", help="keep records containing this info field")
  parser.add_option("-d", "--discard-info",
                    action="append", type="string",
                    dest="infoDiscard", help="discard records containing this info field")
  parser.add_option("-p", "--pass-filter",
                    action="store_true", default=False,
                    dest="passFilter", help="discard records whose filter field is not PASS")

  (options, args) = parser.parse_args()

# Check that a vcf file is given.
  if options.vcfFile == None:
    parser.print_help()
    print >> sys.stderr, "\nInput vcf file (--in, -i) is required."
    exit(1)

# Check that either a reference sequence or region is specified,
# but not both if not dealing with info fields.
  if not options.infoKeep and not options.infoDiscard and not options.passFilter and not options.keepQuality:
    if not options.referenceSequence and not options.region:
      parser.print_help()
      print >> sys.stderr, "\nA region (--region, -r) or reference sequence (--reference-sequence, -s) must be supplied"
      print >> sys.stderr, "if not extracting records based on info strings."
      exit(1)
  if options.referenceSequence and options.region:
    parser.print_help()
    print >> sys.stderr, "\nEither a region (--region, -r) or reference sequence (--reference-sequence, -s) can be supplied, but not both."
    exit(1)

# If a region was supplied, check the format.
  if options.region:
    if options.region.find(":") == -1 or options.region.find("..") == -1:
      print >> sys.stderr, "\nIncorrect format for region string.  Required: ref:start..end."
      exit(1)
    regionList = options.region.split(":",1)
    referenceSequence = regionList[0]
    try: start = int(regionList[1].split("..")[0])
    except ValueError:
      print >> sys.stderr, "region start coordinate is not an integer"
      exit(1)
    try: end = int(regionList[1].split("..")[1])
    except ValueError:
      print >> sys.stderr, "region end coordinate is not an integer"
      exit(1)

# Ensure that discard-info and keep-info haven't both been defined.
  if options.infoKeep and options.infoDiscard:
    print >> sys.stderr, "Cannot specify fields to keep and discard simultaneously."
    exit(1)

# If the --keep-quality argument is used, check that a value and a logical
# argument are supplied and that the logical argument is valid.

  if options.keepQuality:
    for value, logic in options.keepQuality:
      if logic != "eq" and logic != "lt" and logic != "le" and logic != "gt" and logic != "ge":
        print >> sys.stderr, "Error with --keep-quality (-q) argument.  Must take the following form:"
        print >> sys.stderr, "\npython vcfPytools extract --in <VCF> --keep-quality <value> <logic>"
        print >> sys.stderr, "\nwhere logic is one of: eq, le, lt, ge or gt"
        exit(1)
    try: qualityValue = float(value)
    except ValueError:
      print >> sys.stderr, "Error with --keep-quality (-q) argument.  Must take the following form:"
      print >> sys.stderr, "Quality value must be an integer or float value."
      exit(1)
    qualityLogic = logic

# Set the output file to stdout if no output file was specified.
  outputFile, writeOut = setOutput(options.output)

  v = vcf() # Define vcf object.

# Set process info to True if info strings need to be parsed.
  if options.infoKeep or options.infoDiscard: v.processInfo = True

# Open the file.
  v.openVcf(options.vcfFile)

# Read in the header information.
  v.parseHeader(options.vcfFile, writeOut)
  taskDescriptor = "##vcfPytools=extract data"
  writeHeader(outputFile, v, False, taskDescriptor) # tools.py

# Read through all the entries and write out records in the correct
# reference sequence.
  while v.getRecord():
    writeRecord = True
    if options.referenceSequence and v.referenceSequence != options.referenceSequence: writeRecord = False
    elif options.region:
      if v.referenceSequence != referenceSequence: writeRecord = False
      elif v.position < start or v.position > end: writeRecord = False

# Only consider these fields if the record is contained within the
# specified region.
    if options.infoKeep and writeRecord:
      for tag in options.infoKeep:
        if v.infoTags.has_key(tag):
          writeRecord = True
          break
        if not v.infoTags.has_key(tag): writeRecord = False
    if options.infoDiscard and writeRecord:
      for tag in options.infoDiscard:
        if v.infoTags.has_key(tag): writeRecord = False
    if options.passFilter and v.filters != "PASS" and writeRecord: writeRecord = False
    if options.keepQuality:
      if qualityLogic == "eq" and v.quality != qualityValue: writeRecord = False
      if qualityLogic == "le" and v.quality > qualityValue: writeRecord = False
      if qualityLogic == "lt" and v.quality >= qualityValue: writeRecord = False
      if qualityLogic == "ge" and v.quality < qualityValue: writeRecord = False
      if qualityLogic == "gt" and v.quality <= qualityValue: writeRecord = False

    if writeRecord: outputFile.write(v.record)

# Close the file.
  v.closeVcf(options.vcfFile)

# Terminate the program cleanly.
  return 0
