#!/usr/bin/env python
# Dan Blankenberg

import sys

assert sys.version_info[:2] >= ( 2, 4 )


# genbank_to_bed
class Region:
    def __init__( self ):
        self.qualifiers = {}
        self.start = None
        self.end = None
        self.strand = '+'

    def set_coordinates_by_location( self, location ):
        location = location.strip().lower().replace( '..', ',' )
        if "complement(" in location:  # if part of the sequence is on the negative strand, it all is?
            self.strand = '-'  # default of + strand
        for remove_text in ["join(", "order(", "complement(", ")"]:
            location = location.replace( remove_text, "" )
        for number in location.split( ',' ):
            number = number.strip('\n\r\t <>,()')
            if number:
                if "^" in number:
                    # a single point
                    # check that this is correct for points, ie: 413/NC_005027.gbk:     misc_feature    6636286^6636287  ===> 6636285,6636286
                    end = int( number.split( '^' )[0] )
                    start = end - 1
                else:
                    end = int( number )
                    start = end - 1  # match BED coordinates
                if self.start is None or start < self.start:
                    self.start = start
                if self.end is None or end > self.end:
                    self.end = end


class GenBankFeatureParser:
    """Parses Features from Single Locus GenBank file"""
    def __init__( self, fh, features_list=[] ):
        self.fh = fh
        self.features = {}
        fh.seek(0)
        in_features = False
        last_feature_name = None
        base_indent = 0
        last_attr_name = None
        for line in fh:
            if not in_features and line.startswith('FEATURES'):
                in_features = True
                continue
            if in_features:
                lstrip = line.lstrip()
                if line and lstrip == line:
                    break  # end of feature block
                cur_indent = len( line ) - len( lstrip )
                if last_feature_name is None:
                    base_indent = cur_indent
                if cur_indent == base_indent:
                    # a new feature
                    last_attr_name = None
                    fields = lstrip.split( None, 1 )
                    last_feature_name = fields[0].strip()
                    if not features_list or ( features_list and last_feature_name in features_list ):
                        if last_feature_name not in self.features:
                            self.features[last_feature_name] = []
                        region = Region()
                        region.set_coordinates_by_location( fields[1] )
                        self.features[last_feature_name].append( region )
                else:
                    # add info to last known feature
                    line = line.strip()
                    if line.startswith( '/' ):
                        fields = line[1:].split( '=', 1 )
                        if len( fields ) == 2:
                            last_attr_name, content = fields
                        else:
                            # No data
                            last_attr_name = line[1:]
                            content = ""
                        content = content.strip( '"' )
                        if last_attr_name not in self.features[last_feature_name][-1].qualifiers:
                            self.features[last_feature_name][-1].qualifiers[last_attr_name] = []
                        self.features[last_feature_name][-1].qualifiers[last_attr_name].append( content )
                    elif last_attr_name is None and last_feature_name:
                        # must still be working on location
                        self.features[last_feature_name][-1].set_coordinates_by_location( line )
                    else:
                        # continuation of multi-line qualifier content
                        if last_feature_name.lower() in ['translation']:
                            self.features[last_feature_name][-1].qualifiers[last_attr_name][-1] = "%s%s" % ( self.features[last_feature_name][-1].qualifiers[last_attr_name][-1], line.rstrip( '"' ) )
                        else:
                            self.features[last_feature_name][-1].qualifiers[last_attr_name][-1] = "%s %s" % ( self.features[last_feature_name][-1].qualifiers[last_attr_name][-1], line.rstrip( '"' ) )

    def get_features_by_type( self, feature_type ):
        if feature_type not in self.features:
            return []
        else:
            return self.features[feature_type]


# Parse A GenBank file and return arrays of BED regions for the corresponding features
def get_bed_from_genbank(gb_file, chrom, feature_list):
    genbank_parser = GenBankFeatureParser( open( gb_file ) )
    features = {}
    for feature_type in feature_list:
        features[feature_type] = []
        for feature in genbank_parser.get_features_by_type( feature_type ):
            name = ""
            for name_tag in ['gene', 'locus_tag', 'db_xref']:
                if name_tag in feature.qualifiers:
                    if name:
                        name = name + ";"
                    name = name + feature.qualifiers[name_tag][0].replace(" ", "_")
            if not name:
                name = "unknown"

            features[feature_type].append( "%s\t%s\t%s\t%s\t%s\t%s" % ( chrom, feature.start, feature.end, name, 0, feature.strand ) )  # append new bed field here
    return features


# geneMark to bed
# converts GeneMarkHMM to bed
# returns an array of bed regions
def get_bed_from_GeneMark(geneMark_filename, chr):
    orfs = open(geneMark_filename).readlines()
    while True:
        line = orfs.pop(0).strip()
        if line.startswith("--------"):
            orfs.pop(0)
            break
    orfs = "".join(orfs)
    ctr = 0
    regions = []
    for block in orfs.split("\n\n"):
        if block.startswith("List of Regions of interest"):
            break
        best_block = {'start': 0, 'end': 0, 'strand': '+', 'avg_prob': -sys.maxint, 'start_prob': -sys.maxint, 'name': 'DNE'}
        ctr += 1
        ctr2 = 0
        for line in block.split("\n"):
            ctr2 += 1
            fields = line.split()
            start = int(fields.pop(0)) - 1
            end = int(fields.pop(0))
            strand = fields.pop(0)
            if strand == 'complement':
                strand = "-"
            else:
                strand = "+"
            frame = fields.pop(0)
            frame = frame + " " + fields.pop(0)
            avg_prob = float(fields.pop(0))
            try:
                start_prob = float(fields.pop(0))
            except:
                start_prob = 0
            name = "orf_" + str(ctr) + "_" + str(ctr2)
            if avg_prob >= best_block['avg_prob']:
                if start_prob > best_block['start_prob']:
                    best_block = {'start': start, 'end': end, 'strand': strand, 'avg_prob': avg_prob, 'start_prob': start_prob, 'name': name}
        regions.append(chr + "\t" + str(best_block['start']) + "\t" + str(best_block['end']) + "\t" + best_block['name'] + "\t" + str(int(best_block['avg_prob'] * 1000)) + "\t" + best_block['strand'])
    return regions


# geneMarkHMM to bed
# converts GeneMarkHMM to bed
# returns an array of bed regions
def get_bed_from_GeneMarkHMM(geneMarkHMM_filename, chr):
    orfs = open(geneMarkHMM_filename).readlines()
    while True:
        line = orfs.pop(0).strip()
        if line == "Predicted genes":
            orfs.pop(0)
            orfs.pop(0)
            break
    regions = []
    for line in orfs:
        fields = line.split()
        name = "gene_number_" + fields.pop(0)
        strand = fields.pop(0)
        start = fields.pop(0)
        if start.startswith("<"):
            start = 1
        start = int(start) - 1
        end = fields.pop(0)
        if end.startswith(">"):
            end = end[1:]
        end = int(end)
        score = 0  # no scores provided
        regions.append(chr + "\t" + str(start) + "\t" + str(end) + "\t" + name + "\t" + str(score) + "\t" + strand)
    return regions


# glimmer3 to bed
# converts glimmer3 to bed, doing some linear scaling (probably not correct?) on scores
# returns an array of bed regions
def get_bed_from_glimmer3(glimmer3_filename, chr):
    max_score = -sys.maxint
    min_score = sys.maxint
    orfs = []
    for line in open(glimmer3_filename).readlines():
        if line.startswith(">"):
            continue
        fields = line.split()
        name = fields.pop(0)
        start = int(fields.pop(0))
        end = int(fields.pop(0))
        if int(fields.pop(0)) < 0:
            strand = "-"
            temp = start
            start = end
            end = temp
        else:
            strand = "+"
        start = start - 1
        score = (float(fields.pop(0)))
        if score > max_score:
            max_score = score
        if score < min_score:
            min_score = score
        orfs.append((chr, start, end, name, score, strand))

    delta = 0
    if min_score < 0:
        delta = min_score * -1
    regions = []
    for (chr, start, end, name, score, strand) in orfs:
        # need to cast to str because was having the case where 1000.0 was rounded to 999 by int, some sort of precision bug?
        my_score = int(float(str( ( (score + delta) * (1000 - 0 - (min_score + delta)) ) / ( (max_score + delta) + 0 ))))

        regions.append(chr + "\t" + str(start) + "\t" + str(end) + "\t" + name + "\t" + str(my_score) + "\t" + strand)
    return regions
