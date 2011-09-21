'''
2010, Kanwei Li
Summary tree data structure for aggregation

10/20/2010: Changed version to 2 as we no longer look at bottom level, for better performance
'''

import sys, os
import cPickle

VERSION = 2
MIN_LEVEL = 2

class SummaryTree:
    def __init__(self, block_size, levels, draw_cutoff, detail_cutoff):
        self.version = VERSION
        self.chrom_blocks = {}
        self.levels = levels
        self.draw_cutoff = draw_cutoff
        self.detail_cutoff = detail_cutoff
        self.block_size = block_size
        self.chrom_stats = {}
    
    def find_block(self, num, level):
        return (num / self.block_size ** level)
        
    def insert_range(self, chrom, start, end):
        if chrom in self.chrom_blocks:
            blocks = self.chrom_blocks[chrom]
        else:
            blocks = self.chrom_blocks[chrom] = {}
            self.chrom_stats[chrom] = {}
            for level in range(MIN_LEVEL, self.levels+1):
                blocks[level] = {}
            
           
        for level in range(MIN_LEVEL, self.levels+1):
            block_level = blocks[level]
            starting_block = self.find_block(start, level)
            ending_block = self.find_block(end, level)
            for block in range(starting_block, ending_block+1):
                if block in block_level:
                    block_level[block] += 1
                else:
                    block_level[block] = 1
        
    def finish(self):
        ''' Checks for cutoff and only stores levels above it '''
        for chrom, blocks in self.chrom_blocks.iteritems():
            cur_best = 999
            for level in range(self.levels, MIN_LEVEL-1, -1):
                max_val = max(blocks[level].values())
                if max_val < self.draw_cutoff:
                    if "draw_level" not in self.chrom_stats[chrom]:
                        self.chrom_stats[chrom]["draw_level"] = level
                    elif max_val < self.detail_cutoff:
                        self.chrom_stats[chrom]["detail_level"] = level
                        break
                else:
                    self.chrom_stats[chrom][level] = {}
                    self.chrom_stats[chrom][level]["delta"] = self.block_size ** level
                    self.chrom_stats[chrom][level]["max"] = max_val
                    self.chrom_stats[chrom][level]["avg"] = float(max_val) / len(blocks[level])
                    cur_best = level
            
            self.chrom_blocks[chrom] = dict([ (key, value) for key, value in blocks.iteritems() if key >= cur_best ])
        
    def query(self, chrom, start, end, level):
        if chrom in self.chrom_blocks:
            stats = self.chrom_stats[chrom]
            if "detail_level" in stats and level <= stats["detail_level"]:
                return "detail"
            elif "draw_level" in stats and level <= stats["draw_level"]:
                return "draw"
            blocks = self.chrom_blocks[chrom]
            results = []
            multiplier = self.block_size ** level
            starting_block = self.find_block(start, level)
            ending_block = self.find_block(end, level)
            for block in range(starting_block, ending_block+1):
                if block in blocks[level]:
                    results.append( (block * multiplier, blocks[level][block]) )
            return results
            
        return None
        
    def write(self, filename):
        self.finish()
        cPickle.dump(self, open(filename, 'wb'), 2)
        
def summary_tree_from_file(filename):
    return cPickle.load(open(filename, "rb"))
    
