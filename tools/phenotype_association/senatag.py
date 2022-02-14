#!/usr/bin/env python
"""
This tool takes the following file pairs as input:
a) input_snp  : A file with identifiers for SNPs (one on each line)
b) ldfile     : A file where each line has  the following
                snp     list
                where "snp" is an identifier for one SNP and the "list" is a
                comma separated list of all the other snps that are in LD with
                it (as per some threshold of rsquare)

The output is a set of tag SNPs for the given datasets

The algorithm is as follows:

a) Construct a graph for each population, where each node is a SNP and two nodes
are connected using an edge iff they are in LD.
b) For each SNP, count the total number of connected nodes, which have not yet
been visited.
c) Find the SNP with the highest count and assign it to be a tag SNP.
d) Mark that SNP and all the snps connected to it as "visited". This should be
done for each population.
e) Continue steps b-e until all SNPs, in all populations have been visited.
"""
from __future__ import print_function

import heapq
import os
from functools import total_ordering
from getopt import (
    getopt,
    GetoptError,
)
from sys import (
    argv,
    exit,
    stderr,
)

__author__ = "Aakrosh Ratan"
__email__ = "ratan@bx.psu.edu"

# do we want the debug information to be printed?
debug_flag = False


@total_ordering
class node(object):
    def __init__(self, name):
        self.name = name
        self.edges = []
        self.visited = False

    # return the number of nodes connected to this node, that have yet to be
    # visited
    def num_not_visited(self):
        num = 0
        for n in self.edges:
            if n.visited is False:
                num += 1
        return num

    def __eq__(self, other):
        return self.num_not_visited() == other.num_not_visited()

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        return other.num_not_visited() < self.num_not_visited()

    def __str__(self):
        return self.name


class graph(object):
    def __init__(self):
        self.nodes = {}

    def __str__(self):
        string = ""
        for n1 in self.nodes.values():
            n2s = [x.name for x in n1.edges]
            string += "%s %s\n" % (n1.name, ",".join(n2s))
        return string[:-1]

    def add_node(self, n):
        self.nodes[n.name] = n

    def add_edges(self, n1, n2):
        assert n1.name in self.nodes
        assert n2.name in self.nodes
        n1.edges.append(n2)
        n2.edges.append(n1)

    def check_graph(self):
        for n in self.nodes.values():
            ms = [x for x in n.edges]
            for m in ms:
                if n not in m.edges:
                    print("check : %s - %s" % (n, m), file=stderr)


def construct_graph(ldfile, snpfile):
    # construct the initial graph. add all the SNPs as nodes
    g = graph()
    file = open(snpfile, "r")

    for line in file:
        # ignore empty lines and add the remainder to the graph
        if len(line.strip()) == 0:
            continue
        n = node(line.strip())
        g.add_node(n)

    file.close()
    print("Added %d nodes to a graph" % len(g.nodes), file=stderr)

    # now add all the edges
    file = open(ldfile, "r")

    for line in file:
        tokens = line.split()
        assert len(tokens) == 2

        # if this node is in the graph, then we need to construct an edge from
        # this node to all the nodes which are highly related to it
        if tokens[0] in g.nodes:
            n1 = g.nodes[tokens[0]]
            n2s = [g.nodes[x] for x in tokens[1].split(",")]

            for n2 in n2s:
                g.add_edges(n1, n2)

    file.close()
    print("Added all edges to the graph", file=stderr)

    return g


def check_output(g, tagsnps):
    # find all the nodes in the graph
    allsnps = [x.name for x in g.nodes.values()]

    # find the nodes that are covered by our tagsnps
    mysnps = [x.name for x in tagsnps]

    for n in tagsnps:
        for m in n.edges:
            mysnps.append(m.name)

    mysnps = list(set(mysnps))

    if set(allsnps) != set(mysnps):
        diff = list(set(allsnps) - set(mysnps))
        print("%s are not covered" % ",".join(diff), file=stderr)


def main(ldfile, snpsfile, required, excluded):
    # construct the graph
    g = construct_graph(ldfile, snpsfile)
    if debug_flag is True:
        g.check_graph()

    tagsnps = []
    neighbors = {}

    # take care of the SNPs that are required to be TagSNPs
    for s in required:
        t = g.nodes[s]

        t.visited = True
        ns = []

        for n in t.edges:
            if n.visited is False:
                ns.append(n.name)
            n.visited = True

        tagsnps.append(t)
        neighbors[t.name] = list(set(ns))

    # find the tag SNPs for this graph
    data = list(g.nodes.values())[:]
    heapq.heapify(data)

    while data:
        s = heapq.heappop(data)

        if s.visited is True or s.name in excluded:
            continue

        s.visited = True
        ns = []

        for n in s.edges:
            if n.visited is False:
                ns.append(n.name)
            n.visited = True

        tagsnps.append(s)
        neighbors[s.name] = list(set(ns))

        heapq.heapify(data)

    for s in tagsnps:
        if len(neighbors[s.name]) > 0:
            print("%s\t%s" % (s, ",".join(neighbors[s.name])))
            continue
        print(s)

    if debug_flag is True:
        check_output(g, tagsnps)


def read_list(filename):
    assert os.path.exists(filename)
    file = open(filename)
    list = {}

    for line in file:
        list[line.strip()] = 1

    file.close()
    return list


def usage():
    f = stderr
    print("usage:", file=f)
    print("senatag [options] neighborhood.txt inputsnps.txt", file=f)
    print("where inputsnps.txt is a file of snps from one population", file=f)
    print("where neighborhood.txt is neighborhood details for the pop.", file=f)
    print("where the options are:", file=f)
    print("-h,--help : print usage and quit", file=f)
    print("-d,--debug: print debug information", file=f)
    print("-e,--excluded : file with names of SNPs that cannot be TagSNPs", file=f)
    print("-r,--required : file with names of SNPs that should be TagSNPs", file=f)


if __name__ == "__main__":
    try:
        opts, args = getopt(argv[1:], "hdr:e:", ["help", "debug", "required=", "excluded="])
    except GetoptError as err:
        print(str(err))
        usage()
        exit(2)

    required = {}
    excluded = {}

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            exit()
        elif o in ("-d", "--debug"):
            debug_flag = True
        elif o in ("-r", "--required"):
            required = read_list(a)
        elif o in ("-e", "--excluded"):
            excluded = read_list(a)
        else:
            raise AssertionError("unhandled option")

    if len(args) != 2:
        usage()
        exit(3)

    assert os.path.exists(args[0])
    assert os.path.exists(args[1])

    main(args[0], args[1], required, excluded)
