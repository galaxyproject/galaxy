"""
Constructs for grouping tool parameters
"""

from basic import ToolParameter

class Group( object ):
    def __init__( self ):
        self.name = None
        self.inputs = None
    def value_to_basic( self, value, app ):
        """
        Convert value to a (possibly nested) representation using only basic
        types (dict, list, tuple, str, unicode, int, long, float, bool, None)
        """
        return value
    def value_from_basic( self, value, app, ignore_errors=False ):
        """
        Convert a basic representation as produced by `value_to_basic` back
        into the preferred value form.
        """
        return value
        
class Repeat( Group ):
    type = "repeat"
    def __init__( self ):
        self.name = None
        self.title = None
        self.inputs = None
    @property
    def title_plural( self ):
        if self.title.endswith( "s" ):
            return self.title
        else:
            return self.title + "s"
    def value_to_basic( self, value, app ):
        rval = []
        for d in value:
            rval_dict = {}
            # Propogate __index__
            if '__index__' in d:
                rval_dict['__index__'] = d['__index__']
            for input in self.inputs.itervalues():
                rval_dict[ input.name ] = input.value_to_basic( d[input.name], app )
            rval.append( rval_dict )
        return rval
    def value_from_basic( self, value, app, ignore_errors=False ):
        rval = []
        for i, d in enumerate( value ):
            rval_dict = {}
            # If the special __index__ key is not set, create it (for backward
            # compatibility)
            rval_dict['__index__'] = d.get( '__index__', i )
            # Restore child inputs
            for input in self.inputs.itervalues():
                rval_dict[ input.name ] = input.value_from_basic( d[input.name], app, ignore_errors )
            rval.append( rval_dict )
        return rval 
    def visit_inputs( self, prefix, value, callback ):
        for i, d in enumerate( value ):
            for input in self.inputs.itervalues():
                new_prefix = prefix + "%s_%d|" % ( self.name, i )
                if isinstance( input, ToolParameter ):
                    callback( new_prefix, input, d[input.name] )
                else:
                    input.visit_inputs( new_prefix, d[input.name], callback )  
        
class Conditional( Group ):
    type = "conditional"
    def __init__( self ):
        self.name = None
        self.test_param = None
        self.cases = []
    def get_current_case( self, value, trans ):
        # Convert value to user representation
        str_value = self.test_param.filter_value( value, trans )
        # Find the matching case
        for index, case in enumerate( self.cases ):
            if str_value == case.value:
                return index
        raise Exception( "No case matched value:", self.name, str_value )
    def value_to_basic( self, value, app ):
        rval = dict()
        current_case = rval['__current_case__'] = value['__current_case__']
        rval[ self.test_param.name ] = self.test_param.value_to_basic( value[ self.test_param.name ], app )
        for input in self.cases[current_case].inputs.itervalues():
            rval[ input.name ] = input.value_to_basic( value[ input.name ], app )
        return rval
    def value_from_basic( self, value, app, ignore_errors=False ):
        rval = dict()
        current_case = rval['__current_case__'] = value['__current_case__']
        rval[ self.test_param.name ] = self.test_param.value_from_basic( value[ self.test_param.name ], app, ignore_errors )
        for input in self.cases[current_case].inputs.itervalues():
            rval[ input.name ] = input.value_from_basic( value[ input.name ], app, ignore_errors )
        return rval
    def visit_inputs( self, prefix, value, callback ):
        current_case = value['__current_case__']
        new_prefix = prefix + "%s|" % ( self.name )
        for input in self.cases[current_case].inputs.itervalues():
            if isinstance( input, ToolParameter ):
                callback( prefix, input, value[input.name] )
            else:
                input.visit_inputs( prefix, value[input.name], callback )
                         
class ConditionalWhen( object ):
    def __init__( self ):
        self.value = None
        self.inputs = None