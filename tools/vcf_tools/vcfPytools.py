#!/usr/bin/python

import os.path
import sys

__author__ = "alistair ward"
__version__ = "version 0.26"
__date__ = "february 2011"

def main():
  usage = "Usage: vcfPytools.py [tool] [options]\n\n" + \
          "Available tools:\n" + \
          "  annotate:\n\tAnnotate the vcf file with membership in other vcf files.\n" + \
          "  extract:\n\tExtract vcf records from a region.\n" + \
          "  filter:\n\tFilter the vcf file.\n" + \
          "  intersect:\n\tGenerate the intersection of two vcf files.\n" + \
          "  merge:\n\tMerge a list of vcf files.\n" + \
          "  multi:\n\tFind the intersections and unique fractions of multiple vcf files.\n" + \
          "  sort:\n\tSort a vcf file.\n" + \
          "  stats:\n\tGenerate statistics from a vcf file.\n" + \
          "  union:\n\tGenerate the union of two vcf files.\n" + \
          "  unique:\n\tGenerate the unique fraction from two vcf files.\n" + \
          "  validate:\n\tValidate the input vcf file.\n\n" + \
          "vcfPytools.py [tool] --help for information on a specific tool."

# Determine the requested tool.

  if len(sys.argv) > 1:
    tool = sys.argv[1]
  else:
    print >> sys.stderr, usage
    exit(1)

  if tool == "annotate":
    import annotate
    success = annotate.main()
  elif tool == "extract":
    import extract
    success = extract.main()
  elif tool == "filter":
    import filter
    success = filter.main()
  elif tool == "intersect":
    import intersect
    success = intersect.main()
  elif tool == "multi":
    import multi
    success = multi.main()
  elif tool == "merge":
    import merge
    success = merge.main()
  elif tool == "sort":
    import sort
    success = sort.main()
  elif tool == "stats":
    import stats
    success = stats.main()
  elif tool == "union":
    import union
    success = union.main()
  elif tool == "unique":
    import unique
    success = unique.main()
  elif tool == "test":
    import test
    success = test.main()
  elif tool == "validate":
    import validate
    success = validate.main()
  elif tool == "--help" or tool == "-h" or tool == "?":
    print >> sys.stderr, usage
  else:
    print >> sys.stderr, "Unknown tool: ",tool
    print >> sys.stderr, "\n", usage
    exit(1)

# If program completed properly, terminate.

  if success == 0: exit(0)

if __name__ == "__main__":
  main()
