#!/usr/bin/python

import os.path
import sys
import vcfPytools
from vcfPytools import __version__

# Determine whether to output to a file or stdout.
def setOutput(output):
  if output == None:
    outputFile = sys.stdout
    writeOut = False
  else:
    output = os.path.abspath(output)
    outputFile = open(output, 'w')
    writeOut = True

  return outputFile, writeOut

# Determine which file has priority for writing out records.
def setVcfPriority(priorityFile, vcfFiles):
  if priorityFile == None: priority = 0
  elif priorityFile == vcfFiles[0]: priority = 1
  elif priorityFile == vcfFiles[1]: priority = 2
  elif priorityFile.lower() == "merge": priority = 3
  else:
    print >> sys.stderr, "vcf file give priority must be one of the two input vcf files or merge."
    exit(1)

  return priority

# If the union or intersection of two vcf files is being performed
# and the output vcf file is to contain the information from both
# files, the headers need to be merged to ensure that all info and
# format entries have an explanation.
def mergeHeaders(v1, v2, v3):

# If either file does not have a header, terminate the program.
# In order to merge the headers, the different fields must be
# checked to ensure the files are compatible.
  if not v1.hasHeader or not v2.hasHeader:
    print >> sys.stderr, "Both vcf files must have a header in order to merge data sets."
    exit(1)

  v3.infoHeaderTags = v1.infoHeaderTags.copy()
  v3.formatHeaderTags = v1.formatHeaderTags.copy()
  v3.numberDataSets = v1.numberDataSets
  v3.includedDataSets = v1.includedDataSets.copy()
  v3.headerText = v1.headerText
  v3.headerTitles = v1.headerTitles
  v3.infoHeaderString = v1.infoHeaderString.copy()
  v3.formatHeaderString = v1.formatHeaderString.copy()

# Merge the info field descriptions.
  for tag in v2.infoHeaderTags:
    if v1.infoHeaderTags.has_key(tag):
      if v1.infoHeaderTags[tag][0] != v2.infoHeaderTags[tag][0] or \
         v1.infoHeaderTags[tag][1] != v2.infoHeaderTags[tag][1]:
        print v1.infoHeaderTags[tag][0]
        print v1.infoHeaderTags[tag][1]
        print v1.infoHeaderTags[tag][2]
        print >> sys.stderr, "Input vcf files have different definitions for " + tag + " field."
        exit(1)
    else: v3.infoHeaderTags[tag] = v2.infoHeaderTags[tag]

# Merge the format field descriptions.
  for tag in v2.formatHeaderTags:
    if v1.formatHeaderTags.has_key(tag):
      if v1.formatHeaderTags[tag][0] != v2.formatHeaderTags[tag][0] or \
         v1.formatHeaderTags[tag][1] != v2.formatHeaderTags[tag][1]:
        print >> sys.stderr, "Input vcf files have different definitions for " + tag + " field."
        exit(1)
    else: v3.formatHeaderTags[tag] = v2.formatHeaderTags[tag]

# Now check to see if the vcf files contain information from multiple
# records themselves and create an ordered list in which the data
# will appear in the file.  For instance, of the first file has
# already got two sets of data and is being intersected with a file
# with one set of data, the order of data in the new vcf file will be
# the two sets from the first file followed by the second, e.g.
# AB=3/2/4, where the 3 and 2 are from the first file and the 4 is the
# value of AC from the second vcf.  The header will have a ##FILE for
# each of the three files, so the origin if the data can be recovered.
  if v1.numberDataSets == 0:
    v3.includedDataSets[v3.numberDataSets + 1] = v1.filename
    v3.numberDataSets += 1
  if v2.numberDataSets == 0:
    v3.includedDataSets[v3.numberDataSets + 1] = v2.filename
    v3.numberDataSets += 1
  else:
    for i in range(1, v2.numberDataSets + 1):
      v3.includedDataSets[v3.numberDataSets + 1] = v2.includedDataSets[i]
      v3.numberDataSets += 1

# If either of the input files contain multiple data sets (e.g. multiple
# vcf files have undergone intersection or union calculations and all
# information has been retained) and the priority isn't set to 'merge',
# terminate the program.  This is to ensure that the origin of the data
# doesn't get confused.
def checkDataSets(v1, v2):
  if v1.numberDataSets + v2.numberDataSets != 0:
    print >> sys.stderr, "\nERROR:"
    print >> sys.stderr, "input vcf file(s) contain data sets from multiple vcf files."
    print >> sys.stderr, "Further intersection or union operations must include --priority-file merge"
    print >> sys.stderr, "Other tools may be incompatible with this format."
    exit(1)

# Write the header to file.
def writeHeader (outputFile, v, removeGenotypes, taskDescriptor):
  if not v.hasHeader: 
    v.headerText = "##fileformat=VCFv4.0\n##source=vcfPytools " + __version__ + "\n"
    v.headerTitles = "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
  outputFile.write(v.headerText) if v.headerText != "" else None
  print >> outputFile, taskDescriptor
  for tag in v.infoHeaderString: print >> outputFile, v.infoHeaderString[tag]
  for tag in v.formatHeaderString: print >> outputFile, v.formatHeaderString[tag]

# Write out a list of files indicating which data set belongs to which file.
  if v.numberDataSets != 0:
    for i in range(1, v.numberDataSets + 1):
      print >> outputFile, "##FILE=<ID=" + str(i) + ",\"" + v.includedDataSets[i] + "\">"

  if removeGenotypes:
    line = v.headerTitles.rstrip("\n").split("\t")
    newHeaderTitles = line[0]
    for i in range(1,8):
      newHeaderTitles = newHeaderTitles + "\t" + line[i]
    newHeaderTitles = newHeaderTitles + "\n"
    outputFile.write( newHeaderTitles )
  else:
    outputFile.write( v.headerTitles )

# Check that the two reference sequence lists are identical.
# If there are a different number or order, the results may
# not be as expected.
def checkReferenceSequenceLists(list1, list2):
  errorMessage = False
  if len(list1) != len(list2):
    print >> sys.stderr, "WARNING: Input files contain a different number of reference sequences."
    errorMessage = True
  elif list1 != list2:
    print >> sys.stderr, "WARNING: Input files contain different or differently ordered reference sequences."
    errorMessage = True
  if errorMessage:
    print >> sys.stderr, "Results may not be as expected."
    print >> sys.stderr, "Ensure that input files have the same reference sequences in the same order."
    print >> sys.stderr, "Reference sequence lists observed were:\n\t", list1, "\n\t", list2

# Write out a vcf record to file.  The record written depends on the
# value of 'priority' and could therefore be the record from either
# of the vcf files, or a combination of them.

def writeVcfRecord(priority, v1, v2, outputFile):
  if priority == 0:
    if v1.quality >= v2.quality: outputFile.write(v1.record)
    else: outputFile.write(v2.record)
  elif priority == 1: outputFile.write(v1.record)
  elif priority == 2: outputFile.write(v2.record)
  elif priority == 3:

# Define the missing entry values (depends on the number of data sets
# in the file).
    info = ""
    missingEntry1 = missingEntry2 = "."
    for i in range(1, v1.numberDataSets): missingEntry1 += "/."
    for i in range(1, v2.numberDataSets): missingEntry2 += "/."
    secondList = v2.infoTags.copy()

# Build up the info field.
    for tag in v1.infoTags:
      if secondList.has_key(tag):
        if v1.infoHeaderTags[tag][1].lower() != "flag": info += tag + "=" + v1.infoTags[tag] + "/" + v2.infoTags[tag] + ";"
        del secondList[tag]
      else: 
        if v1.infoHeaderTags[tag][1].lower() != "flag": info += tag + "=" + v1.infoTags[tag] + "/" + missingEntry2 + ";"

# Now include the info tags that are not populated in the first vcf file.
    for tag in secondList:
      if v2.infoHeaderTags[tag][1].lower() != "flag": info += tag + "=" + missingEntry1 + "/" + v2.infoTags[tag] + ";"

# Build the complete record.
    info = info.rstrip(";")
    record = v1.referenceSequence + "\t" + str(v1.position) + "\t" + v1.rsid + "\t" + v1.ref + "\t" + \
             v1.alt + "/" + v2.alt + "\t" + v1.quality + "/" + v2.quality + "\t.\t" + info
    print >> outputFile, record
  else:
    print >> sys.sterr, "Unknown file priority."
    exit(1)
