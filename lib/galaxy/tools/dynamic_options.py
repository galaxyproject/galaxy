
import sys, os, logging

log = logging.getLogger(__name__)

class DynamicOptions( object ):
    """Handles dynamically generated SelectToolParameter options"""
    def __init__( self, elem  ):
        # FIXME: Pushing these things in as options ends up being pretty ugly. 
        # We should find a way to make this work through the validation mechanism.
        self.no_data_option = ( 'No data available for this build', 'None', True )
        self.from_file = elem.get( 'from_file', None )
        if elem.tag == 'select_options':
            self.data_ref = elem.get( 'data_ref', None )
            self.param_ref = elem.get( 'param_ref', None )
            self.func = elem.get( 'func', None )
            assert self.func is not None, "Value for option generator function not found"
            self.func_params = elem.findall( 'func_param' )
        else: #elem.tag =='options'
            self.name_col = int( elem.get( 'name_col', None ) )
            assert self.name_col is not None, "Value for option generator name_col not found"
            self.value_col = int( elem.get( 'value_col', None ) )
            assert self.value_col is not None, "Value for option generator value_col not found"
            self.filters = elem.findall( 'filter' )
            for filter in self.filters:
                filter_type = filter.get( 'type', None )
                assert filter_type is not None, "type attribute missing from filter"
                filter_type = filter_type.strip()
                if filter_type == 'data_meta':
                    # We're using metadata information from self.data_ref
                    self.data_ref = filter.get( 'data_ref', None )
        #FIXME: this attr is used only by microbial import, so shouldn't be at this level
        self.microbe_info = None
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
        return dataset
    def get_param_value( self, trans, other_values ):
        if self.param_ref is None: return None
        assert self.param_ref in other_values, "Value for associated parameter %s not found" %self.param_ref.name
        return other_values[ self.param_ref ]
    def load_from_file( self, key=None, value=None, col=None, sep='\t' ):
        """key: build, value: dbkey, col: 0"""
        options = []
        d = {}
        tool_type = None
                        
        for line in open( self.from_file ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                try:
                    fields = line.split( sep )
                    if key == 'build':
                        if col is not None:
                            if fields[ col ].strip() == 'align': # tool is: Extract blastz alignments1
                                tool_type = 'blastz'
                                try: d[ fields[ self.name_col ] ].append( fields[ self.value_col ] )
                                except: d[ fields[ self.name_col ] ] = [ fields[ self.value_col ] ]
                            else: # tool is one of: aggregate_scores_in_intervals2, phastOdds_for_intervals, random_intervals1
                                tool_type = 'intervals'
                                if not fields[ col ] in d: 
                                    d[ fields[ col ] ] = []
                                d[ fields[ col ] ].append( (fields[ self.name_col ], fields[ self.value_col ]) )
                        else:
                            options.append( (fields[ self.name_col ], fields[ self.value_col ], False) )
                    elif key == 'some future key':
                        pass
                    else: # tool is one of: axt_to_concat_fasta, axt_to_fasta, axt_to_lav_1
                        options.append( (fields[ self.name_col ], fields[ self.value_col ], False) )
                except: continue
        if tool_type == 'blastz':
            # FIXME: We need a database of descriptive names corresponding to dbkeys.
            #        We need to resolve the musMusX <--> mmX confusion
            if value[ 0:2 ] == "mm": value = value.replace( 'mm', 'musMus' )
            if value[ 0:2 ] == "rn": value = value.replace( 'rn', 'ratNor' )
            if value in d:
                for val in d[ value ]:
                    options.append( ( val, val, False ) )
        elif tool_type == 'intervals':
            if value in d:
                for (key, val) in d[ value ]:
                    options.append( (key, val, False) )
        else: # tool_type is some future tool type
            pass
        if key == 'build' and not options: return [ ('unspecified', '?', True ) ]
        return options
    def get_options( self, trans, other_values ):
        """
        Used by the following tools so far...
        random_intervals1 - associated data file: /depot/data2/galaxy/regions.loc
        phastOdds_for_intervals - associated data file: /depot/data2/galaxy/phastOdds.loc
        aggregate_scores_in_intervals2 - associated data file: /depot/data2/galaxy/binned_scores.loc  
        axt_to_concat_fasta - associated data file: static/ucsc/builds.txt
        axt_to_fasta - associated data file: static/ucsc/builds.txt
        axt_to_lav_1 - - associated data file: static/ucsc/builds.txt
        Extract blastz alignments1 - associated data file: /depot/data2/galaxy/alignseq.loc   
        """
        # Check for filters first and process any that we find
        for filter in self.filters:
            filter_type = filter.get( 'type', None )
            assert filter_type is not None, "type attribute missing from filter"
            filter_type = filter_type.strip()
            if filter_type == 'data_meta':
                # We're using metadata information from self.data_ref
                dataset = self.get_dataset( trans, other_values )
                if dataset is None: 
                    return options
                key = filter.get( 'key', None )
                assert key is not None, "key attribute missing from data_meta filter"
                key = key.strip()
                value = filter.get( 'value', None )
                assert value is not None, "value attribute missing from data_meta filter"
                value = value.strip()
                col = filter.get( 'col', None )
                assert col is not None, "col attribute missing from data_meta filter"
                col = int( col.strip() )
                if key == 'build': # value must be 'dbkey'
                    value = eval( '''dataset.%s''' %value )
                elif key == 'some other future key': 
                    pass
                return self.load_from_file( key=key, value=value, col=col, sep='\t' )
            elif filter_type == 'some other future type':
                pass
        # We must not have found a filter, so we'll generate the list generically
        return self.load_from_file()

    """
    TODO: the following functions should be generalized so that they are not specific to
    certain tools (e.g., encode).  We may need to standardize data file formats to be able to do this.
    Comments in the functions show the tools that use them along with associated data files, if any
    """    
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
        options = []
        dataset = self.get_dataset( trans, other_values )
        if dataset is None:
            return options
        if dataset.dbkey == '?':
            return [( 'Build not set', 'None', True )]
        d = self.load_from_file_for_maf()
        for key in d:
            if dataset.dbkey in d[key]['builds']:
                options.append( ( d[key]['description'], key, False ) )
        if len( options ) < 1:
            return [self.no_data_option]
        return options
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
        options = []
        dataset = self.get_dataset( trans, other_values )
        if dataset is None:
            return options
        for species in dataset.metadata.species:
            options.append( ( species, species, False ) )
        return options
    def get_options_for_species_for_maf( self, trans, other_values ):
        """
        Used by the following tools:
        GeneBed_Maf_Fasta1 - associated data file: /depot/data2/galaxy/maf_index.loc
        """
        options = []
        assert len( self.func_params ) == 1, "Value for 'maf_source' not found"
        for func_param in self.func_params:
            if func_param.get( 'name' ).strip() == 'maf_source':
                maf_source = func_param.get( 'value' ).strip()
        if maf_source == 'cached':
            d = self.load_from_file_for_maf()
            maf_uid = self.get_param_value( trans, other_values )
            if maf_uid is None:
                return [self.no_data_option]
            if maf_uid == 'None':
                return [( '<b>Build not set, click pencil icon in your history item to associate a build</b>', 'None', True )]
            for key in d[maf_uid]['builds']:
                options.append( (key, key, False) )
            if len( options ) < 1:
                return [self.no_data_option]
        else: # maf_source == 'user'
            dataset = self.get_dataset( trans, other_values )
            if dataset is None:
                return [( "<B>You must wait for the MAF file to be created before you can use this tool.</B>", 'None', True )]
            for species in dataset.metadata.species:
                options.append( ( species, species, False ) )
        return options
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
        options = []
        elem_list = []
        dataset = self.get_dataset( trans, other_values )
        if dataset is None:
            return options
        datafile = dataset.get_file_name()
        try:
            in_file = open( datafile, "r" )
        except:
            return [self.no_data_option]
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
            return options
        elem_list = get_unique_elems( elem_list )
        for elem in elem_list:
            options.append( ( elem, elem, False ) )
        return options
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
        options = []
        def load_from_file_for_encode():
            encode_sets = {}
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
                    except:
                        encode_sets[encode_group][build]=[]
                        encode_sets[encode_group][build].append((description, uid, False))
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
            return encode_sets
        d = load_from_file_for_encode()
        if len( d ) < 1:
            return [self.no_data_option]
        else:
            try: 
                options = d[encode_group][build][0:]
            except:
                options.append( self.no_data_option )
        return options
    def load_from_file_for_microbial( self ):
        self.from_file = "/depot/data2/galaxy/microbes/microbial_data.loc"
        microbe_info= {}
        orgs = {}
        for line in open( self.from_file ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( '\t' )
                #read each line, if not enough fields, go to next line
                try:
                    info_type = fields.pop(0)
                    if info_type.upper() == "ORG":
                        #ORG     12521   Clostridium perfringens SM101   bacteria        Firmicutes      CP000312,CP000313,CP000314,CP000315     http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?db=genomeprj&cmd=Retrieve&dopt=Overview&list_uids=12521
                        org_num = fields.pop(0)
                        name = fields.pop(0)
                        kingdom = fields.pop(0)
                        group = fields.pop(0)
                        chromosomes = fields.pop(0)
                        info_url = fields.pop(0)
                        link_site = fields.pop(0)
                        if org_num not in orgs:
                            orgs[org_num] = {}
                            orgs[org_num]['chrs'] = {}
                        orgs[org_num]['name'] = name
                        orgs[org_num]['kingdom'] = kingdom
                        orgs[org_num]['group'] = group
                        orgs[org_num]['chromosomes'] = chromosomes
                        orgs[org_num]['info_url'] = info_url
                        orgs[org_num]['link_site'] = link_site
                    elif info_type.upper() == "CHR":
                        #CHR     12521   CP000315        Clostridium perfringens phage phiSM101, complete genome 38092   110684521       CP000315.1
                        org_num = fields.pop(0)
                        chr_acc = fields.pop(0)
                        name = fields.pop(0)
                        length = fields.pop(0)
                        gi = fields.pop(0)
                        gb = fields.pop(0)
                        info_url = fields.pop(0)
                        chr = {}
                        chr['name'] = name
                        chr['length'] = length
                        chr['gi'] = gi
                        chr['gb'] = gb
                        chr['info_url'] = info_url
                        if org_num not in orgs:
                            orgs[org_num] = {}
                            orgs[org_num]['chrs'] = {}
                        orgs[org_num]['chrs'][chr_acc] = chr
                    elif info_type.upper() == "DATA":
                        #DATA    12521_12521_CDS 12521   CP000315        CDS     bed     /home/djb396/alignments/playground/bacteria/12521/CP000315.CDS.bed
                        uid = fields.pop(0)
                        org_num = fields.pop(0)
                        chr_acc = fields.pop(0)
                        feature = fields.pop(0)
                        filetype = fields.pop(0)
                        path = fields.pop(0)
                        data = {}
                        data['filetype'] = filetype
                        data['path'] = path
                        data['feature'] = feature
    
                        if org_num not in orgs:
                            orgs[org_num] = {}
                            orgs[org_num]['chrs'] = {}
                        if 'data' not in orgs[org_num]['chrs'][chr_acc]:
                            orgs[org_num]['chrs'][chr_acc]['data'] = {}
                        orgs[org_num]['chrs'][chr_acc]['data'][uid] = data
                    else: continue
                except: continue
        for org_num in orgs:
            org = orgs[org_num]
            if org['kingdom'] not in microbe_info:
                microbe_info[org['kingdom']] = {}
            if org_num not in microbe_info[org['kingdom']]:
                microbe_info[org['kingdom']][org_num] = org
        self.microbe_info = microbe_info
    def get_options_for_kingdoms( self, trans, other_values ):
        if self.microbe_info == None: self.load_from_file_for_microbial()
        options = []
        kingdoms = self.microbe_info.keys()
        kingdoms.sort()
        for kingdom in kingdoms:
            options.append( (kingdom, kingdom, False) )
        return options
    def get_options_for_orgs_by_kingdom( self, trans, other_values ):
        if self.microbe_info == None: self.load_from_file_for_microbial()
        options = []
        kingdom = self.get_param_value( trans, other_values )
        orgs = self.microbe_info[kingdom].keys()
        #need to sort by name
        swap_test = False
        for i in range( 0, len(orgs) - 1 ):
            for j in range( 0, len(orgs) - i - 1 ):
                if self.microbe_info[kingdom][orgs[j]]['name'] > self.microbe_info[kingdom][orgs[j + 1]]['name']:
                    orgs[j], orgs[j + 1] = orgs[j + 1], orgs[j]
                swap_test = True
            if swap_test == False: break
        for org in orgs:
             if self.microbe_info[kingdom][org]['link_site'] == "UCSC":
                options.append( ( "<b>" + self.microbe_info[kingdom][org]['name'] + "</b> <a href=\"" + self.microbe_info[kingdom][org]['info_url'] + "\" target=\"_blank\">(about)</a>", org, False ) )
             else:
                options.append( ( self.microbe_info[kingdom][org]['name'] + " <a href=\"" + self.microbe_info[kingdom][org]['info_url'] + "\" target=\"_blank\">(about)</a>", org, False ) )
        """
        if options:
            options[0] = ( options[0][0], options[0][1], True)
        """
        return options 
    def get_options_for_kingdom_org_feature( self, trans, other_values ):
        if self.microbe_info == None: self.load_from_file_for_microbial()
        options = []
        for func_param in self.func_params:
            if func_param.get( 'name' ) == 'kingdom':
                kingdom = other_values[ func_param.get( 'value' ) ]
            elif func_param.get( 'name' )  == 'org':
                org = other_values[ func_param.get( 'value' ) ]
            elif func_param.get( 'name' )  == 'feature':
                feature = func_param.get( 'value' )
        log.debug("kingdom: %s, org: %s, feature: %s" %(kingdom, org, feature))
        chroms = self.microbe_info[kingdom][org]['chrs'].keys()
        chroms.sort()
        for chr in chroms:
             for data in self.microbe_info[kingdom][org]['chrs'][chr]['data']:
                 if self.microbe_info[kingdom][org]['chrs'][chr]['data'][data]['feature'] == feature:
                     options.append( ( self.microbe_info[kingdom][org]['chrs'][chr]['name'] + " <a href=\"" + self.microbe_info[kingdom][org]['chrs'][chr]['info_url'] + "\" target=\"_blank\">(about)</a>", data, False ) )
        return options

