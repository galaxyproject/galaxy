
import sys, os, logging

log = logging.getLogger(__name__)

class DynamicOptions( object ):
    """Handles dynamically generated SelectToolParameter options"""
    def __init__( self, elem  ):
        self.data_ref = elem.get( 'data_ref', None)
        self.param_ref = elem.get( 'param_ref', None)
        self.from_file = elem.get( 'from_file', None )
        self.func = elem.get( 'func', None )
        assert self.func is not None, "Value for option generator function not found"
        self.func_params = elem.findall( 'func_param' )
        self.no_data_option = ( 'No data available for this build', 'None', True )
    def get_dataset( self, trans, other_values ):
        # No value indicates a configuration error, the named DataToolParameter must preceed this parameter in the tool config
        assert self.data_ref in other_values, "Value for associated DataToolParameter not found"
        # Get the value of the associated DataToolParameter (a dataset)
        dataset = other_values[ self.data_ref ]
        if dataset is None or dataset == '':
            """
            Both of these values indicate that no dataset is selected.  However, 'None' indicates that the dataset is optional 
            while '' indicates that it is not. Currently dynamically generated select lists do not work well with optional datasets.
            """
            return None
        # TODO: this can be eliminated after Dan's script is run.
        dataset.set_meta()
        return dataset
    def get_param_ref( self, trans, other_values ):
        if self.param_ref is None: return None
        else:
            assert self.param_ref in other_values, "Value for associated parameter not found"
            return other_values[ self.param_ref ]

    """
    TODO: the following functions should be generalized so that they are not specific to
    certain tools (e.g., encode).  We may need to standardize data file formats to be able to do this.
    Comments in the functions show the tools that use them along with associated data files, if any
    """
    def get_options_for_build( self, trans, other_values ):
        """
        Used by the following tools:
        random_intervals1 - associated data file: /depot/data2/galaxy/regions.loc
        phastOdds_for_intervals - associated data file: /depot/data2/galaxy/phastOdds.loc
        aggregate_scores_in_intervals2 - associated data file: /depot/data2/galaxy/binned_scores.loc        
        """
        legal_values = set()
        options = []
        dataset = self.get_dataset( trans, other_values )
        if dataset is None:
            return legal_values, options
        def load_from_file_for_build():
            d = {}
            for line in open( self.from_file ):
                line = line.rstrip( '\r\n' )
                if line and not line.startswith( '#' ):
                    try:
                        fields = line.split( "\t" )
                        if not fields[0] in d: 
                            d[ fields[0] ] = []
                        d[ fields[0] ].append( (fields[1], fields[2]) )
                    except:
                        continue
            return d
        d = load_from_file_for_build()
        if dataset.dbkey in d:
            for (key, val) in d[ dataset.dbkey ]:
                options.append( (key, val, False) )
                legal_values.add( val )
        return legal_values, options

    def get_options_for_build_2( self, trans, other_values ):
        """
        Used by the following tools:
        axt_to_concat_fasta - associated data file: static/ucsc/builds.txt
        axt_to_fasta - associated data file: static/ucsc/builds.txt
        axt_to_lav_1 - - associated data file: static/ucsc/builds.txt
        """
        def load_from_file_for_build_2():
            legal_values = set()
            options = []
            for line in open( self.from_file ):
                line = line.rstrip( '\r\n' )
                if line and not line.startswith( '#' ):
                    try:
                        fields = line.split( '\t' )
                        options.append( (fields[1], fields[0], False) )
                        legal_values.add( fields[0] )
                    except: continue
            if len( options ) < 1:
                options.append( ('unspecified', '?', True ) )
                legal_values.add( '?' )
            return legal_values, options
        return load_from_file_for_build_2()

    def get_options_for_build_3( self, trans, other_values ):
        # FIXME: We need a database of descriptive names corresponding to dbkeys.
        #        We need to resolve the musMusX <--> mmX confusion
        """
        Used by the following tools:
        Extract blastz alignments1 - associated data file: /depot/data2/galaxy/alignseq.loc
        """
        legal_values = set()
        options = []
        dataset = self.get_dataset( trans, other_values )
        if dataset is None:
            return legal_values, options
        def load_from_file_for_build_3():
            d = {}
            for line in open( self.from_file ):
                line = line.rstrip( '\r\n' )
                if line and not line.startswith( '#' ):
                    fields = line.split()
                    if fields[0].strip() == "align":
                        try: d[ fields[1] ].append( fields[2] )
                        except: d[ fields[1] ] = [ fields[2] ]
            return d
        d = load_from_file_for_build_3()
        build = dataset.dbkey
        if build[ 0:2 ] == "mm": build = build.replace( 'mm', 'musMus' )
        if build[ 0:2 ] == "rn": build = build.replace( 'rn', 'ratNor' )
        if build in d:
            for val in d[ build ]:
                options.append( ( val, val, False ) )
                legal_values.add( val )
        return legal_values, options        

    def load_from_file_for_maf( self ):
        d = {}
        for line in open( self.from_file ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split('\t')
                try:
                    maf_desc = fields[0]
                    maf_uid = fields[1]
                    builds = fields[2]
                    build_list = []
                    split_builds = builds.split( ',' )
                    for build in split_builds:
                        this_build = build.split( '=' )[0]
                        build_list.append( this_build )
                    paths = fields[3]
                    d[maf_uid] = {}
                    d[maf_uid]['description'] = maf_desc
                    d[maf_uid]['builds'] = build_list
                except: continue
        return d

    def get_options_for_maf( self, trans, other_values ):
        """
        Used by the following tools:
        maf_stats1 - associated data file: /depot/data2/galaxy/maf_index.loc
        GeneBed_Maf_Fasta1 - associated data file: /depot/data2/galaxy/maf_index.loc
        """
        legal_values = set()
        options = []
        dataset = self.get_dataset( trans, other_values )
        if dataset is None:
            return legal_values, options
        d = self.load_from_file_for_maf()
        for i, key in enumerate( d ):
            if dataset.dbkey in d[key]['builds']:
                if i == 0: options.append( ( d[key]['description'], key, True ) )
                else: options.append( ( d[key]['description'], key, False ) )
                legal_values.add( key )
        if len( options ) < 1:
            options.append( self.no_data_option )
            legal_values.add( 'None' )
        return legal_values, options

    def get_options_for_species( self, trans, other_values ):
        """
        Used by the following tools:
        MAF_Limit_To_Species1 - no associated data file
        MAF_Thread_For_Species1 - no associated data file
        MAF_To_BED1 - no associated data file
        MAF_To_Fasta_Concat1 - no associated data file
        
        TODO: multiple tools with same ID
        MAF_To_Fasta1 (maf_to_fasta_multiple_sets.xml) - no associated data file
        MAF_To_Fasta1 (maf_to_fasta.xml) - no associated data file  
        GeneBed_Maf_Fasta_User1 - no associated data file 
        """
        legal_values = set()
        options = []
        dataset = self.get_dataset( trans, other_values )
        if dataset is None:
            return legal_values, options
        for species in dataset.metadata.species:
            options.append( ( species, species, False ) )
            legal_values.add( species )
        return legal_values, options

    def get_options_for_species_for_maf( self, trans, other_values ):
        """
        Used by the following tools:
        GeneBed_Maf_Fasta1 - associated data file: /depot/data2/galaxy/maf_index.loc
        """
        legal_values = set()
        options = []
        assert len( self.func_params ) == 1, "Value for 'maf_source' not found"
        for func_param in self.func_params:
            if func_param.get( 'name' ).strip() == 'maf_source':
                maf_source = func_param.get( 'value' ).strip()
        assert maf_source, "Value for 'maf_source' not properly set"
        if maf_source == 'cached':
            d = self.load_from_file_for_maf()
            maf_uid = self.get_param_ref( trans, other_values )
            assert maf_uid, "Value for maf_uid not found"
            if maf_uid == 'None':
                options.append( ( '<b>build not set, click pencil icon in your history item to associate a build</b>', 'None', True ) )
                legal_values.add( 'None' )
                return legal_values, options
            for key in d[maf_uid]['builds']:
                options.append( (key, key, False) )
                legal_values.add( key )
            if len( options ) < 1:
                options.append( ( 'No data available for this configuration', 'None', True ) )
                legal_values.add( 'None' )
        else: # maf_source == 'user'
            dataset = self.get_dataset( trans, other_values )
            if dataset is None:
                options.append( ("<B>You must wait for the MAF file to be created before you can use this tool.</B>", 'None', True) )
                legal_values.add( 'None' )
                return legal_values, options
            for species in dataset.metadata.species:
                options.append( ( species, species, False ) )
                legal_values.add( species )
        return legal_values, options

    def get_options_for_features( self, trans, other_values ):
        """
        Used by the following tools: 
        Extract_features1 - no associated data file (tool uses data from selected dataset)
        """ 
        def get_unique_elems( elems ): 
            seen = set()
            return [x for x in elems if x not in seen and not seen.add(x)]

        assert len( self.func_params ) == 1, "Value for 'index' not found"
        for func_param in self.func_params:
            if func_param.get( 'name' ).strip() == 'index':
                index = func_param.get( 'value' ).strip()
        assert index is not None, "Value for 'index' not properly set"
        legal_values = set()
        options = []
        elem_list = []
        dataset = self.get_dataset( trans, other_values )
        if dataset is None:
            return legal_values, options
        datafile = dataset.get_file_name()
        try:
            in_file = open( datafile, "r" )
        except:
            options.append( ( "Input datafile doesn't exist", "None", True ) )
            legal_values.add( 'None' )
            return legal_values, options
        try:
            for line in in_file:
                line = line.rstrip( "\r\n" )
                if line and not line.startswith( '#' ):
                    elems = line.split( '\t' )
                    elem_list.append( elems[int( index )] )
        except: pass
        in_file.close()
        if not( elem_list ):
            options.append( ( 'No elements to display, please choose another column', 'None', True ) )
            legal_values.add( 'None' )
            return legal_values, options
        elem_list = get_unique_elems( elem_list )
        for elem in elem_list:
            options.append( ( elem, elem, False ) )
            legal_values.add( elem )
        return legal_values, options

    def get_options_for_encode( self, trans, other_values ):
        """
        Used by the following tools:
        encode_import_all_latest_datasets1 - associated data file: /depot/data2/galaxy/encode_datasets.loc
        encode_import_chromatin_and_chromosomes1 - associated data file: /depot/data2/galaxy/encode_datasets.loc
        encode_import_gencode1 - associated data file: /depot/data2/galaxy/encode_datasets.loc
        encode_import_genes_and_transcripts1 - associated data file: /depot/data2/galaxy/encode_datasets.loc
        encode_import_multi-species_sequence_analysis1 - associated data file: /depot/data2/galaxy/encode_datasets.loc
        encode_import_transcription_regulation1 - associated data file: /depot/data2/galaxy/encode_datasets.loc
        """
        assert len( self.func_params ) == 2, "Values for 'build' and 'encode group' not found"
        for func_param in self.func_params:
            if func_param.get( 'name' ).strip() == 'build':
                build = func_param.get( 'value' ).strip()
            elif func_param.get( 'name' ).strip() == 'encode_group':
                encode_group = func_param.get( 'value' ).strip()
        assert build and encode_group, "Values for 'build' and 'encode group' not properly set"
        legal_values = set()
        options = []
        def load_from_file_for_encode():
            encode_sets = {}
            legal_values = set()
            for line in open( self.from_file ):
                line = line.rstrip( '\r\n' )
                if line and not line.startswith( '#' ):
                    try:
                        fields = line.split( "\t" )
                        encode_group = fields[0]
                        build = fields[1]
                        description = fields[2]
                        uid = fields[3]
                        path = fields[4]
                        try: file_type = fields[5]
                        except: file_type = "bed"
                        #TODO: will remove this later, when galaxy can handle gff files
                        if file_type != "bed": continue
                        if not os.path.isfile(path): continue
                    except:
                        continue
                    try: temp = encode_sets[encode_group]
                    except: encode_sets[encode_group] = {}
                    try:
                        encode_sets[encode_group][build].append((description, uid, False))
                        legal_values.add( uid )
                    except:
                        encode_sets[encode_group][build]=[]
                        encode_sets[encode_group][build].append((description, uid, False))
                        legal_values.add( uid )
            #Order by description and date, highest date on top and bold
            for group in encode_sets:
                for build in encode_sets[ group ]:
                    ordered_build = []
                    for description, uid, selected in encode_sets[ group ][ build ]:
                        item = {}
                        item['date']=0
                        item['description'] = ""
                        item['uid'] = uid
                        item['selected'] = selected
                        item['partitioned'] = False
                        if description[-21:] == '[gencode_partitioned]':
                            item['date'] = description[-31:-23]
                            item['description'] = description[0:-32]
                            item['partitioned'] = True
                        else:
                            item['date'] = description[-9:-1]
                            item['description'] = description[0:-10]
                            
                        for i in range(len(ordered_build)):
                            ordered_description, ordered_uid, ordered_selected, ordered_item = ordered_build[i]
                            if item['description'] < ordered_item['description']:
                                ordered_build.insert( i, (description, uid, selected, item) )
                                break
                            if item['description'] == ordered_item['description'] and item['partitioned'] == ordered_item['partitioned']:
                                if int(item['date']) > int(ordered_item['date']):
                                    ordered_build.insert( i, (description, uid, selected, item) )
                                    break
                        else: ordered_build.append( (description, uid, selected, item) )
                    last_desc = None
                    last_partitioned = None
                    for i in range(len(ordered_build)) :
                        description, uid, selected, item = ordered_build[i]
                        if item['partitioned'] != last_partitioned or last_desc != item['description']:
                            last_desc = item['description']
                            description = "<b>" + description + "</b>"
                        else:
                            last_desc = item['description']
                        last_partitioned = item['partitioned']
                        encode_sets[group][build][i] = (description, uid, selected)        
            return legal_values, encode_sets
        legal_values, d = load_from_file_for_encode()
        if len( d ) < 1:
            options.append( self.no_data_option )
            legal_values.add( 'None' )
        else:
            try: 
                options = d[encode_group][build][0:]
            except:
                options.append( self.no_data_option )
                legal_values.add( 'None' )
        return legal_values, options
