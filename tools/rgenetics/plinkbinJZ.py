#!/usr/bin/env python2.4
"""
"""

import optparse,os,subprocess,gzip,struct,time,commands
from array import array

#from AIMS import util
#from pga import util as pgautil

__FILE_ID__ = '$Id: plinkbinJZ.py,v 1.14 2009/07/13 20:16:50 rejpz Exp $'

VERBOSE = True

MISSING_ALLELES = set(['N', '0', '.', '-',''])

AUTOSOMES = set(range(1, 23) + [str(c) for c in range(1, 23)])

MAGIC_BYTE1 = '00110110'
MAGIC_BYTE2 = '11011000'
FORMAT_SNP_MAJOR_BYTE = '10000000'
FORMAT_IND_MAJOR_BYTE = '00000000'
MAGIC1 = (0, 3, 1, 2)
MAGIC2 = (3, 1, 2, 0)
FORMAT_SNP_MAJOR = (2, 0, 0, 0)
FORMAT_IND_MAJOR = (0, 0, 0, 0)
HEADER_LENGTH = 3

HOM0 = 3
HOM1 = 0
MISS = 2
HET  = 1
HOM0_GENO = (0, 0)
HOM1_GENO = (1, 1)
HET_GENO = (0, 1)
MISS_GENO = (-9, -9)

GENO_TO_GCODE = {
    HOM0_GENO: HOM0, 
    HET_GENO: HET, 
    HOM1_GENO: HOM1, 
    MISS_GENO: MISS, 
    }

CHROM_REPLACE = {
    'X': '23',
    'Y': '24',
    'XY': '25',
    'MT': '26',
    'M': '26',
}

MAP_LINE_EXCEPTION_TEXT = """
One or more lines in the *.map file has only three fields.
The line was:

%s

If you are running rgGRR through EPMP, this is usually a
sign that you are using an old version of the map file.
You can correct the problem by re-running Subject QC.  If
you have already tried this, please contact the developers,
or file a bug.
"""

INT_TO_GCODE = {
     0: array('i', (0, 0, 0, 0)),   1: array('i', (2, 0, 0, 0)),   2: array('i', (1, 0, 0, 0)),   3: array('i', (3, 0, 0, 0)), 
     4: array('i', (0, 2, 0, 0)),   5: array('i', (2, 2, 0, 0)),   6: array('i', (1, 2, 0, 0)),   7: array('i', (3, 2, 0, 0)), 
     8: array('i', (0, 1, 0, 0)),   9: array('i', (2, 1, 0, 0)),  10: array('i', (1, 1, 0, 0)),  11: array('i', (3, 1, 0, 0)), 
    12: array('i', (0, 3, 0, 0)),  13: array('i', (2, 3, 0, 0)),  14: array('i', (1, 3, 0, 0)),  15: array('i', (3, 3, 0, 0)), 
    16: array('i', (0, 0, 2, 0)),  17: array('i', (2, 0, 2, 0)),  18: array('i', (1, 0, 2, 0)),  19: array('i', (3, 0, 2, 0)), 
    20: array('i', (0, 2, 2, 0)),  21: array('i', (2, 2, 2, 0)),  22: array('i', (1, 2, 2, 0)),  23: array('i', (3, 2, 2, 0)), 
    24: array('i', (0, 1, 2, 0)),  25: array('i', (2, 1, 2, 0)),  26: array('i', (1, 1, 2, 0)),  27: array('i', (3, 1, 2, 0)), 
    28: array('i', (0, 3, 2, 0)),  29: array('i', (2, 3, 2, 0)),  30: array('i', (1, 3, 2, 0)),  31: array('i', (3, 3, 2, 0)), 
    32: array('i', (0, 0, 1, 0)),  33: array('i', (2, 0, 1, 0)),  34: array('i', (1, 0, 1, 0)),  35: array('i', (3, 0, 1, 0)), 
    36: array('i', (0, 2, 1, 0)),  37: array('i', (2, 2, 1, 0)),  38: array('i', (1, 2, 1, 0)),  39: array('i', (3, 2, 1, 0)), 
    40: array('i', (0, 1, 1, 0)),  41: array('i', (2, 1, 1, 0)),  42: array('i', (1, 1, 1, 0)),  43: array('i', (3, 1, 1, 0)), 
    44: array('i', (0, 3, 1, 0)),  45: array('i', (2, 3, 1, 0)),  46: array('i', (1, 3, 1, 0)),  47: array('i', (3, 3, 1, 0)), 
    48: array('i', (0, 0, 3, 0)),  49: array('i', (2, 0, 3, 0)),  50: array('i', (1, 0, 3, 0)),  51: array('i', (3, 0, 3, 0)), 
    52: array('i', (0, 2, 3, 0)),  53: array('i', (2, 2, 3, 0)),  54: array('i', (1, 2, 3, 0)),  55: array('i', (3, 2, 3, 0)), 
    56: array('i', (0, 1, 3, 0)),  57: array('i', (2, 1, 3, 0)),  58: array('i', (1, 1, 3, 0)),  59: array('i', (3, 1, 3, 0)), 
    60: array('i', (0, 3, 3, 0)),  61: array('i', (2, 3, 3, 0)),  62: array('i', (1, 3, 3, 0)),  63: array('i', (3, 3, 3, 0)), 
    64: array('i', (0, 0, 0, 2)),  65: array('i', (2, 0, 0, 2)),  66: array('i', (1, 0, 0, 2)),  67: array('i', (3, 0, 0, 2)), 
    68: array('i', (0, 2, 0, 2)),  69: array('i', (2, 2, 0, 2)),  70: array('i', (1, 2, 0, 2)),  71: array('i', (3, 2, 0, 2)), 
    72: array('i', (0, 1, 0, 2)),  73: array('i', (2, 1, 0, 2)),  74: array('i', (1, 1, 0, 2)),  75: array('i', (3, 1, 0, 2)), 
    76: array('i', (0, 3, 0, 2)),  77: array('i', (2, 3, 0, 2)),  78: array('i', (1, 3, 0, 2)),  79: array('i', (3, 3, 0, 2)), 
    80: array('i', (0, 0, 2, 2)),  81: array('i', (2, 0, 2, 2)),  82: array('i', (1, 0, 2, 2)),  83: array('i', (3, 0, 2, 2)), 
    84: array('i', (0, 2, 2, 2)),  85: array('i', (2, 2, 2, 2)),  86: array('i', (1, 2, 2, 2)),  87: array('i', (3, 2, 2, 2)), 
    88: array('i', (0, 1, 2, 2)),  89: array('i', (2, 1, 2, 2)),  90: array('i', (1, 1, 2, 2)),  91: array('i', (3, 1, 2, 2)), 
    92: array('i', (0, 3, 2, 2)),  93: array('i', (2, 3, 2, 2)),  94: array('i', (1, 3, 2, 2)),  95: array('i', (3, 3, 2, 2)), 
    96: array('i', (0, 0, 1, 2)),  97: array('i', (2, 0, 1, 2)),  98: array('i', (1, 0, 1, 2)),  99: array('i', (3, 0, 1, 2)), 
   100: array('i', (0, 2, 1, 2)), 101: array('i', (2, 2, 1, 2)), 102: array('i', (1, 2, 1, 2)), 103: array('i', (3, 2, 1, 2)), 
   104: array('i', (0, 1, 1, 2)), 105: array('i', (2, 1, 1, 2)), 106: array('i', (1, 1, 1, 2)), 107: array('i', (3, 1, 1, 2)), 
   108: array('i', (0, 3, 1, 2)), 109: array('i', (2, 3, 1, 2)), 110: array('i', (1, 3, 1, 2)), 111: array('i', (3, 3, 1, 2)), 
   112: array('i', (0, 0, 3, 2)), 113: array('i', (2, 0, 3, 2)), 114: array('i', (1, 0, 3, 2)), 115: array('i', (3, 0, 3, 2)), 
   116: array('i', (0, 2, 3, 2)), 117: array('i', (2, 2, 3, 2)), 118: array('i', (1, 2, 3, 2)), 119: array('i', (3, 2, 3, 2)), 
   120: array('i', (0, 1, 3, 2)), 121: array('i', (2, 1, 3, 2)), 122: array('i', (1, 1, 3, 2)), 123: array('i', (3, 1, 3, 2)), 
   124: array('i', (0, 3, 3, 2)), 125: array('i', (2, 3, 3, 2)), 126: array('i', (1, 3, 3, 2)), 127: array('i', (3, 3, 3, 2)), 
   128: array('i', (0, 0, 0, 1)), 129: array('i', (2, 0, 0, 1)), 130: array('i', (1, 0, 0, 1)), 131: array('i', (3, 0, 0, 1)), 
   132: array('i', (0, 2, 0, 1)), 133: array('i', (2, 2, 0, 1)), 134: array('i', (1, 2, 0, 1)), 135: array('i', (3, 2, 0, 1)), 
   136: array('i', (0, 1, 0, 1)), 137: array('i', (2, 1, 0, 1)), 138: array('i', (1, 1, 0, 1)), 139: array('i', (3, 1, 0, 1)), 
   140: array('i', (0, 3, 0, 1)), 141: array('i', (2, 3, 0, 1)), 142: array('i', (1, 3, 0, 1)), 143: array('i', (3, 3, 0, 1)), 
   144: array('i', (0, 0, 2, 1)), 145: array('i', (2, 0, 2, 1)), 146: array('i', (1, 0, 2, 1)), 147: array('i', (3, 0, 2, 1)), 
   148: array('i', (0, 2, 2, 1)), 149: array('i', (2, 2, 2, 1)), 150: array('i', (1, 2, 2, 1)), 151: array('i', (3, 2, 2, 1)), 
   152: array('i', (0, 1, 2, 1)), 153: array('i', (2, 1, 2, 1)), 154: array('i', (1, 1, 2, 1)), 155: array('i', (3, 1, 2, 1)), 
   156: array('i', (0, 3, 2, 1)), 157: array('i', (2, 3, 2, 1)), 158: array('i', (1, 3, 2, 1)), 159: array('i', (3, 3, 2, 1)), 
   160: array('i', (0, 0, 1, 1)), 161: array('i', (2, 0, 1, 1)), 162: array('i', (1, 0, 1, 1)), 163: array('i', (3, 0, 1, 1)), 
   164: array('i', (0, 2, 1, 1)), 165: array('i', (2, 2, 1, 1)), 166: array('i', (1, 2, 1, 1)), 167: array('i', (3, 2, 1, 1)), 
   168: array('i', (0, 1, 1, 1)), 169: array('i', (2, 1, 1, 1)), 170: array('i', (1, 1, 1, 1)), 171: array('i', (3, 1, 1, 1)), 
   172: array('i', (0, 3, 1, 1)), 173: array('i', (2, 3, 1, 1)), 174: array('i', (1, 3, 1, 1)), 175: array('i', (3, 3, 1, 1)), 
   176: array('i', (0, 0, 3, 1)), 177: array('i', (2, 0, 3, 1)), 178: array('i', (1, 0, 3, 1)), 179: array('i', (3, 0, 3, 1)), 
   180: array('i', (0, 2, 3, 1)), 181: array('i', (2, 2, 3, 1)), 182: array('i', (1, 2, 3, 1)), 183: array('i', (3, 2, 3, 1)), 
   184: array('i', (0, 1, 3, 1)), 185: array('i', (2, 1, 3, 1)), 186: array('i', (1, 1, 3, 1)), 187: array('i', (3, 1, 3, 1)), 
   188: array('i', (0, 3, 3, 1)), 189: array('i', (2, 3, 3, 1)), 190: array('i', (1, 3, 3, 1)), 191: array('i', (3, 3, 3, 1)), 
   192: array('i', (0, 0, 0, 3)), 193: array('i', (2, 0, 0, 3)), 194: array('i', (1, 0, 0, 3)), 195: array('i', (3, 0, 0, 3)), 
   196: array('i', (0, 2, 0, 3)), 197: array('i', (2, 2, 0, 3)), 198: array('i', (1, 2, 0, 3)), 199: array('i', (3, 2, 0, 3)), 
   200: array('i', (0, 1, 0, 3)), 201: array('i', (2, 1, 0, 3)), 202: array('i', (1, 1, 0, 3)), 203: array('i', (3, 1, 0, 3)), 
   204: array('i', (0, 3, 0, 3)), 205: array('i', (2, 3, 0, 3)), 206: array('i', (1, 3, 0, 3)), 207: array('i', (3, 3, 0, 3)), 
   208: array('i', (0, 0, 2, 3)), 209: array('i', (2, 0, 2, 3)), 210: array('i', (1, 0, 2, 3)), 211: array('i', (3, 0, 2, 3)), 
   212: array('i', (0, 2, 2, 3)), 213: array('i', (2, 2, 2, 3)), 214: array('i', (1, 2, 2, 3)), 215: array('i', (3, 2, 2, 3)), 
   216: array('i', (0, 1, 2, 3)), 217: array('i', (2, 1, 2, 3)), 218: array('i', (1, 1, 2, 3)), 219: array('i', (3, 1, 2, 3)), 
   220: array('i', (0, 3, 2, 3)), 221: array('i', (2, 3, 2, 3)), 222: array('i', (1, 3, 2, 3)), 223: array('i', (3, 3, 2, 3)), 
   224: array('i', (0, 0, 1, 3)), 225: array('i', (2, 0, 1, 3)), 226: array('i', (1, 0, 1, 3)), 227: array('i', (3, 0, 1, 3)), 
   228: array('i', (0, 2, 1, 3)), 229: array('i', (2, 2, 1, 3)), 230: array('i', (1, 2, 1, 3)), 231: array('i', (3, 2, 1, 3)), 
   232: array('i', (0, 1, 1, 3)), 233: array('i', (2, 1, 1, 3)), 234: array('i', (1, 1, 1, 3)), 235: array('i', (3, 1, 1, 3)), 
   236: array('i', (0, 3, 1, 3)), 237: array('i', (2, 3, 1, 3)), 238: array('i', (1, 3, 1, 3)), 239: array('i', (3, 3, 1, 3)), 
   240: array('i', (0, 0, 3, 3)), 241: array('i', (2, 0, 3, 3)), 242: array('i', (1, 0, 3, 3)), 243: array('i', (3, 0, 3, 3)), 
   244: array('i', (0, 2, 3, 3)), 245: array('i', (2, 2, 3, 3)), 246: array('i', (1, 2, 3, 3)), 247: array('i', (3, 2, 3, 3)), 
   248: array('i', (0, 1, 3, 3)), 249: array('i', (2, 1, 3, 3)), 250: array('i', (1, 1, 3, 3)), 251: array('i', (3, 1, 3, 3)), 
   252: array('i', (0, 3, 3, 3)), 253: array('i', (2, 3, 3, 3)), 254: array('i', (1, 3, 3, 3)), 255: array('i', (3, 3, 3, 3)), 
   }

GCODE_TO_INT = dict([(tuple(v),k) for (k,v) in INT_TO_GCODE.items()])

### Exceptions
class DuplicateMarkerInMapFile(Exception): pass
class MapLineTooShort(Exception): pass
class ThirdAllele(Exception): pass
class PedError(Exception): pass
class BadMagic(Exception):
    """ Raised when one of the MAGIC bytes in a bed file does not match
    """
    pass
class BedError(Exception):
    """ Raised when parsing a bed file runs into problems
    """
    pass
class UnknownGenocode(Exception):
    """ Raised when we get a 2-bit genotype that is undecipherable (is it possible?)
    """
    pass
class UnknownGeno(Exception): pass

### Utility functions

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def ceiling(n, k):
    ''' Return the least multiple of k which is greater than n
    '''
    m = n % k
    if m == 0:
        return n
    else:
        return n + k - m

def nbytes(n):
    ''' Return the number of bytes required for n subjects
    '''
    return 2*ceiling(n, 4)/8

### Primary module functionality
class LPed:
    """ The uber-class for processing the Linkage-format *.ped/*.map files
    """
    def __init__(self,  base):
        self.base = base
        self._ped = Ped('%s.ped' % (self.base))
        self._map = Map('%s.map' % (self.base))

        self._markers = {}
        self._ordered_markers = []
        self._marker_allele_lookup = {}
        self._autosomal_indices = set()
        
        self._subjects = {}
        self._ordered_subjects = []
        
        self._genotypes = []

    def parse(self):
        """
        """
        if VERBOSE: print 'plinkbinJZ: Analysis started: %s' % (timenow())
        self._map.parse()
        self._markers = self._map._markers
        self._ordered_markers = self._map._ordered_markers
        self._autosomal_indices = self._map._autosomal_indices
        
        self._ped.parse(self._ordered_markers)
        self._subjects = self._ped._subjects
        self._ordered_subjects = self._ped._ordered_subjects
        self._genotypes = self._ped._genotypes
        self._marker_allele_lookup = self._ped._marker_allele_lookup
        
        ### Adjust self._markers based on the allele information
        ### we got from parsing the ped file
        for m,  name in enumerate(self._ordered_markers):
            a1,  a2 = self._marker_allele_lookup[m][HET]
            self._markers[name][-2] = a1
            self._markers[name][-1] = a2
        if VERBOSE: print 'plinkbinJZ: Analysis finished: %s' % (timenow())

    def getSubjectInfo(self, fid, oiid):
        """
        """
        return self._subject_info[(fid, oiid)]

    def getSubjectInfoByLine(self, line):
        """
        """
        return self._subject_info[self._ordered_subjects[line]]
    
    def getGenotypesByIndices(self, s, mlist, format):
        """ needed for grr if lped - deprecated but..
        """
        mlist = dict(zip(mlist,[True,]*len(mlist))) # hash quicker than 'in' ?
        raw_array = array('i', [row[s] for m,row in enumerate(self._genotypes) if mlist.get(m,None)])            
        if format == 'raw':
            return raw_array
        elif format == 'ref':
            result = array('i', [0]*len(mlist))
            for m, gcode in enumerate(raw_array):
                if gcode == HOM0:
                    nref = 3
                elif gcode == HET:
                    nref = 2
                elif gcode == HOM1:
                    nref = 1
                else:
                    nref = 0
                result[m] = nref
            return result
        else:
            result = []
            for m, gcode in enumerate(raw_array):
                result.append(self._marker_allele_lookup[m][gcode])
            return result
    
    def writebed(self, base):
        """
        """
        dst_name = '%s.fam' % (base)        
        print 'Writing pedigree information to [ %s ]' % (dst_name)
        dst = open(dst_name, 'w')
        for skey in self._ordered_subjects:            
            (fid, iid, did, mid, sex, phe, sid, d_sid, m_sid) = self._subjects[skey]
            dst.write('%s %s %s %s %s %s\n' % (fid, iid, did, mid, sex, phe))
        dst.close()

        dst_name = '%s.bim' % (base)        
        print 'Writing map (extended format) information to [ %s ]' % (dst_name)
        dst = open(dst_name, 'w')        
        for m, marker in enumerate(self._ordered_markers):
            chrom, name, genpos, abspos,  a1,  a2 = self._markers[marker]
            dst.write('%s\t%s\t%s\t%s\t%s\t%s\n' % (chrom, name, genpos, abspos, a1, a2))
        dst.close()

        bed_name = '%s.bed' % (base)        
        print 'Writing genotype bitfile to [ %s ]' % (bed_name)
        print 'Using (default) SNP-major mode'
        bed = open(bed_name, 'w')

        ### Write the 3 header bytes
        bed.write(struct.pack('B', int(''.join(reversed(MAGIC_BYTE1)), 2)))
        bed.write(struct.pack('B', int(''.join(reversed(MAGIC_BYTE2)), 2)))
        bed.write(struct.pack('B', int(''.join(reversed(FORMAT_SNP_MAJOR_BYTE)), 2)))
        
        ### Calculate how many "pad bits" we should add after the last subject
        nsubjects = len(self._ordered_subjects)
        nmarkers = len(self._ordered_markers)
        total_bytes = nbytes(nsubjects)
        nbits = nsubjects  * 2
        pad_nibbles = ((total_bytes * 8) - nbits)/2
        pad = array('i', [0]*pad_nibbles)

        ### And now write genotypes to the file
        for m in xrange(nmarkers):
            geno = self._genotypes[m]
            geno.extend(pad)
            bytes = len(geno)/4
            for b in range(bytes):
                idx = b*4
                gcode = tuple(geno[idx:idx+4])
                try:
                    byte = struct.pack('B', GCODE_TO_INT[gcode])
                except KeyError:
                    print m, b, gcode
                    raise
                bed.write(byte)
        bed.close()
        
    def autosomal_indices(self):
        """ Return the indices of markers in this ped/map that are autosomal.
            This is used by rgGRR so that it can select a random set of markers
            from the autosomes (sex chroms screw up the plot)
        """
        return self._autosomal_indices

class Ped:
    def __init__(self, path):
        self.path = path
        self._subjects = {}
        self._ordered_subjects = []
        self._genotypes = []
        self._marker_allele_lookup = {}
        
    def lineCount(self,infile):
        """ count the number of lines in a file - efficiently using wget
        """
        return int(commands.getoutput('wc -l %s' % (infile)).split()[0])    
         

    def parse(self,  markers):
        """ Parse a given file -- this needs to be memory-efficient so that large
            files can be parsed (~1 million markers on ~5000 subjects?).  It
            should also be fast, if possible.
        """
                
        ### Find out how many lines are in the file so we can ...
        nsubjects = self.lineCount(self.path)
        ### ... Pre-allocate the genotype arrays
        nmarkers = len(markers)
        _marker_alleles = [['0', '0'] for _ in xrange(nmarkers)]
        self._genotypes = [array('i', [-1]*nsubjects) for _ in xrange(nmarkers)]

        if self.path.endswith('.gz'):
            pfile = gzip.open(self.path, 'r')
        else:
            pfile = open(self.path, 'r')

        for s, line in enumerate(pfile):
            line = line.strip()
            if not line:
                continue
            
            fid, iid, did, mid, sex, phe, genos = line.split(None, 6)
            sid = iid.split('.')[0]
            d_sid = did.split('.')[0]
            m_sid = mid.split('.')[0]
            
            skey = (fid, iid)            
            self._subjects[skey] = (fid, iid, did, mid, sex, phe, sid, d_sid, m_sid)
            self._ordered_subjects.append(skey)

            genotypes = genos.split()
            
            for m, marker in enumerate(markers):
                idx = m*2
                a1, a2 = genotypes[idx:idx+2] # Alleles for subject s, marker m
                s1, s2 = seen = _marker_alleles[m] # Alleles seen for marker m
                
                ### FIXME: I think this can still be faster, and simpler to read
                # Two pieces of logic intertwined here:  first, we need to code
                # this genotype as HOM0, HOM1, HET or MISS.  Second, we need to
                # keep an ongoing record of the genotypes seen for this marker
                if a1 == a2:
                    if a1 in MISSING_ALLELES:
                        geno = MISS_GENO
                    else:
                        if s1 == '0':
                            seen[0] = a1
                        elif s1 == a1 or s2 == a2:
                            pass
                        elif s2 == '0':
                            seen[1] = a1
                        else:
                            raise ThirdAllele('a1=a2=%s, seen=%s?' % (a1, str(seen)))
                    
                        if a1 == seen[0]:
                            geno = HOM0_GENO
                        elif a1 == seen[1]:
                            geno = HOM1_GENO
                        else:
                            raise PedError('Cannot assign geno for a1=a2=%s from seen=%s' % (a1, str(seen)))
                elif a1 in MISSING_ALLELES or a2 in MISSING_ALLELES:
                    geno = MISS_GENO
                else:
                    geno = HET_GENO
                    if s1 == '0':
                        seen[0] = a1
                        seen[1] = a2
                    elif s2 == '0':
                        if s1 == a1:
                            seen[1] = a2
                        elif s1 == a2:
                            seen[1] = a1
                        else:
                            raise ThirdAllele('a1=%s, a2=%s, seen=%s?' % (a1, a2, str(seen)))
                    else:
                        if sorted(seen) != sorted((a1, a2)):
                            raise ThirdAllele('a1=%s, a2=%s, seen=%s?' % (a1, a2, str(seen)))
                                        
                gcode = GENO_TO_GCODE.get(geno, None)
                if gcode is None:
                    raise UnknownGeno(str(geno))
                self._genotypes[m][s] = gcode

        # Build the _marker_allele_lookup table
        for m,  alleles in enumerate(_marker_alleles):                
            if len(alleles) == 2:
                a1,  a2 = alleles
            elif len(alleles) == 1:
                a1 = alleles[0]
                a2 = '0'
            else:
                print 'All alleles blank for %s: %s' % (m,  str(alleles))
                raise

            self._marker_allele_lookup[m] = {
                HOM0: (a2, a2),
                HOM1: (a1, a1),
                HET : (a1, a2),
                MISS: ('0','0'),
                }

        if VERBOSE: print '%s(%s) individuals read from [ %s ]' % (len(self._subjects),  nsubjects,  self.path)
        
class Map:
    def __init__(self, path=None):
        self.path = path
        self._markers = {}
        self._ordered_markers = []
        self._autosomal_indices = set()

    def __len__(self):
        return len(self._markers)

    def parse(self):
        """ Parse a Linkage-format map file
        """
        if self.path.endswith('.gz'):
            fh = gzip.open(self.path, 'r')
        else:
            fh = open(self.path, 'r')
            
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue

            fields = line.split()
            if len(fields) < 4:
                raise MapLineTooShort(MAP_LINE_EXCEPTION_TEXT % (str(line),  len(fields)))
            else:
                chrom, name, genpos, abspos = fields
            if name in self._markers:
                raise DuplicateMarkerInMapFile('Marker %s was found twice in map file %s' % (name, self.path))
            abspos = int(abspos)
            if abspos < 0:
                continue
            if chrom in AUTOSOMES:
                self._autosomal_indices.add(i)
            chrom = CHROM_REPLACE.get(chrom, chrom)
            self._markers[name] = [chrom, name, genpos, abspos,  None,  None]
            self._ordered_markers.append(name)
        fh.close()
        if VERBOSE: print '%s (of %s) markers to be included from [ %s ]' % (len(self._ordered_markers),  i,  self.path)

class BPed:
    """ The uber-class for processing Plink's Binary Ped file format *.bed/*.bim/*.fam
    """
    def __init__(self,  base):
        self.base = base
        self._bed = Bed('%s.bed' % (self.base))
        self._bim = Bim('%s.bim' % (self.base))
        self._fam = Fam('%s.fam' % (self.base))

        self._markers = {}
        self._ordered_markers = []
        self._marker_allele_lookup = {}
        self._autosomal_indices = set()
        
        self._subjects = {}
        self._ordered_subjects = []
        
        self._genotypes = []
        
    def parse(self,  quick=False):
        """
        """
        self._quick = quick
        
        self._bim.parse()
        self._markers = self._bim._markers
        self._ordered_markers = self._bim._ordered_markers
        self._marker_allele_lookup = self._bim._marker_allele_lookup
        self._autosomal_indices = self._bim._autosomal_indices
        
        self._fam.parse()
        self._subjects = self._fam._subjects
        self._ordered_subjects = self._fam._ordered_subjects

        self._bed.parse(self._ordered_subjects,  self._ordered_markers,  quick=quick)
        self._bedf = self._bed._fh
        self._genotypes = self._bed._genotypes
        self.nsubjects = len(self._ordered_subjects)
        self.nmarkers = len(self._ordered_markers)
        self._bytes_per_marker = nbytes(self.nsubjects)

    def writeped(self, path=None):
        """
        """
        path = self.path = path or self.path
        
        map_name = self.path.replace('.bed', '.map')
        print 'Writing map file [ %s ]' % (map_name)
        dst = open(map_name, 'w')
        for m in self._ordered_markers:
            chrom, snp, genpos, abspos, a1, a2 = self._markers[m]
            dst.write('%s\t%s\t%s\t%s\n' % (chrom, snp, genpos, abspos))
        dst.close()

        ped_name = self.path.replace('.bed', '.ped')
        print 'Writing ped file [ %s ]' % (ped_name)
        ped = open(ped_name, 'w')
        firstyikes = False
        for s, skey in enumerate(self._ordered_subjects):
            idx = s*2
            (fid, iid, did, mid, sex, phe, oiid, odid, omid) = self._subjects[skey]
            ped.write('%s %s %s %s %s %s' % (fid, iid, odid, omid, sex, phe))
            genotypes_for_subject = self.getGenotypesForSubject(s)
            for m, snp in enumerate(self._ordered_markers):
                #a1, a2 = self.getGenotypeByIndices(s, m)
                a1,a2 = genotypes_for_subject[m]
                ped.write(' %s %s' % (a1, a2))
            ped.write('\n')
        ped.close()

    def getGenotype(self, subject, marker):
        """ Retrieve a genotype for a particular subject/marker pair
        """
        m = self._ordered_markers.index(marker)
        s = self._ordered_subjects.index(subject)
        return self.getGenotypeByIndices(s, m)

    def getGenotypesForSubject(self, s, raw=False):
        """ Returns list of genotypes for all m markers
            for subject s.  If raw==True, then an array
            of raw integer gcodes is returned instead
        """
        if self._quick:
            nmarkers = len(self._markers)
            raw_array = array('i', [0]*nmarkers)
            seek_nibble = s % 4
            for m in xrange(nmarkers):
                seek_byte = m * self._bytes_per_marker + s/4 + HEADER_LENGTH
                self._bedf.seek(seek_byte)
                geno = struct.unpack('B', self._bedf.read(1))[0]
                quartet = INT_TO_GCODE[geno]
                gcode = quartet[seek_nibble]
                raw_array[m] = gcode
        else:
            raw_array = array('i', [row[s] for row in self._genotypes])
            
        if raw:
            return raw_array
        else:
            result = []
            for m, gcode in enumerate(raw_array):
                result.append(self._marker_allele_lookup[m][gcode])
            return result
        
    def getGenotypeByIndices(self, s, m):
        """
        """
        if self._quick:
            # Determine which byte we need to seek to, and
            # which nibble within the byte we need
            seek_byte = m * self._bytes_per_marker + s/4 + HEADER_LENGTH
            seek_nibble = s % 4
            self._bedf.seek(seek_byte)
            geno = struct.unpack('B', self._bedf.read(1))[0]
            quartet = INT_TO_GCODE[geno]
            gcode = quartet[seek_nibble]
        else:
            # Otherwise, just grab the genotypes from the
            # list of arrays
            genos_for_marker = self._genotypes[m]
            gcode = genos_for_marker[s]

        return self._marker_allele_lookup[m][gcode]

    def getGenotypesByIndices(self, s, mlist, format):
        """
        """
        if self._quick:
            raw_array = array('i', [0]*len(mlist))
            seek_nibble = s % 4
            for i,m in enumerate(mlist):
                seek_byte = m * self._bytes_per_marker + s/4 + HEADER_LENGTH
                self._bedf.seek(seek_byte)
                geno = struct.unpack('B', self._bedf.read(1))[0]
                quartet = INT_TO_GCODE[geno]
                gcode = quartet[seek_nibble]
                raw_array[i] = gcode
            mlist = set(mlist)
        else:
            mlist = set(mlist)
            raw_array = array('i', [row[s] for m,row in enumerate(self._genotypes) if m in mlist])
            
        if format == 'raw':
            return raw_array
        elif format == 'ref':
            result = array('i', [0]*len(mlist))
            for m, gcode in enumerate(raw_array):
                if gcode == HOM0:
                    nref = 3
                elif gcode == HET:
                    nref = 2
                elif gcode == HOM1:
                    nref = 1
                else:
                    nref = 0
                result[m] = nref
            return result
        else:
            result = []
            for m, gcode in enumerate(raw_array):
                result.append(self._marker_allele_lookup[m][gcode])
            return result
    
    def getSubject(self, s):
        """
        """
        skey = self._ordered_subjects[s]
        return self._subjects[skey]
    
    def autosomal_indices(self):
        """ Return the indices of markers in this ped/map that are autosomal.
            This is used by rgGRR so that it can select a random set of markers
            from the autosomes (sex chroms screw up the plot)
        """
        return self._autosomal_indices

class Bed:

    def __init__(self, path):
        self.path = path
        self._genotypes = []
        self._fh = None

    def parse(self, subjects,  markers,  quick=False):
        """ Parse the bed file, indicated either by the path parameter,
            or as the self.path indicated in __init__.  If quick is
            True, then just parse the bim and fam, then genotypes will
            be looked up dynamically by indices
        """
        self._quick = quick
        
        ordered_markers = markers
        ordered_subjects = subjects
        nsubjects = len(ordered_subjects)
        nmarkers = len(ordered_markers)
        
        bed = open(self.path, 'rb')
        self._fh = bed

        byte1 = bed.read(1)
        byte2 = bed.read(1)
        byte3 = bed.read(1)
        format_flag = struct.unpack('B', byte3)[0]

        h1 = tuple(INT_TO_GCODE[struct.unpack('B', byte1)[0]])
        h2 = tuple(INT_TO_GCODE[struct.unpack('B', byte2)[0]])
        h3 = tuple(INT_TO_GCODE[format_flag])

        if h1 != MAGIC1 or h2 != MAGIC2:
            raise BadMagic('One or both MAGIC bytes is wrong: %s==%s or %s==%s' % (h1, MAGIC1, h2, MAGIC2))
        if format_flag:
            print 'Detected that binary PED file is v1.00 SNP-major mode (%s, "%s")\n' % (format_flag, h3)
        else:
            raise 'BAD_FORMAT_FLAG? (%s, "%s")\n' % (format_flag, h3)

        print 'Parsing binary ped file for %s markers and %s subjects' % (nmarkers, nsubjects)

        ### If quick mode was specified, we're done ...
        self._quick = quick
        if quick:
            return
            
        ### ... Otherwise, parse genotypes into an array, and append that
        ### array to self._genotypes
        ngcodes = ceiling(nsubjects, 4)
        bytes_per_marker = nbytes(nsubjects)
        for m in xrange(nmarkers):
            genotype_array = array('i', [-1]*(ngcodes))
            for byte in xrange(bytes_per_marker):
                intval = struct.unpack('B', bed.read(1))[0]
                idx = byte*4
                genotype_array[idx:idx+4] = INT_TO_GCODE[intval]
            self._genotypes.append(genotype_array)
        
class Bim:
    def __init__(self, path):
        """
        """
        self.path = path
        self._markers = {}
        self._ordered_markers = []
        self._marker_allele_lookup = {}
        self._autosomal_indices = set()

    def parse(self):
        """
        """
        print 'Reading map (extended format) from [ %s ]' % (self.path)
        bim = open(self.path, 'r')
        for m, line in enumerate(bim):
            chrom, snp, gpos, apos, a1, a2 = line.strip().split()
            self._markers[snp] = (chrom, snp, gpos, apos, a1, a2)
            self._marker_allele_lookup[m] = {
                HOM0: (a2, a2),
                HOM1: (a1, a1),
                HET : (a1, a2),
                MISS: ('0','0'),
                }
            self._ordered_markers.append(snp)
            if chrom in AUTOSOMES:
                self._autosomal_indices.add(m)
        bim.close()
        print '%s markers to be included from [ %s ]' % (m+1, self.path)

class Fam:
    def __init__(self, path):
        """
        """
        self.path = path
        self._subjects = {}
        self._ordered_subjects = []

    def parse(self):
        """
        """
        print 'Reading pedigree information from [ %s ]' % (self.path)
        fam = open(self.path, 'r')
        for s, line in enumerate(fam):
            fid, iid, did, mid, sex, phe = line.strip().split()
            sid = iid.split('.')[0]
            d_sid = did.split('.')[0]
            m_sid = mid.split('.')[0]
            skey = (fid, iid)
            self._ordered_subjects.append(skey)
            self._subjects[skey] = (fid, iid, did, mid, sex, phe, sid, d_sid, m_sid)
        fam.close()
        print '%s individuals read from [ %s ]' % (s+1, self.path)

### Command-line functionality and testing
def test(arg):
    '''
    '''
    
    import time

    if arg == 'CAMP_AFFY.ped':
        print 'Testing bed.parse(quick=True)'
        s = time.time()
        bed = Bed(arg.replace('.ped', '.bed'))
        bed.parse(quick=True)
        print bed.getGenotype(('400118', '10300283'), 'rs2000467')
        print bed.getGenotype(('400118', '10101384'), 'rs2294019')
        print bed.getGenotype(('400121', '10101149'), 'rs2294019')        
        print bed.getGenotype(('400123', '10200290'), 'rs2294019')        
        assert bed.getGenotype(('400118', '10101384'), 'rs2294019') == ('4','4')
        e = time.time()
        print 'e-s = %s\n' % (e-s)
    
    print 'Testing bed.parse'
    s = time.time()
    bed = BPed(arg)
    bed.parse(quick=False)
    e = time.time()
    print 'e-s = %s\n' % (e-s)

    print 'Testing bed.writeped'
    s = time.time()
    outname = '%s_BEDTEST' % (arg)
    bed.writeped(outname)
    e = time.time()
    print 'e-s = %s\n' % (e-s)
    del(bed)

    print 'Testing ped.parse'
    s = time.time()
    ped = LPed(arg)
    ped.parse()
    e = time.time()
    print 'e-s = %s\n' % (e-s)

    print 'Testing ped.writebed'
    s = time.time()
    outname = '%s_PEDTEST' % (arg)
    ped.writebed(outname)
    e = time.time()
    print 'e-s = %s\n' % (e-s)
    del(ped)
    
def profile_bed(arg):
    """
    """
    bed = BPed(arg)
    bed.parse(quick=False)
    outname = '%s_BEDPROFILE' % (arg)
    bed.writeped(outname)

def profile_ped(arg):
    """
    """
    ped = LPed(arg)
    ped.parse()
    outname = '%s_PEDPROFILE' % (arg)
    ped.writebed(outname)

if __name__ == '__main__':
    """ Run as a command-line, this script should get one or more arguments,
        each one a ped file to be parsed with the PedParser (unit tests?)
    """
    op = optparse.OptionParser()
    op.add_option('--profile-bed', action='store_true', default=False)
    op.add_option('--profile-ped', action='store_true', default=False)
    opts, args = op.parse_args()
    
    if opts.profile_bed:
        import profile
        import pstats
        profile.run('profile_bed(args[0])', 'fooprof')
        p = pstats.Stats('fooprof')
        p.sort_stats('cumulative').print_stats(10)
    elif opts.profile_ped:
        import profile
        import pstats
        profile.run('profile_ped(args[0])', 'fooprof')
        p = pstats.Stats('fooprof')
        p.sort_stats('cumulative').print_stats(10)
    else:
        for arg in args:
            test(arg)
    
    ### Code used to generate the INT_TO_GCODE dictionary
    #print '{\n  ',
    #for i in range(256):
    #   b = INT2BIN[i]
    #    ints = []
    #    s = str(i).rjust(3)
    #    #print b
    #    for j in range(4):
    #        idx = j*2
    #        #print i, j, idx, b[idx:idx+2], int(b[idx:idx+2], 2)
    #        ints.append(int(b[idx:idx+2], 2))
    #    print '%s: array(\'i\', %s),' % (s,tuple(ints)),
    #    if i > 0 and (i+1) % 4 == 0:
    #        print '\n  ',
    #print '}'


