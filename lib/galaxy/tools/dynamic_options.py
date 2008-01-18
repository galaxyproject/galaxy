
import sys, os, logging

log = logging.getLogger(__name__)

class DynamicOptions( object ):
    """Handles dynamically generated SelectToolParameter options"""
    def __init__( self, elem  ):
        self.from_file_data = None
        # FIXME: Pushing these things in as options ends up being pretty ugly. 
        # We should find a way to make this work through the validation mechanism.
        self.no_data_option = [ ( 'No data available for this build', 'None', True ) ]
        self.no_data_option_not_selected = [ ( 'No data available for this build', 'None', False ) ]
        self.no_elems_option = [ ( 'No elements to display, please choose another column', 'None', True ) ]
        self.unspecified_build_option = [ ( 'unspecified', '?', True ) ]
        self.build_not_set_option = [ ( 'Build not set, click the pencil icon in your history item to set the build', 'None', True ) ]
        self.wait_for_maf_option = [ ( 'You must wait for the MAF file to be created before you can use this tool.', 'None', True ) ]
        self.from_file = elem.get( 'from_file', None )
        if self.from_file is not None:
            self.from_file = self.from_file.strip()
            try: 
                i = self.from_file.rindex( "/" )
                self.data_file = self.from_file[ i+1: ]
            except:
                self.data_file = self.from_file
        else: 
            self.data_file = None
        self.filters = elem.findall( 'filter' )
        self.data_ref = None
        for filter in self.filters:
            filter_type = filter.get( 'type', None )
            assert filter_type is not None, "Required 'type' attribute missing from filter"
            if filter_type.strip() == 'data_meta':
                self.data_ref = filter.get( 'data_ref', None )
                assert self.data_ref is not None, "Required 'data_ref' attribute missing from 'data_meta' filter"
                self.data_ref = self.data_ref.strip()
            elif filter_type.strip() == 'param_meta':
                self.param_ref = filter.get( 'param_ref', None )
                assert self.param_ref is not None, "Required 'param_ref' attribute missing from 'param_meta' filter"
                self.param_ref = self.param_ref.strip()
    def get_dependency_names( self ):
        """
        Return the names of parameters these options depend on -- both data
        and other param types.
        """
        rval = []
        if self.data_ref:
            rval.append( self.data_ref )
        if self.param_ref:
            rval.append( self.param_ref )
        return rval        
    def get_data_ref_value( self, trans, other_values ):
        # No value indicates a configuration error, the named DataToolParameter must preceed this parameter in the tool config
        assert self.data_ref in other_values, "Value for associated DataToolParameter not found"
        # Get the value of the associated DataToolParameter (a dataset)
        dataset = other_values[ self.data_ref ]
        if dataset is None or dataset == '':
            # Both of these values indicate that no dataset is selected.  However, 'None' 
            # indicates that the dataset is optional while '' indicates that it is not. 
            # Currently dynamically generated select lists do not work well with optional datasets.
            return None
        return dataset
    def get_param_value( self, param, trans, other_values ):
        if param is None: 
            return None
        assert param in other_values, "Value for associated param_value %s not found" %param
        return other_values[ param ]
    def get_param_ref_value( self, trans, other_values ):
        if self.param_ref is None: 
            return None
        assert self.param_ref in other_values, "Value for associated param_ref %s not found" %self.param_ref.name
        return other_values[ self.param_ref ]
    def get_unique_elems( self, elems ): 
        seen = set()
        return [ x for x in elems if x not in seen and not seen.add( x ) ]
    def get_options( self, trans, other_values, must_be_valid=False ):
        filters = {}
        key = None
        # Check for filters and build a dictionary from them
        for filter in self.filters:
            filter_type = filter.get( 'type', None )
            assert filter_type is not None, "type attribute missing from filter"
            filter_type = filter_type.strip()
            if filter_type == 'data_meta':
                filters[ 'data_meta' ] = {}
                dataset = self.get_data_ref_value( trans, other_values )
                if dataset is None: 
                    return []
                key = filter.get( 'key', None )
                if key is not None:
                    filters[ 'data_meta' ][ 'key' ] = key.strip()
                value = filter.get( 'value', None )
                if value is not None: 
                    value = value.strip()
                else:
                    if key == 'build': 
                        value = dataset.get_dbkey()
                    elif key == 'file_name': 
                        value = dataset.get_file_name()
                    elif key == 'species': 
                        value = dataset.metadata.species
                filters[ 'data_meta' ][ 'value' ] = value
                if self.data_file == 'maf_index.loc' and key == 'build' and value == '?':
                    if must_be_valid: 
                        return []
                    return self.build_not_set_option
            elif filter_type == 'param_meta':
                filters[ 'param_meta' ] = {}
                value = self.get_param_ref_value( trans, other_values )
                filters[ 'param_meta' ][ 'value' ] = value
            elif filter_type == 'param_value':
                n = filter.get( 'name', None )
                assert n is not None, "param_value filters require a 'name' attribute"
                n = n.strip()
                v = self.get_param_value( n, trans, other_values )
                assert v is not None, "param_value filters require a 'value' attribute"
                v = v.strip()
                try:
                    filters[ 'param_values' ][ n ] = v
                except:
                    filters[ 'param_values' ] = {}
                    filters[ 'param_values' ][ n ] = v
            elif filter_type == 'column':
                n = filter.get( 'name', None )
                assert n is not None, "column filters require a 'name' attribute"
                n = n.strip()
                v = filter.get( 'value', None )
                assert v is not None, "column filters require a 'value' attribute"
                v = v.strip()
                try: 
                    filters[ 'columns' ][ n ] = v
                except: 
                    filters[ 'columns' ] = {}
                    filters[ 'columns' ][ n ] = v
            elif filter_type == 'param':
                n = filter.get( 'name', None )
                assert n is not None, "param filters require a 'name' attribute"
                n = n.strip()
                v = filter.get( 'value', None )
                assert v is not None, "param filters require a 'value' attribute"
                v = v.strip()
                try: 
                    filters[ 'params' ][ n ] = v
                except:
                    filters[ 'params' ] = {}
                    filters[ 'params' ][ n ] = v
        # Now that we've parsed our filters, we need to see if the tool is a maf tool 
        # which requires special handling
        try:
            maf_source = filters[ 'params' ][ 'maf_source' ]
            if maf_source == 'cached':
                maf_uid = filters[ 'param_meta' ][ 'value' ]
                if maf_uid in [ None, 'None' ]:
                    if must_be_valid: 
                        return []
                    if maf_uid is None: 
                        return self.no_data_option
                    if maf_uid == 'None': 
                        return self.build_not_set_option
                return self.generate_for_maf( maf_uid, '\t', must_be_valid=must_be_valid )
            elif maf_source == 'user':
                dataset = self.get_data_ref_value( trans, other_values )
                if dataset is None: 
                    return self.wait_for_maf_option
                filters[ 'data_meta' ][ 'key' ] = 'species'
                filters[ 'data_meta' ][ 'value' ] = dataset.metadata.species
        except:
            pass
        return self.generate_options( filters, must_be_valid=must_be_valid )
    def generate_options( self, filters={}, sep='\t', must_be_valid=False ):
        try: 
            key = filters[ 'data_meta' ][ 'key' ]
        except:
            try: 
                key = filters[ 'param_meta' ][ 'key' ]
            except: 
                key = None
        if key == 'species':
            species = filters[ 'data_meta' ][ 'value' ]
            return self.generate_for_species( species )
        elif key == 'file_name':
            file_name = filters[ 'data_meta' ][ 'value' ]
            value_col = int( filters[ 'columns' ][ 'value_col' ] )
            return self.generate_from_dataset( file_name, value_col, sep )
        elif key == 'build':
            build = filters[ 'data_meta' ][ 'value' ]
            build_col = int( filters[ 'columns' ][ 'build_col' ].strip() )
            name_col = int( filters[ 'columns' ][ 'name_col' ] )
            value_col = int( filters[ 'columns' ][ 'value_col' ] )
            return self.generate_for_build( build, build_col, name_col, value_col, sep, must_be_valid=must_be_valid )
        else: # key is None
            if self.data_file == 'datatypes_registry':
                return self.generate_from_datatypes_registry()
            elif self.data_file == 'encode_datasets.loc':
                encode_group = filters[ 'params' ][ 'encode_group' ]
                build = filters[ 'params' ][ 'build' ]
                return self.generate_for_encode( encode_group, build, sep, must_be_valid=must_be_valid )
            elif self.data_file == 'microbial_data.loc':
                if self.from_file_data is None: 
                    self.load_microbial_data()
                try: 
                    kingdom = filters[ 'param_values' ][ 'kingdom' ]
                except: 
                    kingdom = None
                try: 
                    org = filters[ 'param_values' ][ 'org' ]
                except: 
                    org = None
                try: 
                    feature = filters[ 'params' ][ 'feature' ]
                except: 
                    feature = None
                return self.generate_for_microbial( kingdom, org, feature, must_be_valid=must_be_valid )
            else:
                name_col = int( filters[ 'columns' ][ 'name_col' ] )
                value_col = int( filters[ 'columns' ][ 'value_col' ] )
                return self.generate( name_col, value_col, sep )
    def generate_from_datatypes_registry( self ):
        from galaxy.datatypes import registry
        datatypes_registry = registry.Registry()
        options = []
        formats = datatypes_registry.datatypes_by_extension.keys()
        formats.sort()
        options.append( ( 'Auto-detect', 'auto', True ) )
        for format in formats:
            label = format.capitalize()
            options.append( ( label, format, False ) )
        return options
    def generate_for_encode( self, encode_group, build, sep, must_be_valid=False ):
        options = []
        def generate():
            encode_sets = {}
            for line in open( self.from_file ):
                line = line.rstrip( '\r\n' )
                if line and not line.startswith( '#' ):
                    try:
                        fields = line.split( sep )
                        encode_group = fields[ 0 ]
                        build = fields[ 1 ]
                        description = fields[ 2 ]
                        uid = fields[ 3 ]
                        path = fields[ 4 ]
                        try: 
                            file_type = fields[ 5 ]
                        except: 
                            file_type = "bed"
                        #TODO: will remove this later, when galaxy can handle gff files
                        if file_type != "bed": 
                            continue
                        if not os.path.isfile( path ): 
                            continue
                    except: 
                        continue
                    try: 
                        temp = encode_sets[ encode_group ]
                    except: 
                        encode_sets[ encode_group ] = {}
                    try:
                        encode_sets[ encode_group ][ build ].append( ( description, uid, False ) )
                    except:
                        encode_sets[ encode_group ][ build ] = []
                        encode_sets[ encode_group ][ build] .append( ( description, uid, False ) )
            #Order by description and date, highest date on top and bold
            for group in encode_sets:
                for build in encode_sets[ group ]:
                    ordered_build = []
                    for description, uid, selected in encode_sets[ group ][ build ]:
                        item = {}
                        item[ 'date' ] = 0
                        item[ 'description' ] = ""
                        item[ 'uid' ] = uid
                        item[ 'selected' ] = selected
                        item[ 'partitioned' ] = False
                        if description[ -21: ] == '[gencode_partitioned]':
                            item[ 'date' ] = description[ -31:-23 ]
                            item[ 'description' ] = description[ 0:-32 ]
                            item[ 'partitioned' ] = True
                        else:
                            item[ 'date' ] = description[ -9:-1 ]
                            item[ 'description' ] = description[ 0:-10 ]
                            
                        for i in range( len( ordered_build ) ):
                            ordered_description, ordered_uid, ordered_selected, ordered_item = ordered_build[ i ]
                            if item[ 'description' ] < ordered_item[ 'description' ]:
                                ordered_build.insert( i, ( description, uid, selected, item ) )
                                break
                            if item[ 'description' ] == ordered_item[ 'description' ] and item[ 'partitioned' ] == ordered_item[ 'partitioned' ]:
                                if int( item[ 'date' ] ) > int( ordered_item[ 'date' ] ):
                                    ordered_build.insert( i, ( description, uid, selected, item ) )
                                    break
                        else: 
                            ordered_build.append( ( description, uid, selected, item ) )
                    last_desc = None
                    last_partitioned = None
                    for i in range( len( ordered_build ) ) :
                        description, uid, selected, item = ordered_build[ i ]
                        if item[ 'partitioned' ] != last_partitioned or last_desc != item[ 'description' ]:
                            last_desc = item[ 'description' ]
                            description = "<b>" + description + "</b>"
                        else:
                            last_desc = item[ 'description' ]
                        last_partitioned = item[ 'partitioned' ]
                        encode_sets[ group ][ build ][ i ] = ( description, uid, selected )        
            return encode_sets
        d = generate()
        if len( d ) < 1:
            if must_be_valid: 
                return []
            return self.no_data_option_not_selected
        else:
            try: 
                options = d[ encode_group ][ build ][ 0: ]
            except:
                if must_be_valid: 
                    return []
                return self.no_data_option_not_selected
        return options
    def generate_for_microbial( self, kingdom=None, org=None, feature=None, must_be_valid=False ):
        options = []
        if not kingdom and not org and not feature:
            kingdoms = self.from_file_data.keys()
            kingdoms.sort()
            for kingdom in kingdoms:
                options.append( ( kingdom, kingdom, False ) )
            if options:
                options[0] = ( options[0][0], options[0][1], True )
        elif kingdom and not org and not feature:
            orgs = self.from_file_data[ kingdom ].keys()
            #need to sort by name
            swap_test = False
            for i in range( 0, len( orgs ) - 1 ):
                for j in range( 0, len( orgs ) - i - 1 ):
                    if self.from_file_data[ kingdom ][ orgs[ j ] ][ 'name' ] > self.from_file_data[ kingdom ][ orgs[ j + 1 ] ][ 'name' ]:
                        orgs[ j ], orgs[ j + 1 ] = orgs[ j + 1 ], orgs[ j ]
                    swap_test = True
                if swap_test == False: 
                    break
            for org in orgs:
                 if self.from_file_data[ kingdom ][ org ][ 'link_site' ] == "UCSC":
                    options.append( ( "<b>" + self.from_file_data[ kingdom ][ org ][ 'name' ] + "</b> <a href=\"" + self.from_file_data[ kingdom ][ org ][ 'info_url' ] + "\" target=\"_blank\">(about)</a>", org, False ) )
                 else:
                    options.append( ( self.from_file_data[ kingdom ][ org ][ 'name' ] + " <a href=\"" + self.from_file_data[ kingdom ][ org ][ 'info_url' ] + "\" target=\"_blank\">(about)</a>", org, False ) )
            if options:
                options[0] = ( options[0][0], options[0][1], True )
        else:
            chroms = self.from_file_data[ kingdom ][ org ][ 'chrs' ].keys()
            chroms.sort()
            for chr in chroms:
                 for data in self.from_file_data[ kingdom ][ org ][ 'chrs' ][ chr ][ 'data' ]:
                     if self.from_file_data[ kingdom ][ org ][ 'chrs' ][ chr ][ 'data' ][ data ][ 'feature' ] == feature:
                         options.append( ( self.from_file_data[ kingdom ][ org ][ 'chrs' ][ chr ][ 'name' ] + " <a href=\"" + self.from_file_data[ kingdom ][ org ][ 'chrs' ][ chr ][ 'info_url' ] + "\" target=\"_blank\">(about)</a>", data, False ) )
        return options
    def load_microbial_data( self, sep='\t' ):
        microbe_info= {}
        orgs = {}
        for line in open( self.from_file ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( sep )
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
                            orgs[ org_num ] = {}
                            orgs[ org_num ][ 'chrs' ] = {}
                        orgs[ org_num ][ 'name' ] = name
                        orgs[ org_num ][ 'kingdom' ] = kingdom
                        orgs[ org_num ][ 'group' ] = group
                        orgs[ org_num ][ 'chromosomes' ] = chromosomes
                        orgs[ org_num ][ 'info_url' ] = info_url
                        orgs[ org_num ][ 'link_site' ] = link_site
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
                        chr[ 'name' ] = name
                        chr[ 'length' ] = length
                        chr[ 'gi' ] = gi
                        chr[ 'gb' ] = gb
                        chr[ 'info_url' ] = info_url
                        if org_num not in orgs:
                            orgs[ org_num ] = {}
                            orgs[ org_num ][ 'chrs' ] = {}
                        orgs[ org_num ][ 'chrs' ][ chr_acc ] = chr
                    elif info_type.upper() == "DATA":
                        #DATA    12521_12521_CDS 12521   CP000315        CDS     bed     /home/djb396/alignments/playground/bacteria/12521/CP000315.CDS.bed
                        uid = fields.pop(0)
                        org_num = fields.pop(0)
                        chr_acc = fields.pop(0)
                        feature = fields.pop(0)
                        filetype = fields.pop(0)
                        path = fields.pop(0)
                        data = {}
                        data[ 'filetype' ] = filetype
                        data[ 'path' ] = path
                        data[ 'feature' ] = feature
    
                        if org_num not in orgs:
                            orgs[ org_num ] = {}
                            orgs[ org_num ][ 'chrs' ] = {}
                        if 'data' not in orgs[ org_num ][ 'chrs' ][ chr_acc ]:
                            orgs[ org_num ][ 'chrs' ][ chr_acc ][ 'data' ] = {}
                        orgs[ org_num ][ 'chrs' ][ chr_acc ][ 'data' ][ uid ] = data
                    else: 
                        continue
                except: 
                    continue
        for org_num in orgs:
            org = orgs[ org_num ]
            if org[ 'kingdom' ] not in microbe_info:
                microbe_info[ org[ 'kingdom' ] ] = {}
            if org_num not in microbe_info[ org[ 'kingdom' ] ]:
                microbe_info[ org[ 'kingdom' ] ][org_num] = org
        self.from_file_data = microbe_info
    def generate_for_species( self, species ):
        options = []
        for s in species:
            options.append( ( s, s, False ) )
        return options
    def generate_for_maf( self, maf_uid, sep, must_be_valid=False ):
        options = []
        d = {}
        for line in open( self.from_file ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( sep )
                try:
                    name_col_data = fields[ 0 ] # ENCODE TBA (hg17)
                    value_col_data = fields[ 1 ] # ENCODE_TBA_hg17
                    builds_col_data = fields[ 2 ] # armadillo=armadillo,baboon=baboon,galGal2=chicken,...
                    build_list = []
                    builds = builds_col_data.split( ',' )
                    for build in builds:
                        this_build = build.split( '=' )[ 0 ]
                        build_list.append( this_build )
                    d[ value_col_data ] = {}
                    d[ value_col_data ][ 'description' ] = name_col_data
                    d[ value_col_data ][ 'builds' ] = build_list
                except: 
                    continue
        for key in d[ maf_uid ][ 'builds' ]:
            options.append( ( key, key, False ) )
        if not options:
            if must_be_valid: 
                return []
            return self.no_data_option
        return options
    def generate_from_dataset( self, file_name, value_col, sep, must_be_valid=False ):
        options = []
        elem_list = []
        try: 
            in_file = open( file_name, "r" )
        except:
            if must_be_valid: 
                return []
            return self.no_data_option
        try:
            for line in in_file:
                line = line.rstrip( "\r\n" )
                if line and not line.startswith( '#' ):
                    elems = line.split( sep )
                    elem_list.append( elems[ value_col ] )
        except: 
            pass
        in_file.close()
        if not( elem_list ):
            if must_be_valid: 
                return []
            return self.no_elems_option
        elem_list = self.get_unique_elems( elem_list )
        for elem in elem_list:
            options.append( ( elem, elem, False ) )
        return options
    def generate_for_build( self, build, build_col, name_col, value_col, sep, must_be_valid=False ):
        options = []
        d = {}
        for line in open( self.from_file ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( sep )
                # TDDO: regenerate the following data files so that they follow a column standard.
                # build_col = 0 - put build values in column 0
                # name_col = 1 - put the select list description values in column 1
                # value_col = 2 - put the select list value values in column 2
                # This will allow us to eliminate the following data_file conditionals
                #
                # TODO: the alignseq.loc file is currently ony used by the "Extract blastz alignments1"
                # tool, which seems to be deprecated.  Can we eliminate it altogether?
                if self.data_file == 'alignseq.loc':
                    if fields[ build_col ].strip() == 'align':
                        try: 
                            d[ fields[ name_col ] ].append( fields[ value_col ] )
                        except: 
                            d[ fields[ name_col ] ] = [ fields[ value_col ] ]
                elif self.data_file == 'regions.loc' or self.data_file == 'phastOdds.loc' or self.data_file == 'binned_scores.loc':
                    if not fields[ build_col ] in d: 
                        d[ fields[ build_col ] ] = []
                    d[ fields[ build_col ] ].append( (fields[ name_col ], fields[ value_col ]) )
                elif self.data_file == 'maf_index.loc' or self.data_file == 'maf_pairwise.loc':
                    try:
                        maf_desc = fields[ name_col ] # ENCODE TBA (hg17)
                        maf_uid = fields[ value_col ] # ENCODE_TBA_hg17
                        builds = fields[ build_col ] # armadillo=armadillo,baboon=baboon,galGal2=chicken,...
                        build_list = []
                        split_builds = builds.split( ',' )
                        for b in split_builds:
                            this_build = b.split( '=' )[0]
                            build_list.append( this_build )
                        d[ maf_uid ] = {}
                        d[ maf_uid ][ 'description' ] = maf_desc
                        d[ maf_uid ][ 'builds' ] = build_list
                    except: 
                        continue

        # TODO: the alignseq.loc file is currently ony used by the "Extract blastz alignments1"
        # tool, which seems to be deprecated.  Can we eliminate it altogether?
        if self.data_file == 'alignseq.loc':
            # FIXME: We need a database of descriptive names corresponding to dbkeys.
            #        We need to resolve the musMusX <--> mmX confusion
            if build[ 0:2 ] == "mm": 
                build = build.replace( 'mm', 'musMus' )
            if build[ 0:2 ] == "rn": 
                build = build.replace( 'rn', 'ratNor' )
            if build in d:
                for val in d[ build ]:
                    options.append( ( val, val, False ) )
        elif self.data_file == 'regions.loc' or self.data_file == 'phastOdds.loc' or self.data_file == 'binned_scores.loc':
            if build in d:
                for (key, val) in d[ build ]:
                    options.append( ( key, val, False ) )
        elif self.data_file == 'maf_index.loc' or self.data_file == 'maf_pairwise.loc':
            for key in d:
                if build in d[ key ][ 'builds' ]:
                    options.append( ( d[ key ][ 'description' ], key, False ) )
            if not options:
                if must_be_valid: 
                    return []
                return self.no_data_option
        if not options: 
            if must_be_valid: 
                return []
            return self.unspecified_build_option
        return options
    def generate( self, name_col, value_col, sep ):
        options = []
        for line in open( self.from_file ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( sep )
                # TODO: this option list should be sorted
                options.append( ( fields[ name_col ], fields[ value_col ], False ) )
        return options
