#!/usr/bin/python

import os.path
import sys
import re

class vcf:
  def __init__(self):

# Header info.
    self.filename = ""
    self.hasHeader = True
    self.headerText = ""
    self.headerTitles = ""
    #self.headerInfoText = ""
    #self.headerFormatText = ""

# Store the info and format tags as well as the lines that describe
# them in a dictionary.
    self.numberDataSets = 0 
    self.includedDataSets = {}
    self.infoHeaderTags = {}
    self.infoHeaderString = {}
    self.formatHeaderTags = {}
    self.formatHeaderString = {}

# Genotype information.
    self.genotypes = False
    self.infoField = {}

# Reference sequence information.
    self.referenceSequences = {}
    self.referenceSequenceList = []
    self.referenceSequence = ""

# Record information.
    self.position = -1
    self.samplesList = []

# Determine which fields to process.
    self.processInfo = False
    self.processGenotypes = False
    self.dbsnpVcf = False
    self.hapmapVcf = False

# Open a vcf file.
  def openVcf(self, filename):
    if filename == "stdin":
      self.filehandle = sys.stdin
      self.filename = "stdin"
    else:
      try: self.filehandle = open(filename,"r")
      except IOError:
        print >> sys.stderr, "Failed to find file: ",filename
        exit(1)
      self.filename = os.path.abspath(filename)

# Parse the vcf header.
  def parseHeader(self, filename, writeOut):
    while self.getHeaderLine(filename, writeOut):
      continue

# Determine the type of information in the header line.
  def getHeaderLine(self, filename, writeOut):
    self.headerLine = self.filehandle.readline().rstrip("\n")
    if self.headerLine.startswith("##INFO"): success = self.headerInfo(writeOut, "info")
    elif self.headerLine.startswith("##FORMAT"): success = self.headerInfo(writeOut, "format")
    elif self.headerLine.startswith("##FILE"): success = self.headerFiles(writeOut)
    elif self.headerLine.startswith("##"): success = self.headerAdditional()
    elif self.headerLine.startswith("#"): success = self.headerTitleString(filename, writeOut)
    else: success = self.noHeader(filename, writeOut)

    return success

# Read information on an info field from the header line.
  def headerInfo(self, writeOut, lineType):
    tag = self.headerLine.split("=",1)
    tagID = (tag[1].split("ID=",1))[1].split(",",1)

# Check if this info field has already been defined.
    if (lineType == "info" and self.infoHeaderTags.has_key(tagID[0])) or (lineType == "format" and self.formatHeaderTags.has_key(tagID[0])):
      print >> sys.stderr, "Info tag \"", tagID[0], "\" is defined multiple times in the header."
      exit(1)

# Determine the number of entries, entry type and description.
    tagNumber = (tagID[1].split("Number=",1))[1].split(",",1)
    tagType = (tagNumber[1].split("Type=",1))[1].split(",",1)
    try: tagDescription = ( ( (tagType[1].split("Description=\"",1))[1] ).split("\">") )[0]
    except IndexError: tagDescription = ""
    tagID = tagID[0]; tagNumber = tagNumber[0]; tagType = tagType[0]

# Check that the number of fields associated with the tag is either
# an integer or a '.' to indicate variable number of entries.
    if tagNumber == ".": tagNumber = "variable"
    else:
      try: tagNumber = int(tagNumber)
      except ValueError:
        print >> sys.stderr, "\nError parsing header.  Problem with info tag:", tagID
        print >> sys.stderr, "Number of fields associated with this tag is not an integer or '.'"
        exit(1)

    if lineType == "info":
      self.infoHeaderTags[tagID] = tagNumber, tagType, tagDescription
      self.infoHeaderString[tagID] = self.headerLine
    if lineType == "format":
      self.formatHeaderTags[tagID] = tagNumber, tagType, tagDescription
      self.formatHeaderString[tagID] = self.headerLine

    return True

# Check to see if the records contain information from multiple different
# sources.  If vcfPytools has been used to find the intersection or union
# of two vcf files, the records may have been merged to keep all the
# information available.  If this is the case, there will be a ##FILE line
# for each set of information in the file.  The order of these files needs
# to be maintained.
  def headerFiles(self, writeOut):
    fileID = (self.headerLine.split("ID=",1))[1].split(",",1)
    filename = fileID[1].split("\"",2)[1]
    try: fileID = int(fileID[0])
    except ValueError:
      print >> sys.stderr, "File ID in ##FILE entry must be an integer."
      print >> sys.stderr, self.headerLine
      exit(1)
    if self.includedDataSets.has_key(fileID):
      print >> sys.stderr, "\nERROR: file " + self.filename
      print >> sys.stderr, "Multiple files in the ##FILE list have identical ID values."
      exit(1)
    self.includedDataSets[fileID] = filename

# Set the number of files with information in this vcf file.
    if fileID > self.numberDataSets: self.numberDataSets = fileID

    return True

# Read additional information contained in the header.
  def headerAdditional(self):
    self.headerText += self.headerLine + "\n"

    return True

# Read in the column titles to check that all standard fields
# are present and read in all the samples.
  def headerTitleString(self, filename, writeOut):
    self.headerTitles = self.headerLine + "\n"

# Strip the end of line character from the last infoFields entry.
    infoFields = self.headerLine.split("\t")
    if len(infoFields) > 8:
#      if len(infoFields) - 9 == 1 and writeOut: print >> sys.stdout, len(infoFields) - 9, " sample present in vcf file: ", filename
#      elif writeOut: print >> sys.stdout, len(infoFields) - 9, " samples present in vcf file: ", filename
      self.samplesList = infoFields[9:]
      self.genotypes = True
    elif len(infoFields) == 8:
      if writeOut: print >> sys.stdout, "No samples present in the header.  No genotype information available."
    else:
      print self.headerLine, len(infoFields)
      print >> sys.stderr, "Not all vcf standard fields are available."
      exit(1)

    return False

# If there is no header in the vcf file, close and reopen the
# file so that the first line is avaiable for parsing as a 
# vcf record.
  def noHeader(self, filename, writeOut):
    if writeOut: print >> sys.stdout, "No header lines present in", filename
    self.hasHeader = False
    self.closeVcf(filename)
    self.openVcf(filename)

    return False

# Check that info fields exist.
  def checkInfoFields(self, tag):
    if self.infoHeaderTags.has_key(tag) == False:
      print >> sys.stderr, "Info tag \"", tag, "\" does not exist in the header."
      exit(1)

# Get the next line of information from the vcf file.
  def getRecord(self):
    self.record = self.filehandle.readline()
    if not self.record: return False

# Set up and execute a regular expression match.
    recordRe = re.compile(r"^(\S+)\t(\d+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)\t(\S+)(\n|\t.+)$")
    #recordRe = re.compile(r"^(\S+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)(\n|\s+.+)$")
    recordMatch = recordRe.match(self.record)
    if recordMatch == None:
      print >> sys.stderr, "Unable to resolve vcf record.\n"
      print >> sys.stderr, self.record
      exit(1)

    self.referenceSequence = recordMatch.group(1)
    try: self.position = int(recordMatch.group(2))
    except ValueError:
      text = "variant position is not an integer"
      self.generalError(text, "", None)
    self.rsid       = recordMatch.group(3)
    self.ref        = recordMatch.group(4)
    self.alt        = recordMatch.group(5)
    self.quality    = recordMatch.group(6)
    self.filters    = recordMatch.group(7)
    self.info       = recordMatch.group(8)
    self.genotypeString = recordMatch.group(9)
    self.infoTags   = {}

# Check that the quality is an integer or a float.  If not, set the quality
# to zero.
    try: self.quality = float(self.quality)
    except ValueError: self.quality = float(0.)

# If recordMatch.group(9) is not the end of line character, there is
# genotype information with this record.
    if self.genotypeString != "\n": self.hasGenotypes = True
    else: self.hasGenotypes = False

# Add the reference sequence to the dictionary.  If it didn't previously
# exist append the reference sequence to the end of the list as well. 
# This ensures that the order in which the reference sequences appeared
# in the header can be preserved.
    if self.referenceSequence not in self.referenceSequences:
      self.referenceSequences[self.referenceSequence] = True
      self.referenceSequenceList.append(self.referenceSequence)

# Check for multiple alternate alleles.
    self.alternateAlleles = self.alt.split(",")
    self.numberAlternateAlleles = len(self.alternateAlleles)

# If required, process the info and genotypes.
    if self.processInfo: self.processInfoFields()
    if self.processGenotypes and self.hasGenotypes: self.processGenotypeFields()

    return True

# Process the info string.
  def processInfoFields(self):

# First break the info string into its constituent elements.
    infoEntries = self.info.split(";")

# As long as some info fields exist, place them into a dictionary.
    for entry in infoEntries:
      infoEntry = entry.split("=")

# If the entry is a flag, there will be no equals and the length of
# infoEntry will be 1.  In this case, set the dictionary entry to the
# whole entry.  If the vcf file has undergone a union or intersection
# operation and contains the information from multiple files, this may
# be a '/' seperate list of flags and so cannot be set to a Boolean value
# yet.
      if len(infoEntry) == 1: self.infoTags[infoEntry[0]] = infoEntry[0]
      elif len(infoEntry) > 1: self.infoTags[infoEntry[0]] = infoEntry[1]

# Process the genotype formats and values.
  def processGenotypeFields(self):
    genotypeEntries = self.genotypeString.split("\t")
    self.genotypeFormatString = genotypeEntries[1]
    self.genotypes = list(genotypeEntries[2:])
    self.genotypeFormats = {}
    self.genotypeFields = {}
    self.genotypeFormats = self.genotypeFormatString.split(":")

# Check that the number of genotype fields is equal to the number of samples
    if len(self.samplesList) != len(self.genotypes):
      text = "The number of genotypes is different to the number of samples"
      self.generalError(text, "", "")

# Add the genotype information to a dictionary.
    for i in range( len(self.samplesList) ):
      genotypeInfo = self.genotypes[i].split(":")
      self.genotypeFields[ self.samplesList[i] ] = {}

# Check that there are as many fields as in the format field.  If not, this must
# be because the information is not known.  In this case, it is permitted that
# the genotype information is either . or ./.
      if genotypeInfo[0] == "./." or genotypeInfo[0] == "." and len(self.genotypeFormats) != len(genotypeInfo): 
        self.genotypeFields[ self.samplesList[i] ] = "."
      else:
        if len(self.genotypeFormats) != len(genotypeInfo):
          text = "The number of genotype fields is different to the number specified in the format string"
          self.generalError(text, "sample", self.samplesList[i])

        for j in range( len(self.genotypeFormats) ): self.genotypeFields[ self.samplesList[i] ][ self.genotypeFormats[j] ] = genotypeInfo[j]

# Parse through the vcf file until the correct reference sequence is
# encountered and the position is greater than or equal to that requested.
  def parseVcf(self, referenceSequence, position, writeOut, outputFile):
    success = True
    if self.referenceSequence != referenceSequence:
      while self.referenceSequence != referenceSequence and success:
        if writeOut: outputFile.write(self.record)
        success = self.getRecord()

    while self.referenceSequence == referenceSequence and self.position < position and success:
      if writeOut: outputFile.write(self.record)
      success = self.getRecord()

    return success

# Get the information for a specific info tag.  Also check that it contains
# the correct number and type of entries.
  def getInfo(self, tag):
    result = []

# Check if the tag exists in the header information.  If so,
# determine the number and type of entries asscoiated with this
# tag.
    if self.infoHeaderTags.has_key(tag):
      infoNumber = self.infoHeaderTags[tag][0]
      infoType = self.infoHeaderTags[tag][1]
      numberValues = infoNumber

# First check that the tag exists in the information string.  Then split
# the entry on commas.  For flag entries, do not perform the split.
      if self.infoTags.has_key(tag):
        if numberValues == 0 and infoType == "Flag": result = True
        elif numberValues != 0 and infoType == "Flag":
          print >> sys.stderr, "ERROR"
          exit(1)
        else:
          fields = self.infoTags[tag].split(",")
          if len(fields) != numberValues:
            text = "Unexpected number of entries"
            self.generalError(text, "information tag", tag)

          for i in range(infoNumber):
            try: result.append(fields[i])
            except IndexError:
              text = "Insufficient values. Expected: " + self.infoHeaderTags[tag][0]
              self.generalError(text, "tag:", tag)
      else: numberValues = 0

    else:
      text = "information field does not have a definition in the header"
      self.generalError(text, "tag", tag)

    return numberValues, infoType, result

# Get the genotype information.
  def getGenotypeInfo(self, sample, tag):
    result = []
    if self.formatHeaderTags.has_key(tag):
      infoNumber = self.formatHeaderTags[tag][0]
      infoType = self.formatHeaderTags[tag][1]
      numberValues = infoNumber

      if self.genotypeFields[sample] == "." and len(self.genotypeFields[sample]) == 1:
        numberValues = 0
        result = "."
      else:
        if self.genotypeFields[sample].has_key(tag):
          if tag == "GT":
            if len(self.genotypeFields[sample][tag]) != 3 and len(self.genotypeFields[sample][tag]) != 1:
              text = "Unexected number of characters in genotype (GT) field"
              self.generalError(text, "sample", sample)

# If a diploid call, check whether or not the genotype is phased.
            elif len(self.genotypeFields[sample][tag]) == 3:
              self.phased = True if self.genotypeFields[sample][tag][1] == "|" else False
              result.append( self.genotypeFields[sample][tag][0] )
              result.append( self.genotypeFields[sample][tag][2] )
            elif len(self.genotypeFields[sample][tag]) == 3:
              result.append( self.genotypeFields[sample][tag][0] )
          else:
            fields = self.genotypeFields[sample][tag].split(",")
            if len(fields) != numberValues:
              text = "Unexpected number of characters in " + tag + " field"
              self.generalError(text, "sample", sample)

            for i in range(infoNumber): result.append(fields[i])
    else:
      text = "genotype field does not have a definition in the header"
      self.generalError(text, "tag", tag)

    return numberValues, result

# Parse the dbsnp entry.  If the entry conforms to the required variant type,
# return the dbsnp rsid value, otherwise ".".
  def getDbsnpInfo(self):

# First check that the variant class (VC) is listed as SNP.
    vc = self.info.split("VC=",1)
    if vc[1].find(";") != -1: snp = vc[1].split(";",1) 
    else:
      snp = []
      snp.append(vc[1])

    if snp[0].lower() == "snp": rsid = self.rsid
    else: rsid = "."

    return rsid

# Build a new vcf record.
  def buildRecord(self, removeGenotypes):
    record = self.referenceSequence + "\t" + \
                str(self.position) + "\t" + \
                self.rsid + "\t" + \
                self.ref + "\t" + \
                self.alt + "\t" + \
                str(self.quality) + "\t" + \
                self.filters + "\t" + \
                self.info

    if self.hasGenotypes and not removeGenotypes: record += self.genotypeString

    record += "\n"

    return record

# Close the vcf file.
  def closeVcf(self, filename):
    self.filehandle.close()

# Define error messages for different handled errors.
  def generalError(self, text, field, fieldValue):
    print >> sys.stderr, "\nError encountered when attempting to read:"
    print >> sys.stderr, "\treference sequence :\t", self.referenceSequence
    print >> sys.stderr, "\tposition :\t\t", self.position
    if field != "": print >> sys.stderr, "\t", field, ":\t", fieldValue
    print >> sys.stderr,  "\n", text
    exit(1)
