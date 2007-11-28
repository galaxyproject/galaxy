
import sys, os, logging

log = logging.getLogger(__name__)

class DynamicOptions( object ):
    """Handles dynamically generated SelectToolParameter options"""
    def __init__( self, elem  ):
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
        else: self.data_file = None
        if elem.tag == 'select_options':
            self.data_ref = elem.get( 'data_ref', None )
            self.param_ref = elem.get( 'param_ref', None )
            self.func = elem.get( 'func', None )
            assert self.func is not None, "Value for option generator function not found"
            self.func_params = elem.findall( 'func_param' )
        else: #elem.tag =='options'
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
        #FIXME: this attr is used only by microbial import, so shouldn't be at this level
        self.microbe_info = None
    def get_dataset( self, trans, other_values ):
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
    def get_param_value( self, trans, other_values ):
        if self.param_ref is None: return None
        assert self.param_ref in other_values, "Value for associated parameter %s not found" %self.param_ref.name
        return other_values[ self.param_ref ]
    def get_unique_elems( self, elems ): 
        seen = set()
        return [ x for x in elems if x not in seen and not seen.add( x ) ]
    def get_options( self, trans, other_values, must_be_valid = False ):
        filters = {}
        key = None
        # Check for filters and build a dictionary from them
        for filter in self.filters:
            filter_type = filter.get( 'type', None )
            assert filter_type is not None, "type attribute missing from filter"
            filter_type = filter_type.strip()
            if filter_type == 'data_meta':
                filters[ 'data_meta' ] = {}
                dataset = self.get_dataset( trans, other_values )
                if dataset is None: return []
                key = filter.get( 'key', None )
                assert key is not None, "key attribute missing from data_meta filter"
                filters[ 'data_meta' ][ 'key' ] = key.strip()
                value = filter.get( 'value', None )
                if value is not None: value = value.strip()
                else:
                    if key == 'build': value = dataset.get_dbkey()
                    elif key == 'file_name': value = dataset.get_file_name()
                    elif key == 'species': value = dataset.metadata.species
                    elif key == 'maf': pass # value does not need to be set, maf tools require special handling - see below
                filters[ 'data_meta' ][ 'value' ] = value
                if self.data_file == 'maf_index.loc' and key == 'build' and value == '?':
                    if must_be_valid: return []
                    return self.build_not_set_option
            elif filter_type == 'param_meta':
                filters[ 'param_meta' ] = {}
                key = filter.get( 'key', None )
                assert key is not None, "key attribute missing from param_meta filter"
                filters[ 'param_meta' ][ 'key' ] = key.strip()
                value = self.get_param_value( trans, other_values )
                filters[ 'param_meta' ][ 'value' ] = value
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
                # TODO: I'm not sure I like the way 'param' filters are implemented, I may be rethinking this approach...
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
        # Now that we've parsed our filters, we need to see if the tool is a maf tool which requires special handling
        try: key = filters[ 'data_meta' ][ 'key' ]
        except: key == None
        if key == 'maf':
            maf_source = filters[ 'params' ][ 'maf_source' ]
            if maf_source == 'cached':
                maf_uid = filters[ 'param_meta' ][ 'value' ]
                if maf_uid in [None, 'None']:
                    if must_be_valid: return []
                    if maf_uid is None: return self.no_data_option
                    if maf_uid == 'None': return self.build_not_set_option
            elif maf_source == 'user':
                dataset = self.get_dataset( trans, other_values )
                if dataset is None: return self.wait_for_maf_option
                filters[ 'data_meta' ][ 'key' ] = 'species'
                filters[ 'data_meta' ][ 'value' ] = dataset.metadata.species
        return self.generate_options( filters, must_be_valid = must_be_valid )
    def generate_options( self, filters={}, sep='\t', must_be_valid = False ):
        # Extract the info from the tool's options filters, if any
        try: key = filters[ 'data_meta' ][ 'key' ]
        except: key = None
        try: value = filters[ 'data_meta' ][ 'value' ]
        except: value = None
        if key is None and value is None:
            # Look for param_meta filter
            try: key = filters[ 'param_meta' ][ 'key' ]
            except: key = None
            try: value = filters[ 'param_meta' ][ 'value' ]
            except: value = None
        try: name_col = int( filters[ 'columns' ][ 'name_col' ] )
        except: name_col = None
        try: value_col = int( filters[ 'columns' ][ 'value_col' ] )
        except: value_col = None
        try: encode_group = filters[ 'params' ][ 'encode_group' ]
        except: encode_group = None
        try: build = filters[ 'params' ][ 'build' ]
        except: build = None
        try: maf_source = filters[ 'params' ][ 'maf_source' ]
        except: maf_source = None

        # Order of the following conditionals is critical
        if encode_group is not None and build is not None:
            return self.generate_from_file_for_encode( encode_group, build, must_be_valid = must_be_valid )
        elif key == 'species':
            return self.generate_from_dataset_for_species( value )
        elif key == 'maf':
            return self.generate_from_file_for_maf( maf_source, value, must_be_valid = must_be_valid )
        elif key == 'file_name':
            return self.generate_from_dataset( value, value_col )
        elif key == 'build':
            build_col = int( filters[ 'columns' ][ 'build_col' ].strip() )
            return self.generate_from_file_for_build( value, build_col, name_col, value_col, must_be_valid = must_be_valid )
        elif key is None:
            return self.generate_from_file( name_col, value_col )
    def generate_from_file_for_encode( self, encode_group, build, sep='\t', must_be_valid = False ):
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
                        try: file_type = fields[ 5 ]
                        except: file_type = "bed"
                        #TODO: will remove this later, when galaxy can handle gff files
                        if file_type != "bed": continue
                        if not os.path.isfile( path ): continue
                    except: continue
                    try: temp = encode_sets[ encode_group ]
                    except: encode_sets[ encode_group ] = {}
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
                        else: ordered_build.append( ( description, uid, selected, item ) )
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
            if must_be_valid: return []
            return self.no_data_option_not_selected
        else:
            try: options = d[ encode_group ][ build ][ 0: ]
            except:
                if must_be_valid: return []
                return self.no_data_option_not_selected
        return options
    def generate_from_dataset_for_species( self, value ):
        options = []
        for species in value:
            options.append( ( species, species, False ) )
        return options
    def generate_from_file_for_maf( self, maf_source, maf_uid, sep='\t', must_be_valid = False ):
        options = []
        d = {}
        # We will only reach here if the maf-source param value is 'cached'
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
                except: continue
        for key in d[ maf_uid ][ 'builds' ]:
            options.append( ( key, key, False ) )
        if not options:
            if must_be_valid: return []
            return self.no_data_option
        return options
    def generate_from_dataset( self, value, value_col, sep='\t', must_be_valid = False ):
        options = []
        elem_list = []
        try: in_file = open( value, "r" )
        except:
            if must_be_valid: return []
            return self.no_data_option
        try:
            for line in in_file:
                line = line.rstrip( "\r\n" )
                if line and not line.startswith( '#' ):
                    elems = line.split( sep )
                    elem_list.append( elems[ value_col ] )
        except: pass
        in_file.close()
        if not( elem_list ):
            if must_be_valid: return []
            return self.no_elems_option
        elem_list = self.get_unique_elems( elem_list )
        for elem in elem_list:
            options.append( ( elem, elem, False ) )
        return options
    def generate_from_file_for_build( self, value, build_col, name_col, value_col, sep='\t', must_be_valid = False ):
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
                        try: d[ fields[ name_col ] ].append( fields[ value_col ] )
                        except: d[ fields[ name_col ] ] = [ fields[ value_col ] ]
                elif self.data_file == 'regions.loc' or self.data_file == 'phastOdds.loc' or self.data_file == 'binned_scores.loc':
                    if not fields[ build_col ] in d: 
                        d[ fields[ build_col ] ] = []
                    d[ fields[ build_col ] ].append( (fields[ name_col ], fields[ value_col ]) )
                elif self.data_file == 'maf_index.loc':
                    try:
                        maf_desc = fields[ name_col ] # ENCODE TBA (hg17)
                        maf_uid = fields[ value_col ] # ENCODE_TBA_hg17
                        builds = fields[ build_col ] # armadillo=armadillo,baboon=baboon,galGal2=chicken,...
                        build_list = []
                        split_builds = builds.split( ',' )
                        for build in split_builds:
                            this_build = build.split( '=' )[0]
                            build_list.append( this_build )
                        d[ maf_uid ] = {}
                        d[ maf_uid ][ 'description' ] = maf_desc
                        d[ maf_uid ][ 'builds' ] = build_list
                    except: continue

        # TODO: the alignseq.loc file is currently ony used by the "Extract blastz alignments1"
        # tool, which seems to be deprecated.  Can we eliminate it altogether?
        if self.data_file == 'alignseq.loc':
            # FIXME: We need a database of descriptive names corresponding to dbkeys.
            #        We need to resolve the musMusX <--> mmX confusion
            if value[ 0:2 ] == "mm": value = value.replace( 'mm', 'musMus' )
            if value[ 0:2 ] == "rn": value = value.replace( 'rn', 'ratNor' )
            if value in d:
                for val in d[ value ]:
                    options.append( ( val, val, False ) )
        elif self.data_file == 'regions.loc' or self.data_file == 'phastOdds.loc' or self.data_file == 'binned_scores.loc':
            if value in d:
                for (key, val) in d[ value ]:
                    options.append( ( key, val, False ) )
        elif self.data_file == 'maf_index.loc':
            for key in d:
                if value in d[ key ][ 'builds' ]:
                    options.append( ( d[ key ][ 'description' ], key, False ) )
            if not options:
                if must_be_valid: return []
                return self.no_data_option
        if not options: 
            if must_be_valid: return []
            return self.unspecified_build_option
        return options
    def generate_from_file( self, name_col, value_col, sep='\t' ):
        options = []
        for line in open( self.from_file ):
            line = line.rstrip( '\r\n' )
            if line and not line.startswith( '#' ):
                fields = line.split( sep )
                # TODO: this option list should be sorted
                options.append( ( fields[ name_col ], fields[ value_col ], False ) )
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
        if options:
            options[0] = ( options[0][0], options[0][1], True)
        return options
    def get_options_for_orgs_by_kingdom( self, trans, other_values ):
        if self.microbe_info == None: self.load_from_file_for_microbial()
        options = []
        for func_param in self.func_params:
            if func_param.get( 'name' ) == 'kingdom':
                kingdom = other_values[ func_param.get( 'value' ) ]
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
        if options:
            options[0] = ( options[0][0], options[0][1], True)
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

