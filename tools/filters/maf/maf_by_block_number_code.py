#!/usr/bin/env python2.4
#Dan Blankenberg
"""
Returns valid column numbers, defaulting to 1 for text files
"""

def get_columns(dataset):
    if not dataset.metadata.columns: return [("1", "1", True)]
    return map(lambda col: (str(col), str(col), False), range(1, dataset.metadata.columns+1))
