#!/usr/bin/env python

# Toy program to generate inverted index of word to line.
# Takes input text file on stdin and prints output index on stdout.

import os
import sys

words = {}

mainfile = sys.argv[1]
indexfile = sys.argv[1] + ".idx1"

main = open(mainfile)
index = open(indexfile, "w")

linenum = 0
for line in main:
    linenum += 1
    line = line.rstrip().lower().replace(".", "").replace(",", "").replace(";", "").replace("-", " ")
    for w in line.split(" "):
        if w:
            if w not in words:
                words[w] = set()
            words[w].add(linenum)

for w in sorted(words.keys()):
    index.write(f"{w}: {', '.join(str(i) for i in words[w])}\n")

open(os.path.splitext(sys.argv[1])[0] + ".idx2", "w")
open(sys.argv[1] + ".idx3", "w")
open(sys.argv[1] + ".idx4", "w")
open(sys.argv[1] + ".idx5", "w")
