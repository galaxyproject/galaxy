"""
Sample
"""
from galaxy.model import SampleState

class SampleStateFactory( object ):
    def new( self, request_type, name, description=None ):
        """
        Return new SampleState.
        """
        assert name, 'SampleState requires a name'
        if description is None:
            description = ''
        return SampleState( name=name, desc=description, request_type=request_type )
    def from_elem( self, request_type, elem ):
        """
        Return SampleState created from an xml string.
        """
        name = elem.get( 'name', None )
        description = elem.get( 'description', None )
        return self.new( request_type, name, description=description )

sample_state_factory = SampleStateFactory()
