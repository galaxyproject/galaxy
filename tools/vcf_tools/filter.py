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

def filterFail(text, file):
  print >> sys.stderr, text
  if file != None: os.remove(file)
  exit(1)

def main():

# Parse the command line options
  usage = "Usage: vcfPytools.py filter [options]"
  parser = optparse.OptionParser(usage = usage)
  parser.add_option("-i", "--in",
                    action="store", type="string",
                    dest="vcfFile", help="input vcf file")
  parser.add_option("-o", "--out",
                    action="store", type="string",
                    dest="output", help="output vcf file")
  parser.add_option("-q", "--quality",
                    action="store", type="int",
                    dest="quality", help="filter out SNPs with qualities lower than selected value")
  parser.add_option("-n", "--info",
                    action="append", type="string", nargs=3,
                    dest="infoFilters", help="filter based on entries in the info string")
  parser.add_option("-r", "--remove-genotypes",
                    action="store_true", default=False,
                    dest="removeGeno", help="remove the genotype strings from the vcf file")
  parser.add_option("-m", "--mark-as-pass",
                    action="store_true", default=False,
                    dest="markPass", help="Mark all records as having passed filters")

  (options, args) = parser.parse_args()

# Check that a single vcf file is given.
  if options.vcfFile == None:
    parser.print_help()
    print >> sys.stderr, "\nInput vcf file (-i, --input) is required for vcf filtering."
    exit(1)

# The --mark-as-pass option can only be used if no actual filters
# have been specified.
  if options.markPass and options.infoFilters:
    print >> sys.stderr, "--mark-as-pass cannot be used in conjunction with filters."
    exit(1)

# Set the output file to stdout if no output file was specified.
  outputFile, writeOut = setOutput(options.output) # tools.py

  v = vcf() # Define vcf object.

# Open the vcf file.
  v.openVcf(options.vcfFile)

# Read in the header information.
  v.parseHeader(options.vcfFile, writeOut)
  taskDescriptor = "##vcfPytools="
  if options.infoFilters:
    taskDescriptor += "filtered using the following filters: "
    for filter, value, logic in options.infoFilters: taskDescriptor += str(filter) + str(value) + ","
    taskDescriptor = taskDescriptor.rstrip(",")
  if options.markPass: taskDescriptor += "marked all records as PASS"
    
  writeHeader(outputFile, v, options.removeGeno, taskDescriptor)

# Check that specified filters from the info field are either integers or floats.
  if options.infoFilters:
    v.processInfo = True # Process the info string
    filters = {}
    filterValues = {}
    filterLogic = {}
    for filter, value, logic in options.infoFilters:
      filterName = str(filter) + str(value)
      if "-" in filter or "-" in value or "-" in logic:
        print >> sys.stderr, "\n--info (-n) requires three arguments, for example:"
        print >> sys.stderr, "\t--info DP 5 lt: filter records with DP less than (lt) 5.\n"
        print >> sys.stderr, "allowed logic arguments:\n\tgt: greater than\n\tlt: less than."
        print >> sys.stderr, "\nError in:", filter
        exit(1)
      if logic != "gt" and logic != "lt":
        print >> sys.stderr, "\nfilter logic not recognised."
        print >> sys.stderr, "allowed logic arguments:\n\tgt: greater than\n\tlt: less than."
        print >> sys.stderr, "\nError in:", filter
        exit(1)
      if v.infoHeaderTags.has_key(filter):
        if v.infoHeaderTags[filter][1].lower() == "integer":
          try:
            filters[filterName] = filter
            filterValues[filterName] = int(value)
            filterLogic[filterName] = logic
            #filterLogic[filterName] = logic
          except ValueError:
            text = "Filter " + filter + " requires an integer entry, not " + str(type(value))
            filterFail(text, options.output)

        if v.infoHeaderTags[filter][1].lower() == "float":
          try:
            filters[filterName] = filter
            filterValues[filterName] = float(value)
            filterLogic[filterName] = logic
            #filters[filterName] = float(value)
            #filterLogic[filterName] = logic
          except ValueError:
            text = "Filter " + filter + " requires an float entry, not " + str(type(value))
            filterFail(text, options.output)

      else:
        text = "Filter " + filter + " has no explanation in the header.  Unknown type for the entry."
        filterFail(text, options.output)

# Parse the vcf file and check if any of the filters are failed.  If
# so, build up a string of failed filters.
  while v.getRecord():
    filterString = ""

# Mark the record as "PASS" if --mark-as-pass was applied.
    if options.markPass: v.filters = "PASS"

# Check for quality filtering.
    if options.quality != None:
      if v.quality < options.quality:
        filterString = filterString + ";" + "Q" + str(options.quality) if filterString != "" else "Q" + str(options.quality)

# Check for filtering on info string filters.
    if options.infoFilters:
      for filterName, filter in filters.iteritems():
        value = filterValues[filterName]
        logic = filterLogic[filterName]
        if v.infoTags.has_key(filter):
          if type(value) == int:
            if logic == "lt" and int(v.infoTags[filter]) < value:
              filterString = filterString + ";" + filter + str(value) if filterString != "" else filter + str(value)
            if logic == "gt" and int(v.infoTags[filter]) > value:
              filterString = filterString + ";" + filter + str(value) if filterString != "" else filter + str(value)
          elif type(value) == float:
            if logic == "lt" and float(v.infoTags[filter]) < value:
              filterString = filterString + ";" + filter + str(value) if filterString != "" else filter + str(value)
            if logic == "gt" and float(v.infoTags[filter]) > value:
              filterString = filterString + ";" + filter + str(value) if filterString != "" else filter + str(value)

    filterString = "PASS" if filterString == "" else filterString
    v.filters = filterString
    record = v.buildRecord(options.removeGeno)
    outputFile.write(record)

# Close the vcf files.
  v.closeVcf(options.vcfFile)

# Terminate the program.
  return 0
