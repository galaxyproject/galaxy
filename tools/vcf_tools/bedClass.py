#!/usr/bin/python

import os.path
import sys

class bed:
  def __init__(self):
    self.numberTargets = 0
    self.referenceSequences = {}
    self.referenceSequenceList = []

  def openBed(self, filename):
    if filename == "stdin": self.filehandle = sys.stdin
    else:
      try: self.filehandle = open(filename,"r")
      except IOError:
        print >> sys.stderr, "Failed to find file: ",filename
        exit(1)

# Get a bed record.
  def getRecord(self):
    self.record = self.filehandle.readline()
    if not self.record: return False

    self.numberTargets = self.numberTargets + 1
    self.ref = ""
    self.start = 0
    self.end = 0

# bed file should be 0-based, half-open, so the start coordinate
# must be that in the bed file plus one.
    entries = self.record.rstrip("\n").split("\t")
    self.referenceSequence = entries[0]

# Add the reference sequence to the dictionary.  If it didn't previously
# exist append the reference sequence to the end of the list as well. 
# This ensures that the order in which the reference sequences appeared
# in the header can be preserved.
    if self.referenceSequence not in self.referenceSequences:
      self.referenceSequences[self.referenceSequence] = True
      self.referenceSequenceList.append(self.referenceSequence)

    try: self.start = int(entries[1]) + 1
    except:
      text = "start position need is not an integer"
      self.generalError(text, "start", entries[1])

    try: self.end = int(entries[2])
    except:
      text = "end position need is not an integer"
      self.generalError(text, "end", entries[2])

# Check that the record is a valid interval.
    if self.end - self.start < 0:
      print >> sys.stderr, "Invalid target interval:\n\t", self.record
      exit(1)

    return True

# Parse through the bed file until the correct reference sequence is
# encountered and the end position is greater than or equal to that requested.
  def parseBed(self, referenceSequence, position):
    success = True
    if self.referenceSequence != referenceSequence:
      while self.referenceSequence != referenceSequence and success: success = self.getRecord()

    while self.referenceSequence == referenceSequence and self.end < position and success: success = self.getRecord()

    return success

# Close the bed file.
  def closeBed(self, filename):
    self.filehandle.close()

# Define error messages for different handled errors.
  def generalError(self, text, field, fieldValue):
    print >> sys.stderr, "\nError encountered when attempting to read:"
    if field != "": print >> sys.stderr, "\t", field, ":             ", fieldValue
    print >> sys.stderr,  "\n", text
    exit(1)
