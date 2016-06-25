import datetime
import uuid


class Dictifiable:
    """ Mixin that enables objects to be converted to dictionaries. This is useful
        when for sharing objects across boundaries, such as the API, tool scripts,
        and JavaScript code. """

    def to_dict( self, view='collection', value_mapper=None ):
        """
        Return item dictionary.
        """

        if not value_mapper:
            value_mapper = {}

        def get_value( key, item ):
            """
            Recursive helper function to get item values.
            """
            # FIXME: why use exception here? Why not look for key in value_mapper
            # first and then default to to_dict?
            try:
                return item.to_dict( view=view, value_mapper=value_mapper )
            except:
                if key in value_mapper:
                    return value_mapper.get( key )( item )
                if type(item) == datetime.datetime:
                    return item.isoformat()
                elif type(item) == uuid.UUID:
                    return str(item)
                # Leaving this for future reference, though we may want a more
                # generic way to handle special type mappings going forward.
                # If the item is of a class that needs to be 'stringified' before being put into a JSON data structure
                # elif type(item) in []:
                #    return str(item)
                return item

        # Create dict to represent item.
        rval = dict(
            model_class=self.__class__.__name__
        )

        # Fill item dict with visible keys.
        try:
            visible_keys = self.__getattribute__( 'dict_' + view + '_visible_keys' )
        except AttributeError:
            raise Exception( 'Unknown Dictifiable view: %s' % view )
        for key in visible_keys:
            try:
                item = self.__getattribute__( key )
                if isinstance( item, list ):
                    rval[ key ] = []
                    for i in item:
                        rval[ key ].append( get_value( key, i ) )
                else:
                    rval[ key ] = get_value( key, item )
            except AttributeError:
                rval[ key ] = None

        return rval
