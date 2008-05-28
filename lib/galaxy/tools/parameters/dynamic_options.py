"""
Support for generating the options for a SelectToolParameter dynamically (based
on the values of other parameters or other aspects of the current state)
"""

import operator, sys, os, logging
import basic, validation

log = logging.getLogger(__name__)

class DynamicOptions( object ):
    """Handles dynamically generated SelectToolParameter options"""
    def __init__( self, elem, tool_param  ):
        self.tool_param = tool_param
        self.data_ref = None
        self.param_ref = None
        self.data_file_path = None
        self.data_file_data = None
        self.validators = []

        # Parse the options tag
        self.data_file = elem.get( 'from_file', None )
        if self.data_file is not None:
            self.data_file = self.data_file.strip()
        self.name_col = elem.get( 'name_col', None )
        if self.name_col is not None:
            self.name_col = int( self.name_col.strip() )
        self.value_col = elem.get( 'value_col', None )
        if self.value_col is not None:
            self.value_col = int( self.value_col.strip() )
        self.separator = elem.get( 'seperator', '\t' )
        self.line_startswith = elem.get( 'line_startswith', None )

        # Parse the Validator tags
        for validator in elem.findall( 'validator' ):
            validator_type = validator.get( 'type', None )
            assert validator_type is not None, "Required 'type' attribute missing from validator"
            validator_type = validator_type.strip()
            self.validators.append( validation.Validator.from_element( self.tool_param, validator ) )

        # Parse the filter tags
        self.filters = elem.findall( 'filter' )
        for filter in self.filters:
            filter_type = filter.get( 'type', None )
            assert filter_type is not None, "Required 'type' attribute missing from filter"
            filter_type = filter_type.strip()

            if filter_type == 'data_meta':
                self.data_ref = filter.get( 'data_ref', None )
                assert self.data_ref is not None, "Required 'data_ref' attribute missing from 'data_meta' filter"
                self.data_ref = self.data_ref.strip()

            elif filter_type == 'param_meta':
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
    def get_options( self, trans, other_values ):
        filters = {}
        key = None
        # Check for filters and build a dictionary from them
        for filter in self.filters:
            filter_type = filter.get( 'type', None )
            assert filter_type is not None, "'type' attribute missing from filter"
            filter_type = filter_type.strip()

            if filter_type == 'data_meta':
                filters[ 'data_meta' ] = {}
                dataset = self.get_data_ref_value( trans, other_values )
                if dataset is None: 
                    return []
                # meta_key is optional
                meta_key = filter.get( 'meta_key', None )
                if meta_key is not None:
                    filters[ 'data_meta' ][ 'meta_key' ] = meta_key.strip()
                    if meta_key == 'dbkey':
                        meta_value = dataset.get_dbkey()
                    elif meta_key == 'species': 
                        meta_value = dataset.metadata.species
                    filters[ 'data_meta' ][ 'meta_value' ] = meta_value
                elif self.data_file == 'data_ref':
                    # We'll be reading data directly from the input dataset
                    filters[ 'data_meta' ][ 'meta_key' ] = 'data_ref'
                    self.data_file_path = dataset.get_file_name()
                    filters[ 'data_meta' ][ 'meta_value' ] = self.data_file_path
                # meta_key_col is optional
                meta_key_col = filter.get( 'meta_key_col', None )
                if meta_key_col is not None:
                    filters[ 'data_meta' ][ 'meta_key_col' ] = int( meta_key_col.strip() )

            elif filter_type == 'param_meta':
                filters[ 'param_meta' ] = {}
                meta_value = self.get_param_ref_value( trans, other_values )
                filters[ 'param_meta' ][ 'meta_value' ] = meta_value

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
        if self.data_file and self.data_file.startswith( 'static' ):
            self.data_file_path = self.data_file
        elif self.data_file not in [ None, 'data_ref' ] and not os.path.isabs( self.data_file ):
            self.data_file_path = "%s/%s" % ( trans.app.config.tool_data_path, self.data_file )
        # Now that we've parsed our filters, we need to see if the tool is a maf tool 
        # which requires special handling
        # TODO: remove or rework this if possible
        try:
            maf_source = filters[ 'params' ][ 'maf_source' ]
            if maf_source == 'cached':
                maf_uid = filters[ 'param_meta' ][ 'meta_value' ]
                if maf_uid in [ None, 'None' ]:
                    return []
                return self.generate_for_maf( maf_uid, '\t' )
            elif maf_source == 'user':
                dataset = self.get_data_ref_value( trans, other_values )
                filters[ 'data_meta' ][ 'meta_key' ] = 'species'
                filters[ 'data_meta' ][ 'meta_value' ] = dataset.metadata.species
        except:
            pass
        return self.generate_options( trans, filters=filters, sep=self.separator )
    def generate_options( self, trans, filters={}, sep='\t' ):
        try: 
            meta_key = filters[ 'data_meta' ][ 'meta_key' ]
        except:
            try: 
                meta_key = filters[ 'param_meta' ][ 'meta_key' ]
            except: 
                meta_key = None
        if meta_key == 'species':
            return self.generate_for_species( filters[ 'data_meta' ][ 'meta_value' ] )
        elif meta_key == 'data_ref':
            dataset_file_name = filters[ 'data_meta' ][ 'meta_value' ]
            return self.generate_from_dataset( dataset_file_name, self.value_col, sep=sep )
        elif meta_key == 'dbkey':
            dbkey = filters[ 'data_meta' ][ 'meta_value' ]
            if type( self.tool_param ) == basic.DataToolParameter:
                return meta_key, dbkey
            meta_key_col = filters[ 'data_meta' ][ 'meta_key_col' ]
            return self.generate_for_dbkey( dbkey, meta_key_col, self.name_col, self.value_col, sep=sep )
        else: # meta_key is None
            if self.data_file == 'datatypes_registry':
                upload_file_formats = trans.app.datatypes_registry.upload_file_formats
                return self.generate_from_datatypes_registry( upload_file_formats )
            elif self.data_file == 'encode_datasets.loc':
                encode_group = filters[ 'params' ][ 'encode_group' ]
                dbkey = filters[ 'params' ][ 'dbkey' ]
                return self.generate_for_encode( encode_group, dbkey, sep=sep )
            elif self.data_file == 'microbial_data.loc':
                if self.data_file_data is None: 
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
                return self.generate_for_microbial( kingdom, org, feature )
            else:
                return self.generate( self.name_col, self.value_col, sep=sep )
    def generate_from_datatypes_registry( self, upload_file_formats ):
        options = []
        formats = upload_file_formats
        formats.sort()
        options.append( ( 'Auto-detect', 'auto', True ) )
        for format in formats:
            label = format.capitalize()
            options.append( ( label, format, False ) )
        return options
    def generate_for_encode( self, encode_group, dbkey, sep='\t' ):
        options = []
        def generate():
            encode_sets = {}
            for line in open( self.data_file_path ):
                line = line.rstrip( '\r\n' )
                if line and not line.startswith( '#' ):
                    try:
                        fields = line.split( sep )
                        encode_group = fields[ 0 ]
                        dbkey = fields[ 1 ]
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
                        encode_sets[ encode_group ][ dbkey ].append( ( description, uid, False ) )
                    except:
                        encode_sets[ encode_group ][ dbkey ] = []
                        encode_sets[ encode_group ][ dbkey].append( ( description, uid, False ) )
            #Order by description and date, highest date on top and bold
            for group in encode_sets:
                for dbkey in encode_sets[ group ]:
                    ordered_dbkey = []
                    for description, uid, selected in encode_sets[ group ][ dbkey ]:
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
                            
                        for i in range( len( ordered_dbkey ) ):
                            ordered_description, ordered_uid, ordered_selected, ordered_item = ordered_dbkey[ i ]
                            if item[ 'description' ] < ordered_item[ 'description' ]:
                                ordered_dbkey.insert( i, ( description, uid, selected, item ) )
                                break
                            if item[ 'description' ] == ordered_item[ 'description' ] and item[ 'partitioned' ] == ordered_item[ 'partitioned' ]:
                                if int( item[ 'date' ] ) > int( ordered_item[ 'date' ] ):
                                    ordered_dbkey.insert( i, ( description, uid, selected, item ) )
                                    break
                        else: 
                            ordered_dbkey.append( ( description, uid, selected, item ) )
                    last_desc = None
                    last_partitioned = None
                    for i in range( len( ordered_dbkey ) ) :
                        description, uid, selected, item = ordered_dbkey[ i ]
                        if item[ 'partitioned' ] != last_partitioned or last_desc != item[ 'description' ]:
                            last_desc = item[ 'description' ]
                            description = "<b>" + description + "</b>"
                        else:
                            last_desc = item[ 'description' ]
                        last_partitioned = item[ 'partitioned' ]
                        encode_sets[ group ][ dbkey ][ i ] = ( description, uid, selected )        
            return encode_sets
        d = generate()
        try: 
            options = d[ encode_group ][ dbkey ][ 0: ]
        except:
            return []
        return options
    def generate_for_microbial( self, kingdom=None, org=None, feature=None ):
        options = []
        if not kingdom and not org and not feature:
            kingdoms = self.data_file_data.keys()
            kingdoms.sort()
            for kingdom in kingdoms:
                options.append( ( kingdom, kingdom, False ) )
            if options:
                options[0] = ( options[0][0], options[0][1], True )
        elif kingdom and not org and not feature:
            orgs = self.data_file_data[ kingdom ].keys()
            #need to sort by name
            swap_test = False
            for i in range( 0, len( orgs ) - 1 ):
                for j in range( 0, len( orgs ) - i - 1 ):
                    if self.data_file_data[ kingdom ][ orgs[ j ] ][ 'name' ] > self.data_file_data[ kingdom ][ orgs[ j + 1 ] ][ 'name' ]:
                        orgs[ j ], orgs[ j + 1 ] = orgs[ j + 1 ], orgs[ j ]
                    swap_test = True
                if swap_test == False: 
                    break
            for org in orgs:
                 if self.data_file_data[ kingdom ][ org ][ 'link_site' ] == "UCSC":
                    options.append( ( "<b>" + self.data_file_data[ kingdom ][ org ][ 'name' ] + "</b> <a href=\"" + self.data_file_data[ kingdom ][ org ][ 'info_url' ] + "\" target=\"_blank\">(about)</a>", org, False ) )
                 else:
                    options.append( ( self.data_file_data[ kingdom ][ org ][ 'name' ] + " <a href=\"" + self.data_file_data[ kingdom ][ org ][ 'info_url' ] + "\" target=\"_blank\">(about)</a>", org, False ) )
            if options:
                options[0] = ( options[0][0], options[0][1], True )
        else:
            chroms = self.data_file_data[ kingdom ][ org ][ 'chrs' ].keys()
            chroms.sort()
            for chr in chroms:
                 for data in self.data_file_data[ kingdom ][ org ][ 'chrs' ][ chr ][ 'data' ]:
                     if self.data_file_data[ kingdom ][ org ][ 'chrs' ][ chr ][ 'data' ][ data ][ 'feature' ] == feature:
                         options.append( ( self.data_file_data[ kingdom ][ org ][ 'chrs' ][ chr ][ 'name' ] + " <a href=\"" + self.data_file_data[ kingdom ][ org ][ 'chrs' ][ chr ][ 'info_url' ] + "\" target=\"_blank\">(about)</a>", data, False ) )
        return options
    def load_microbial_data( self, sep='\t' ):
        microbe_info= {}
        orgs = {}
        for line in open( self.data_file_path ):
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
        self.data_file_data = microbe_info
    def generate_for_species( self, species ):
        options = []
        for s in species:
            options.append( ( s, s, False ) )
        return options
    def generate_for_maf( self, maf_uid, sep='\t' ):
        options = []
        d = {}
        for line in open( self.data_file_path ):
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
        return options
    def generate_from_dataset( self, file_name, value_col, sep='\t' ):
        options = []
        elem_list = []
        try: 
            in_file = open( file_name, "r" )
        except:
            return []
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
            return []
        elem_list = self.get_unique_elems( elem_list )
        for elem in elem_list:
            options.append( ( elem, elem, False ) )
        return options
    def generate_for_dbkey( self, dbkey, dbkey_col, name_col, value_col, sep='\t' ):
        options = []
        d = {}
        for line in open( self.data_file_path ):
            line = line.rstrip( '\r\n' )
            if not line or line.startswith( '#' ) or ( self.line_startswith and not line.startswith ( self.line_startswith ) ):
                continue
            fields = line.split( sep )
            if self.data_file == 'maf_index.loc' or self.data_file == 'maf_pairwise.loc':
                try:
                    maf_desc = fields[ name_col ] # ENCODE TBA (hg17)
                    maf_uid = fields[ value_col ] # ENCODE_TBA_hg17
                    dbkeys = fields[ dbkey_col ] # armadillo=armadillo,baboon=baboon,galGal2=chicken,...
                    dbkey_list = []
                    split_dbkeys = dbkeys.split( ',' )
                    for b in split_dbkeys:
                        this_dbkey = b.split( '=' )[0]
                        dbkey_list.append( this_dbkey )
                    d[ maf_uid ] = {}
                    d[ maf_uid ][ 'description' ] = maf_desc
                    d[ maf_uid ][ 'builds' ] = dbkey_list
                except: 
                    continue
            else:
                if dbkey not in d:
                    d[ dbkey ] = []
                if dbkey == fields[ dbkey_col ].strip():
                    d[ dbkey ].append( ( fields[ name_col ], fields[ value_col ] ) )
        if self.data_file == 'maf_index.loc' or self.data_file == 'maf_pairwise.loc':
            for key in d:
                if dbkey in d[ key ][ 'builds' ]:
                    options.append( ( d[ key ][ 'description' ], key, False ) )
        else:
            if dbkey in d:
                for name, value in d[ dbkey ]:
                    options.append( ( name, value, False ) )
        return options
    def generate( self, name_col, value_col, sep='\t' ):
        options = []
        for line in open( self.data_file_path ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( sep )
                options.append( ( fields[ name_col ], fields[ value_col ], False ) )
        return sorted( options, key=operator.itemgetter(0) )


