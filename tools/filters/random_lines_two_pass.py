#!/usr/bin/env python
# Dan Blankenberg
#
# Selects N random lines from a file and outputs to another file, maintaining original line order
# allows specifying a seed
# does two passes to determine line offsets/count, and then to output contents
#
# Modified by Praveen Kumar, 2018
# In this version, user has an option to specify second file with lines to ignore from the main input.
#


from __future__ import print_function

import optparse
import random
from math import (
    ceil,
    log
)

def randint(a, b):
    return a + int(random.random() * (b + 1 - a))


def sample(population, k):
    """Copied straight from python 2.7."""

    # Sampling without replacement entails tracking either potential
    # selections (the pool) in a list or previous selections in a set.

    # When the number of selections is small compared to the
    # population, then tracking selections is efficient, requiring
    # only a small set and an occasional reselection.  For
    # a larger number of selections, the pool tracking method is
    # preferred since the list takes less space than the
    # set and it doesn't suffer from frequent reselections.

    n = len(population)
    if not 0 <= k <= n:
        raise ValueError("sample larger than population")
    result = [None] * k
    setsize = 21  # size of a small set minus size of an empty list
    if k > 5:
        setsize += 4 ** ceil(log(k * 3, 4))  # table size for big sets
    if n <= setsize or hasattr(population, "keys"):
        # An n-length list is smaller than a k-length set, or this is a
        # mapping type so the other algorithm wouldn't work.
        pool = list(population)
        for i in range(k):         # invariant:  non-selected at [0,n-i)
            j = int(random.random() * (n - i))
            result[i] = pool[j]
            pool[j] = pool[n - i - 1]   # move non-selected item into vacancy
    else:
        try:
            selected = set()
            selected_add = selected.add
            for i in range(k):
                j = int(random.random() * n)
                while j in selected:
                    j = int(random.random() * n)
                selected_add(j)
                result[i] = population[j]
        except (TypeError, KeyError):   # handle (at least) sets
            if isinstance(population, list):
                raise
            return sample(tuple(population), k)
    return result


def get_random_by_subtraction(line_offsets, num_lines):
    while len(line_offsets) > num_lines:
        del line_offsets[randint(0, len(line_offsets) - 1)]
    return line_offsets


def get_random_by_sample(line_offsets, num_lines):
    line_offsets = sample(line_offsets, num_lines)
    line_offsets.sort()
    return line_offsets


def get_random(line_offsets, num_lines):
    if num_lines > (len(line_offsets) / 2):
        return get_random_by_subtraction(line_offsets, num_lines)
    else:
        return get_random_by_sample(line_offsets, num_lines)


def __main__():
    parser = optparse.OptionParser()
    parser.add_option('-s', '--seed', dest='seed', action='store', type="string", default=None, help='Set the random seed.')
    (options, args) = parser.parse_args()
    
    if len(args) == 3:
        run_mode = "no_neg_file"
    elif len(args) == 4:
        run_mode = "neg_file_mode_1"
    elif len(args) == 5:
        run_mode = "neg_file_mode_2"
    else:
        print("Invalid command line specified.")
        exit()
    
    with open(args[0], 'rb') as input, open(args[1], 'wb') as output:
        if run_mode == "no_neg_file":
            num_lines = int(args[2])
            assert num_lines > 0, "You must select at least one line."
        elif run_mode == "neg_file_mode_1":
            num_lines = int(args[2])
            if args[3].strip() == "num_from_neg_file":
                assert num_lines > 0, "You must select at least one line."
        elif run_mode == "neg_file_mode_2":
            num_lines = int(args[2])
        else:
            num_lines = int(args[2])
            assert num_lines > 0, "You must select at least one line."
        
        if options.seed is not None:
            seed_int = int("".join([str(ord(_)) for _ in options.seed]))
            try:
                # Select version 1, which results in the same seed for python 2 and 3
                random.seed(seed_int, version=1)
            except TypeError:
                # We're on python 2.X, which doesn't know the version argument
                random.seed(seed_int)
        
        if run_mode == "neg_file_mode_1" or run_mode == "neg_file_mode_2":
            if run_mode == "neg_file_mode_1":
                neg_file_input = open(args[3], 'r').readlines()
            elif run_mode == "neg_file_mode_2":
                neg_file_input = open(args[4], 'r').readlines()
                num_lines = len(neg_file_input) + num_lines
            neg_list = []
            for each in neg_file_input:
                neg_list.append(each.strip())
            original_input = []
            for each in input.readlines():
                original_input.append(each.strip())
            y = [x for x in original_input if x not in neg_list]
            tmp_file = open("tmp_file.txt", "w")
            for each in y:
                tmp_file.write(each + "\n")
            tmp_file.close()
            input.close()
            input = open("tmp_file.txt", "r")
        
        
        # get line offsets
        line_offsets = []
        teller = input.tell
        readliner = input.readline
        appender = line_offsets.append
        while True:
            offset = teller()
            if readliner():
                appender(offset)
            else:
                break

        total_lines = len(line_offsets)
        assert num_lines <= total_lines, "Error: asked to select more lines (%i) than there were in the file (%i)." % (num_lines, total_lines)

        # get random line offsets
        line_offsets = get_random(line_offsets, num_lines)

        # write out random lines
        seeker = input.seek
        writer = output.write
        for line_offset in line_offsets:
            seeker(line_offset)
            writer(readliner())
    print("Kept %i of %i total lines." % (num_lines, total_lines))
    if options.seed is not None:
        print('Used random seed of "%s".' % options.seed)
    if run_mode == "neg_file_mode_1" or run_mode == "neg_file_mode_2":
        import os
        os.remove("tmp_file.txt")

if __name__ == "__main__":
    __main__()
