#!/usr/bin/env python

import timeit

import edlib
import editdistance
import Levenshtein

with open('../../test_data/Enterobacteria_Phage_1/mutated_90_perc_oneline.fasta', 'r') as f:
    queryFull = f.readline()
print('Read query: ', len(queryFull) ,' characters.')

with open('../../test_data/Enterobacteria_Phage_1/Enterobacteria_phage_1_oneline.fa', 'r') as f:
    targetFull = f.readline()
print('Read target: ', len(targetFull) ,' characters.')

for seqLen in [30, 100, 1000, 10000, 50000]:
    query = queryFull[:seqLen]
    target = targetFull[:seqLen]
    numRuns = max(1000000000 // (seqLen**2), 1)

    print('Sequence length: ', seqLen)

    edlibTime = timeit.timeit(stmt="edlib.align(query, target)",
                              number=numRuns, globals=globals()) / numRuns
    print('Edlib: ', edlibTime)
    print(edlib.align(query, target))

    editdistanceTime = timeit.timeit(stmt="editdistance.eval(query, target)",
                                     number=numRuns, globals=globals()) / numRuns
    print('editdistance: ', editdistanceTime)

    levenshteinTime = timeit.timeit(stmt="Levenshtein.distance(query, target)",
                                     number=numRuns, globals=globals()) / numRuns
    print('levenshtein: ', levenshteinTime)

    print('edlib is %f times faster than editdistance.' % (editdistanceTime / edlibTime))
    print('edlib is %f times faster than Levenshtein.' % (levenshteinTime / edlibTime))
