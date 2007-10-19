
import sys, os, logging

log = logging.getLogger(__name__)

class DynamicOptions( object ):
    """Handles dynamically generated SelectToolParameter options"""
    def __init__( self, elem  ):
        self.data_ref = elem.get( 'data_ref', None)
        self.from_file = elem.get( 'from_file', None )
        assert self.from_file is not None, "Value for option data file not found"
        self.func = elem.get( 'func', None )
        assert self.func is not None, "Value for option generator function not found"
        self.func_params = elem.findall( 'func_param' )
    def get_dataset( self, trans, other_values ):
        # No value indicates a configuration error, the named DataToolParameter must preceed this parameter in the tool config
        assert self.data_ref in other_values, "Value for associated DataToolParameter not found"
        # Get the value of the associated DataToolParameter (a dataset)
        dataset = other_values[ self.data_ref ]
        if dataset is None or dataset == '':
            """
            Both of these values indicate that no dataset is selected.  However, 'None' indicates that the dataset is optional 
            while '' indicates that it is not. Currently column parameters do not work well with optional datasets.
            """
            return None
        # TODO: this can be eliminated after Dan's script is run.
        dataset.set_meta()
        return dataset
    #TODO: the following functions should be generalized so that they are not specific to
    #certain tools (e.g., encode).  We may need to standardize data file formats to be able to do this.
    def load_from_file_for_build( self ):
        dict = {}
        for line in open( self.from_file ):
            if line and not line.startswith( '#' ):
                try:
                    fields = line.rstrip('\r\n').split( "\t" )
                    if not fields[0] in dict: 
                        dict[ fields[0] ] = []
                    dict[ fields[0] ].append( (fields[1], fields[2]) )
                except:
                    continue
        return dict
    def get_options_for_build( self, trans, other_values ):
        legal_values = set()
        options = []
        dataset = self.get_dataset( trans, other_values )
        if dataset is None:
            return legal_values, options
        dict = self.load_from_file_for_build()
        if dataset.dbkey in dict:
            for (descript, scorefile) in dict[ dataset.dbkey ]:
                options.append( (descript, scorefile, False) )
                legal_values.add( scorefile )
        return legal_values, options
    def load_from_file_for_encode( self ):
        encode_sets= {}
        legal_values = set()
        try:
            for line in open( self.from_file ):
                if line and not line.startswith( '#' ):
                    try:
                        fields = line.rstrip('\r\n').split( "\t" )
                        encode_group = fields[0]
                        build = fields[1]
                        description = fields[2]
                        uid = fields[3]
                        path = fields[4]
                        try: file_type = fields[5]
                        except: file_type = "bed"
                        #TODO: will remove this later, when galaxy can handle gff files
                        if file_type != "bed": continue
                        #verify that file exists before making it an option
                        if not os.path.isfile(path):
                            continue
                    except:
                        continue
                    #check if group is initialized, if not inititalize
                    try: temp = encode_sets[encode_group]
                    except: encode_sets[encode_group] = {}
                    #add data to group in proper build
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
                        item['uid']=uid
                        item['selected']=selected
                        item['partitioned']=False
                        
                        if description[-21:]=='[gencode_partitioned]':
                            item['date'] = description[-31:-23]
                            item['description'] = description[0:-32]
                            item['partitioned']=True
                        else:
                            item['date'] = description[-9:-1]
                            item['description'] = description[0:-10]
                            
                        for i in range(len(ordered_build)):
                            ordered_description, ordered_uid, ordered_selected, ordered_item = ordered_build[i]
                            if item['description'] < ordered_item['description']:
                                ordered_build.insert(i, (description, uid, selected, item) )
                                break
                            if item['description'] == ordered_item['description'] and item['partitioned'] == ordered_item['partitioned']:
                                if int(item['date']) > int(ordered_item['date']):
                                    ordered_build.insert(i, (description, uid, selected, item) )
                                    break
                        else:
                            ordered_build.append( (description, uid, selected, item) )
                    
                    last_desc = None
                    last_partitioned = None
                    for i in range(len(ordered_build)) :
                        description, uid, selected, item = ordered_build[i]
                        if item['partitioned'] != last_partitioned or last_desc != item['description']:
                            last_desc = item['description']
                            description = "<b>"+description+"</b>"
                        else:
                            last_desc = item['description']
                        last_partitioned = item['partitioned']
                        encode_sets[group][build][i] = (description, uid, selected)        
        except Exception, exc:
            #TODO: Fix this...
            print >>sys.stdout, 'load_from_file_for_encode: initialization error -> %s' % exc
        return legal_values, encode_sets
    #return available datasets for group and build, set None option as selected for hg16
    def get_options_for_encode( self, trans, other_values ):
        assert len( self.func_params ) == 2, "Values for 'build' and 'encode group' not found"
        for func_param in self.func_params:
            if func_param.get( 'name' ).strip() == 'build':
                build = func_param.get( 'value' ).strip()
            elif func_param.get( 'name' ).strip() == 'encode_group':
                encode_group = func_param.get( 'value' ).strip()
        legal_values = set()
        options = []
        legal_values, dict = self.load_from_file_for_encode()
        if len( dict ) < 1:
            options.append(('No data available for this build','None',True))
            legal_values.add( 'None' )
        else:
            try: 
                options = dict[encode_group][build][0:]
            except:
                options.append(('No data available for this build','None',True))
                legal_values.add( 'None' )
        return legal_values, options
