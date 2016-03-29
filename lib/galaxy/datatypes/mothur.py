"""
Mothur Metagenomics Datatypes
James E Johnson - University of Minnesota
Iyad Kandalaft <Iyad.Kandalaft@agr.gc.ca> - Agriculture and Agri-Foods Canda
"""

import logging, os, os.path, sys, time, tempfile, shutil, string, glob, re
import galaxy.model
from galaxy.datatypes.sniff import *
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.data import Text
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.sequence import Fasta
from galaxy import util
from galaxy.datatypes.images import Html
import pkg_resources

log = logging.getLogger(__name__)

## Mothur Classes 

class Otu( Text ):
    file_ext = 'mothur.otu'
    MetadataElement( name="columns", default=0, desc="Number of columns", readonly=True, visible=True, no_value=0 )
    MetadataElement( name="labels", default=[], desc="Label Names", readonly=True, visible=True, no_value=[] )
    def __init__(self, **kwd):
        Text.__init__( self, **kwd )
    def set_meta( self, dataset, overwrite = True, **kwd ):
        if dataset.has_data():
            label_names = set()
            ncols = 0
            data_lines = 0
            comment_lines = 0
            try:
                with open( dataset.file_name ) as fh:
                    for line in fh:
                        fields = line.strip().split('\t')
                        if len(fields) >= 2: 
                            data_lines += 1
                            ncols = max(ncols,len(fields))
                            label_names.add(fields[0])
                        else:
                            comment_lines += 1
                    # Set the discovered metadata values for the dataset
                    dataset.metadata.data_lines = data_lines
                    dataset.metadata.columns = ncols
                    dataset.metadata.labels = list( label_names )
                    dataset.metadata.labels.sort()
            except:
                pass

    def sniff( self, filename ):
        """
        Determines whether the file is a otu (operational taxonomic unit) format
        """
        try:
            with open( filename ) as fh:
                count = 0
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if not line:
                        break #EOF
                    if line and line[0] != '@':
                        linePieces = line.split('\t')
                        if len(linePieces) < 2:
                            return False
                        if count >= 1:
                            try:
                                check = int(linePieces[1])
                                if check + 2 != len(linePieces):
                                    return False
                            except ValueError:
                                return False
                        count += 1
                        if count == 5:
                            return True
            if count < 5 and count > 0:
                return True
        except:
            pass
        return False

class Sabund( Otu ):
    file_ext = 'mothur.sabund'
    def __init__(self, **kwd):
        """
        # http://www.mothur.org/wiki/Sabund_file
        """
        Otu.__init__( self, **kwd )
    def init_meta( self, dataset, copy_from=None ):
        Otu.init_meta( self, dataset, copy_from=copy_from )
    def sniff( self, filename ):
        """
        Determines whether the file is a otu (operational taxonomic unit) format
        label<TAB>count[<TAB>value(1..n)]
        
        """
        try:
            with open( filename ) as fh:
                count = 0
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if not line:
                        break #EOF
                    if line and line[0] != '@':
                        linePieces = line.split('\t')
                        if len(linePieces) < 2:
                            return False
                        try:
                            check = int(linePieces[1])
                            if check + 2 != len(linePieces):
                                return False
                            for i in range( 2, len(linePieces)):
                                ival = int(linePieces[i])
                        except ValueError:
                            return False
                        count += 1
            if count > 0:
                return True
        except:
            pass
        return False

class GroupAbund( Otu ):
    file_ext = 'mothur.shared'
    MetadataElement( name="groups", default=[], desc="Group Names", readonly=True, visible=True, no_value=[] )
    def __init__(self, **kwd):
        Otu.__init__( self, **kwd )
        # self.column_names[0] = ['label']
        # self.column_names[1] = ['group']
        # self.column_names[2] = ['count']
    """
    def init_meta( self, dataset, copy_from=None ):
        Otu.init_meta( self, dataset, copy_from=copy_from )
    """
    def init_meta( self, dataset, copy_from=None ):
        Otu.init_meta( self, dataset, copy_from=copy_from )
    def set_meta( self, dataset, overwrite = True, skip=1, max_data_lines = 100000, **kwd ):
        # See if file starts with header line
        if dataset.has_data():
            label_names = set()
            group_names = set()
            data_lines = 0
            comment_lines = 0
            ncols = 0
            try:
                with open( dataset.file_name ) as fh:
                    line = fh.readline()
                    fields = line.strip().split('\t')
                    ncols = max(ncols,len(fields))
                    if fields[0] == 'label' and fields[1] == 'Group':
                        skip=1
                        comment_lines += 1
                    else:
                        skip=0
                        data_lines += 1
                        label_names.add(fields[0])
                        group_names.add(fields[1])
                    for line in fh:
                        data_lines += 1
                        fields = line.strip().split('\t')
                        ncols = max(ncols,len(fields))
                        label_names.add(fields[0])
                        group_names.add(fields[1])
                    # Set the discovered metadata values for the dataset
                    dataset.metadata.data_lines = data_lines
                    dataset.metadata.columns = ncols
                    dataset.metadata.labels = list( label_names )
                    dataset.metadata.labels.sort()
                    dataset.metadata.groups = list( group_names )
                    dataset.metadata.groups.sort()
                    dataset.metadata.skip = skip
            except:
                pass

    def sniff( self, filename, vals_are_int=False):
        """
        Determines whether the file is a otu (operational taxonomic unit) Shared format
        label<TAB>group<TAB>count[<TAB>value(1..n)]
        The first line is column headings as of Mothur v 1.20
        """
        try:
            with open( filename ) as fh:
                count = 0
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if not line:
                        break #EOF
                    if line and line[0] != '@':
                        linePieces = line.split('\t')
                        if len(linePieces) < 3:
                            return False
                        if count > 0 or linePieces[0] != 'label':
                            try:
                                check = int(linePieces[2])
                                if check + 3 != len(linePieces):
                                    return False
                                for i in range( 3, len(linePieces)):
                                    if vals_are_int:
                                        ival = int(linePieces[i])
                                    else:
                                        fval = float(linePieces[i])
                            except ValueError:
                                return False
                        count += 1
                        if count >= 5:
                            return True
            if count < 5 and count > 0:
                return True
        except:
            pass
        return False

class SecondaryStructureMap(Tabular):
    file_ext = 'mothur.map'
    def __init__(self, **kwd):
        """Initialize secondary structure map datatype"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['Map']

    def sniff( self, filename ):
        """
        Determines whether the file is a secondary structure map format
        A single column with an integer value which indicates the row that this row maps to.
        check you make sure is structMap[10] = 380 then structMap[380] = 10.
        """
        try:
            with open( filename ) as fh:
                line_num = 0
                rowidxmap = {}
                while True:
                    line = fh.readline()
                    line_num += 1
                    line = line.strip()
                    if not line:
                        break #EOF
                    if line:
                        try:
                            pointer = int(line)
                            if pointer > line_num:
                                rowidxmap[pointer] = line_num
                            elif pointer > 0 or line_num in rowidxmap:
                                if rowidxmap[line_num] != pointer:
                                    return False
                        except ValueError:
                            return False
        except:
            return False
        if line_num < 3:
            return False
        return True

class SequenceAlignment( Fasta ):
    file_ext = 'mothur.align'
    def __init__(self, **kwd):
        Fasta.__init__( self, **kwd )
        """Initialize AlignCheck datatype"""

    def sniff( self, filename ):
        """
        Determines whether the file is in Mothur align fasta format
        Each sequence line must be the same length
        """
        
        try:
            with open( filename ) as fh:
                len = -1
                while True:
                    line = fh.readline()
                    if not line:
                        break #EOF
                    line = line.strip()
                    if line: #first non-empty line
                        if line.startswith( '>' ):
                            #The next line.strip() must not be '', nor startwith '>'
                            line = fh.readline().strip()
                            if line == '' or line.startswith( '>' ):
                                break
                            if len < 0:
                                len = len(line)
                            elif len != len(line):
                                return False
                        else:
                            break #we found a non-empty line, but its not a fasta header
                if len > 0:
                    return True
        except:
            pass
        return False

class AlignCheck( Tabular ):
    file_ext = 'mothur.align.check'
    def __init__(self, **kwd):
        """Initialize AlignCheck datatype"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['name','pound','dash','plus','equal','loop','tilde','total']
        self.column_types = ['str','int','int','int','int','int','int','int']
        self.comment_lines = 1

    def set_meta( self, dataset, overwrite = True, **kwd ):
        # Tabular.set_meta( self, dataset, overwrite = overwrite, first_line_is_header = True, skip = 1 )
        data_lines = 0
        if dataset.has_data():
            dataset_fh = open( dataset.file_name )
            while True:
                line = dataset_fh.readline()
                if not line: break
                data_lines += 1
            dataset_fh.close()
        dataset.metadata.comment_lines = 1
        dataset.metadata.data_lines = data_lines - 1 if data_lines > 0 else 0
        dataset.metadata.column_names = self.column_names
        dataset.metadata.column_types = self.column_types

class AlignReport(Tabular):
    """
QueryName	QueryLength	TemplateName	TemplateLength	SearchMethod	SearchScore	AlignmentMethod	QueryStart	QueryEnd	TemplateStart	TemplateEnd	PairwiseAlignmentLength	GapsInQuery	GapsInTemplate	LongestInsert	SimBtwnQuery&Template
AY457915	501		82283		1525		kmer		89.07		needleman	5		501		1		499		499			2		0		0		97.6
    """
    file_ext = 'mothur.align.report'
    def __init__(self, **kwd):
        """Initialize AlignCheck datatype"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['QueryName','QueryLength','TemplateName','TemplateLength','SearchMethod','SearchScore',
                             'AlignmentMethod','QueryStart','QueryEnd','TemplateStart','TemplateEnd',
                             'PairwiseAlignmentLength','GapsInQuery','GapsInTemplate','LongestInsert','SimBtwnQuery&Template'
                             ]

class BellerophonChimera( Tabular ):
    file_ext = 'mothur.bellerophon.chimera'
    def __init__(self, **kwd):
        """Initialize AlignCheck datatype"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['Name','Score','Left','Right']

class SecondaryStructureMatch(Tabular):
    """
	name	pound	dash	plus	equal	loop	tilde	total
	9_1_12	42	68	8	28	275	420	872
	9_1_14	36	68	6	26	266	422	851
	9_1_15	44	68	8	28	276	418	873
	9_1_16	34	72	6	30	267	430	860
	9_1_18	46	80	2	36	261	
    """
    def __init__(self, **kwd):
        """Initialize SecondaryStructureMatch datatype"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['name','pound','dash','plus','equal','loop','tilde','total']

class DistanceMatrix( Text ):
    file_ext = 'mothur.dist'
    """Add metadata elements"""
    MetadataElement( name="sequence_count", default=0, desc="Number of sequences", readonly=True, visible=True, optional=True, no_value='?' )

    def init_meta( self, dataset, copy_from=None ):
        Text.init_meta( self, dataset, copy_from=copy_from )

    def set_meta( self, dataset, overwrite = True, skip = 0, **kwd ):
        Text.set_meta(self, dataset,overwrite = overwrite, skip = skip, **kwd )
        try:
            with open( dataset.file_name ) as fh:
                line = '@'
                while line[0] == '@':
                    line = fh.readline().strip().strip()
                dataset.metadata.sequence_count = int(line) 
        except Exception, e:
            log.warn("DistanceMatrix set_meta %s" % e)

class LowerTriangleDistanceMatrix(DistanceMatrix):
    file_ext = 'mothur.lower.dist'
    def __init__(self, **kwd):
        """Initialize secondary structure map datatype"""
        DistanceMatrix.__init__( self, **kwd )

    def init_meta( self, dataset, copy_from=None ):
        DistanceMatrix.init_meta( self, dataset, copy_from=copy_from )

    def sniff( self, filename ):
        """
        Determines whether the file is a lower-triangle distance matrix (phylip) format
        The first line has the number of sequences in the matrix.
        The remaining lines have the sequence name followed by a list of distances from all preceeding sequences
                5
                U68589
                U68590	0.3371
                U68591	0.3609	0.3782
                U68592	0.4155	0.3197	0.4148
                U68593	0.2872	0.1690	0.3361	0.2842
        """
        try:
            with open( filename ) as fh:
                count = 0
                line = fh.readline()
                sequence_count = int(line.strip())
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if not line:
                        break #EOF
                    if line:
                        # Split into fields
                        linePieces = line.split('\t')
                        # Each line should have the same number of
                        # fields as the Python line index
                        linePieces = line.split('\t')
                        if len(linePieces) != (count + 1):
                            return False
                        # Distances should be floats
                        try:
                            for linePiece in linePieces[2:]:
                                check = float(linePiece)
                        except ValueError:
                            return False
                        # Increment line counter
                        count += 1
                        # Only check first 5 lines
                        if count == 5:
                            return True
            if count < 5 and count > 0:
                return True
        except:
            pass
        return False

class SquareDistanceMatrix(DistanceMatrix):
    file_ext = 'mothur.square.dist'

    def __init__(self, **kwd):
        DistanceMatrix.__init__( self, **kwd )
    def init_meta( self, dataset, copy_from=None ):
        DistanceMatrix.init_meta( self, dataset, copy_from=copy_from )

    def sniff( self, filename ):
        """
        Determines whether the file is a square distance matrix (Column-formatted distance matrix) format
        The first line has the number of sequences in the matrix.
        The following lines have the sequence name in the first column plus a column for the distance to each sequence 
        in the row order in which they appear in the matrix.
               3
               U68589  0.0000  0.3371  0.3610
               U68590  0.3371  0.0000  0.3783
               U68590  0.3371  0.0000  0.3783
        """
        try:
            with open( filename ) as fh:
                count = 0
                while True:
                    line = fh.readline().strip()
                    if not line:
                        break #EOF
                    if line[0] != '@':
                        if count == 0:
                            seq_cnt = int(line)
                            col_cnt = seq_cnt + 1
                        else:
                            linePieces = line.split('\t')
                            if len(linePieces) != col_cnt :
                                return False
                            try:
                                for i in range(1, col_cnt):
                                    check = float(linePieces[i])
                            except ValueError:
                                return False
                        count += 1
            if count > 2:
                return True
        except:
            pass
        return False

class PairwiseDistanceMatrix(DistanceMatrix,Tabular):
    file_ext = 'mothur.pair.dist'
    def __init__(self, **kwd):
        """Initialize secondary structure map datatype"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['Sequence','Sequence','Distance']
        self.column_types = ['str','str','float']
    def set_meta( self, dataset, overwrite = True, skip = None, **kwd ):
        Tabular.set_meta(self, dataset,overwrite = overwrite, skip = skip, **kwd )

    def sniff( self, filename ):
        """
        Determines whether the file is a pairwise distance matrix (Column-formatted distance matrix) format
        The first and second columns have the sequence names and the third column is the distance between those sequences.
        """
        try:
            with open( filename ) as fh:
                count = 0
                all_ints = True
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if not line:
                        break #EOF
                    if line and line[0] != '@':
                        linePieces = line.split('\t')
                        if len(linePieces) != 3:
                            return False
                        try:
                            check = float(linePieces[2])
                            try:
                                # See if it's also an integer
                                check_int = int(linePieces[2])
                            except ValueError:
                                # At least one value is not an
                                # integer
                                all_ints = False
                        except ValueError:
                            return False
                        count += 1
                        if count == 5:
                            if not all_ints:
                                return True
                            else:
                                return False
            if count < 5 and count > 0:
                if not all_ints:
                    return True
                else:
                    return False
        except:
            pass
        return False


class Names(Tabular):
    file_ext = 'mothur.names'
    def __init__(self, **kwd):
        """
        # http://www.mothur.org/wiki/Name_file
        Name file shows the relationship between a representative sequence(col 1)  and the sequences(comma-separated) it represents(col 2)
        """
        Tabular.__init__( self, **kwd )
        self.column_names = ['name','representatives']
        self.columns = 2

class Summary(Tabular):
    file_ext = 'mothur.summary'
    def __init__(self, **kwd):
        """summarizes the quality of sequences in an unaligned or aligned fasta-formatted sequence file"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['seqname','start','end','nbases','ambigs','polymer']
        self.columns = 6

class Group(Tabular):
    file_ext = 'mothur.groups'
    MetadataElement( name="groups", default=[], desc="Group Names", readonly=True, visible=True, no_value=[] )
    def __init__(self, **kwd):
        """
        # http://www.mothur.org/wiki/Groups_file
        Group file assigns sequence (col 1)  to a group (col 2)
        """
        Tabular.__init__( self, **kwd )
        self.column_names = ['name','group']
        self.columns = 2
    def set_meta( self, dataset, overwrite = True, skip = None, max_data_lines = None, **kwd ):
        Tabular.set_meta(self, dataset, overwrite, skip, max_data_lines)
        group_names = set() 
        try:
            with open( dataset.file_name ) as fh:
                for line in fh:
                    fields = line.strip().split('\t')
                    try:
                        group_names.add(fields[1])
                    except IndexError:
                        # Ignore missing 2nd column
                        pass
                dataset.metadata.groups = []
                dataset.metadata.groups += group_names
        except:
            pass

class AccNos(Tabular):
    file_ext = 'mothur.accnos'
    def __init__(self, **kwd):
        """A list of names"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['name']
        self.columns = 1

class Oligos( Text ):
    file_ext = 'mothur.oligos'

    def sniff( self, filename ):
        """
        # http://www.mothur.org/wiki/Oligos_File
        Determines whether the file is a otu (operational taxonomic unit) format
        """
        try:
            with open( filename ) as fh:
                count = 0
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if not line:
                        break #EOF
                    else:
                        if line[0] != '#':
                            linePieces = line.split('\t')
                            if len(linePieces) == 2 and re.match('forward|reverse',linePieces[0]):
                                count += 1
                                continue
                            elif len(linePieces) == 3 and re.match('barcode',linePieces[0]):
                                count += 1
                                continue
                            else:
                                return False
                            if count > 20:
                                return True
                if count > 0:
                    return True
        except:
            pass
        return False

class Frequency(Tabular):
    file_ext = 'mothur.freq'
    def __init__(self, **kwd):
        """A list of names"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['position','frequency']
        self.column_types = ['int','float']

    def sniff( self, filename ):
        """
        Determines whether the file is a frequency tabular format for chimera analysis
        #1.14.0
        0	0.000
        1	0.000
        ...
        155	0.975
        """
        try:
            with open( filename ) as fh:
                count = 0
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if not line:
                        break #EOF
                    else:
                        if count == 0 and line[0] != '#':
                            return False
                        if line[0] != '#':
                            linePieces = line.split('\t')
                            if len(linePieces) != 2:
                                return False
                            try:
                                i = int(linePieces[0])
                                f = float(linePieces[1])
                            except:
                                return False
                        count += 1
                if count > 0:
                    return True
        except:
            pass
        return False

class Quantile(Tabular):
    file_ext = 'mothur.quan'
    MetadataElement( name="filtered", default=False, no_value=False, optional=True , desc="Quantiles calculated using a mask", readonly=True)
    MetadataElement( name="masked", default=False, no_value=False, optional=True , desc="Quantiles calculated using a frequency filter", readonly=True)
    def __init__(self, **kwd):
        """Quantiles for chimera analysis"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['num','ten','twentyfive','fifty','seventyfive','ninetyfive','ninetynine']
        self.column_types = ['int','float','float','float','float','float','float']
    def sniff( self, filename ):
        """
        Determines whether the file is a quantiles tabular format for chimera analysis
        1	0	0	0	0	0	0
        2       0.309198        0.309198        0.37161 0.37161 0.37161 0.37161
        3       0.510982        0.563213        0.693529        0.858939        1.07442 1.20608
        ...
        """
        try:
            with open( filename ) as fh:
                count = 0
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if not line:
                        break #EOF
                    else:
                        if line[0] != '#':
                            try:
                                linePieces = line.split('\t')
                                i = int(linePieces[0])
                                f = float(linePieces[1])
                                f = float(linePieces[2])
                                f = float(linePieces[3])
                                f = float(linePieces[4])
                                f = float(linePieces[5])
                                f = float(linePieces[6])
                                count += 1
                                continue
                            except:
                                return False
                            if count > 10:
                                return True
                if count > 0:
                    return True
        except:
            pass
        return False

class LaneMask(Text):
    file_ext = 'mothur.filter'

    def sniff( self, filename ):
        """
        Determines whether the file is a lane mask filter:  1 line consisting of zeros and ones.
        """
        try:
            with open( filename ) as fh:
                count=0
                while True:
                    line = fh.readline().strip()
                    if not line:
                        break #EOF
                    else:
                        count+=1
                        if not re.match('^[01]+$',line):
                            return False
                if count != 1:
                    return False
                return True
        except:
            pass
        return False

class CountTable(Tabular):
    MetadataElement( name="groups", default=[], desc="Group Names", readonly=True, visible=True, no_value=[] )
    file_ext = 'mothur.count_table'

    def __init__(self, **kwd):
        """
        # http://www.mothur.org/wiki/Count_File
        A table with first column names and following columns integer counts
        # Example 1:
        Representative_Sequence total   
        U68630  1
        U68595  1
        U68600  1
        # Example 2 (with group columns):
        Representative_Sequence total   forest  pasture 
        U68630  1       1       0       
        U68595  1       1       0       
        U68600  1       1       0       
        U68591  1       1       0       
        U68647  1       0       1       
        """
        Tabular.__init__( self, **kwd )
        self.column_names = ['name','total']

    def set_meta( self, dataset, overwrite = True, skip = 1, max_data_lines = None, **kwd ):
        try:
            data_lines = 0;
            with open( dataset.file_name ) as fh:
                line = fh.readline()
                if line:
                    line = line.strip()
                    colnames = line.split() 
                    if len(colnames) > 1:
                        dataset.metadata.columns = len( colnames )
                        if len(colnames) > 2:
                            dataset.metadata.groups = colnames[2:]
                        column_types = ['str']
                        for i in range(1,len(colnames)):
                            column_types.append('int')
                        dataset.metadata.column_types = column_types
                        dataset.metadata.comment_lines = 1
                while line:
                    line = fh.readline()
                    if not line: break
                    data_lines += 1
                dataset.metadata.data_lines = data_lines
        except:
            pass

class RefTaxonomy(Tabular):
    file_ext = 'mothur.ref.taxonomy'
    """
        # http://www.mothur.org/wiki/Taxonomy_outline
        A table with 2 or 3 columns:
        - SequenceName
        - Taxonomy (semicolon-separated taxonomy in descending order)
        - integer ?
        Example: 2-column ( http://www.mothur.org/wiki/Taxonomy_outline )
          X56533.1        Eukaryota;Alveolata;Ciliophora;Intramacronucleata;Oligohymenophorea;Hymenostomatida;Tetrahymenina;Glaucomidae;Glaucoma;
          X97975.1        Eukaryota;Parabasalidea;Trichomonada;Trichomonadida;unclassified_Trichomonadida;
          AF052717.1      Eukaryota;Parabasalidea;
        Example: 3-column ( http://vamps.mbl.edu/resources/databases.php )
          v3_AA008	Bacteria;Firmicutes;Bacilli;Lactobacillales;Streptococcaceae;Streptococcus	5
          v3_AA016	Bacteria	120
          v3_AA019	Archaea;Crenarchaeota;Marine_Group_I	1
    """
    def __init__(self, **kwd):
        Tabular.__init__( self, **kwd )
        self.column_names = ['name','taxonomy']

    def sniff( self, filename ):
        """
        Determines whether the file is a Reference Taxonomy
        """
        try:
            pat = '^([^ \t\n\r\x0c\x0b;]+([(]\\d+[)])?(;[^ \t\n\r\x0c\x0b;]+([(]\\d+[)])?)*(;)?)$'
            with open( filename ) as fh:
                count = 0
                # VAMPS  taxonomy files do not require a semicolon after the last taxonomy category
                # but assume assume the file will have some multi-level taxonomy assignments
                found_semicolons = False
                while True:
                    line = fh.readline()
                    if not line:
                        break #EOF
                    line = line.strip()
                    if line:
                        fields = line.split('\t')
                        if not (2 <= len(fields) <= 3):
                            return False
                        if not re.match(pat,fields[1]):
                            return False
                        if not found_semicolons and str(fields[1]).count(';') > 0:
                            found_semicolons = True
                        if len(fields) == 3:
                            check = int(fields[2])
                        count += 1
                        if count > 100:
                            break
                if count > 0:
                    # This will be true if at least one entry
                    # has semicolons in the 2nd column
                    return found_semicolons
        except:
            pass
        return False

class ConsensusTaxonomy(Tabular):
    file_ext = 'mothur.cons.taxonomy'
    def __init__(self, **kwd):
        """A list of names"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['OTU','count','taxonomy']

class TaxonomySummary(Tabular):
    file_ext = 'mothur.tax.summary'
    def __init__(self, **kwd):
        """A Summary of taxon classification"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['taxlevel','rankID','taxon','daughterlevels','total']

class Phylip(Text):
    file_ext = 'mothur.phy'

    def sniff( self, filename ):
        """
        Determines whether the file is in Phylip format (Interleaved or Sequential)
        The first line of the input file contains the number of species and the
        number of characters, in free format, separated by blanks (not by
        commas). The information for each species follows, starting with a
        ten-character species name (which can include punctuation marks and blanks),
        and continuing with the characters for that species.
        http://evolution.genetics.washington.edu/phylip/doc/main.html#inputfiles
        Interleaved Example:
            6   39
        Archaeopt CGATGCTTAC CGCCGATGCT
        HesperorniCGTTACTCGT TGTCGTTACT
        BaluchitheTAATGTTAAT TGTTAATGTT
        B. virginiTAATGTTCGT TGTTAATGTT
        BrontosaurCAAAACCCAT CATCAAAACC
        B.subtilisGGCAGCCAAT CACGGCAGCC
        
        TACCGCCGAT GCTTACCGC
        CGTTGTCGTT ACTCGTTGT
        AATTGTTAAT GTTAATTGT
        CGTTGTTAAT GTTCGTTGT
        CATCATCAAA ACCCATCAT
        AATCACGGCA GCCAATCAC
        """
        try:
            with open( filename ) as fh:
                # counts line
                line = fh.readline().strip()
                linePieces = line.split()
                count = int(linePieces[0])
                seq_len = int(linePieces[1])
                # data lines
                """
                TODO check data lines
                while True:
                    line = fh.readline()
                    # name is the first 10 characters
                    name = line[0:10]
                    seq = line[10:].strip()
                    # nucleic base or amino acid 1-char designators (spaces allowed)
                    bases = ''.join(seq.split())
                    # float per base (each separated by space)
                """
                return True
        except:
            pass
        return False


class Axes(Tabular):
    file_ext = 'mothur.axes'

    def __init__(self, **kwd):
        """Initialize axes datatype"""
        Tabular.__init__( self, **kwd )
    def sniff( self, filename ):
        """
        Determines whether the file is an axes format
        The first line may have column headings.
        The following lines have the name in the first column plus float columns for each axis.
		==> 98_sq_phylip_amazon.fn.unique.pca.axes <==
		group   axis1   axis2
		forest  0.000000        0.145743        
		pasture 0.145743        0.000000        
		
		==> 98_sq_phylip_amazon.nmds.axes <==
        		axis1   axis2   
		U68589  0.262608        -0.077498       
		U68590  0.027118        0.195197        
		U68591  0.329854        0.014395        
        """
        try:
            with open( filename ) as fh:
                count = 0
                line = fh.readline()
                line = line.strip()
                col_cnt = None
                all_integers = True
                while True:
                    line = fh.readline()
                    line = line.strip()
                    if not line:
                        break #EOF
                    if line:
                        fields = line.split('\t')
                        if col_cnt == None:  # ignore values in first line as they may be column headings
                            col_cnt = len(fields)
                            # There should be at least 2 columns
                            if col_cnt < 2:
                                return False
                        else:  
                            if len(fields) != col_cnt :
                                return False
                            try:
                                for i in range(1, col_cnt):
                                    check = float(fields[i])
                                    # Check abs value is <= 1.0
                                    if abs(check) > 1.0:
                                        return False
                                    # Also test for whether value is an integer
                                    try:
                                        check = int(fields[i])
                                    except ValueError:
                                        all_integers = False
                            except ValueError:
                                return False
                            count += 1
                        if count > 10:
                            break
                if count > 0:
                    if not all_integers:
                        # At least one value was a float
                        return True
                    else:
                        return False
        except:
            pass
        return False

class SffFlow(Tabular):
    MetadataElement( name="flow_values", default="", no_value="", optional=True , desc="Total number of flow values", readonly=True)
    MetadataElement( name="flow_order", default="TACG", no_value="TACG", desc="Total number of flow values", readonly=False)
    file_ext = 'mothur.sff.flow'
    """
        # http://www.mothur.org/wiki/Flow_file
        The first line is the total number of flow values - 800 for Titanium data. For GS FLX it would be 400. 
        Following lines contain:
        - SequenceName
        - the number of useable flows as defined by 454's software
        - the flow intensity for each base going in the order of TACG.
        Example:
          800
          GQY1XT001CQL4K 85 1.04 0.00 1.00 0.02 0.03 1.02 0.05 ...
          GQY1XT001CQIRF 84 1.02 0.06 0.98 0.06 0.09 1.05 0.07 ... 
          GQY1XT001CF5YW 88 1.02 0.02 1.01 0.04 0.06 1.02 0.03 ...
    """
    def __init__(self, **kwd):
        Tabular.__init__( self, **kwd )

    def set_meta( self, dataset, overwrite = True, skip = 1, max_data_lines = None, **kwd ):
        Tabular.set_meta(self, dataset, overwrite, 1, max_data_lines)
        try:
            with open( dataset.file_name ) as fh:
                line = fh.readline()
                line = line.strip()
                flow_values = int(line)
                dataset.metadata.flow_values = flow_values
        except:
            pass

    def make_html_table( self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        comments = []
        try:
            # Generate column header
            out.append('<tr>')
            out.append( '<th>%d. Name</th>' % 1 )
            out.append( '<th>%d. Flows</th>' % 2 )
            for i in range( 3, dataset.metadata.columns+1 ):
                base = dataset.metadata.flow_order[(i+1)%4]
                out.append( '<th>%d. %d %s</th>' % (i-2,base) )
            out.append('</tr>')
            out.append( self.make_html_peek_rows( dataset, skipchars=skipchars ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % str( exc )
        return out

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
