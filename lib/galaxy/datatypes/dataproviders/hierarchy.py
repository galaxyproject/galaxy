"""
Dataproviders that iterate over lines from their sources.
"""

import line
from xml.etree.ElementTree import Element, iterparse

_TODO = """
"""

import logging
log = logging.getLogger( __name__ )


# ----------------------------------------------------------------------------- hierarchal/tree data providers
class HierarchalDataProvider( line.BlockDataProvider ):
    """
    Class that uses formats where a datum may have a parent or children
    data.

    e.g. XML, HTML, GFF3, Phylogenetic
    """
    def __init__( self, source, **kwargs ):
        # TODO: (and defer to better (than I can write) parsers for each subtype)
        super( HierarchalDataProvider, self ).__init__( source, **kwargs )


# ----------------------------------------------------------------------------- xml
class XMLDataProvider( HierarchalDataProvider ):
    """
    Data provider that converts selected XML elements to dictionaries.
    """
    # using xml.etree's iterparse method to keep mem down
    # TODO:   this, however (AFAIK), prevents the use of xpath
    settings = {
        'selector'  : 'str',  # urlencoded
        'max_depth' : 'int',
    }
    ITERPARSE_ALL_EVENTS = ( 'start', 'end', 'start-ns', 'end-ns' )
    # TODO: move appropo into super

    def __init__( self, source, selector=None, max_depth=None, **kwargs ):
        """
        :param  selector:   some partial string in the desired tags to return
        :param  max_depth:  the number of generations of descendents to return
        """
        self.selector = selector
        self.max_depth = max_depth
        self.namespaces = {}

        super( XMLDataProvider, self ).__init__( source, **kwargs )

    def matches_selector( self, element, selector=None ):
        """
        Returns true if the ``element`` matches the ``selector``.

        :param  element:    an XML ``Element``
        :param  selector:   some partial string in the desired tags to return

        Change point for more sophisticated selectors.
        """
        # search for partial match of selector to the element tag
        # TODO: add more flexibility here w/o re-implementing xpath
        # TODO: fails with '#' - browser thinks it's an anchor - use urlencode
        # TODO: need removal/replacement of etree namespacing here - then move to string match
        return bool( ( selector is None ) or
                     ( isinstance( element, Element ) and selector in element.tag ) )

    def element_as_dict( self, element ):
        """
        Converts an XML element (its text, tag, and attributes) to dictionary form.

        :param  element:    an XML ``Element``
        """
        # TODO: Key collision is unlikely here, but still should be better handled
        return {
            'tag'      : element.tag,
            'text'     : element.text.strip() if element.text else None,
            # needs shallow copy to protect v. element.clear()
            'attrib'   : dict( element.attrib )
        }

    def get_children( self, element, max_depth=None ):
        """
        Yield all children of element (and their children - recursively)
        in dictionary form.
        :param  element:    an XML ``Element``
        :param  max_depth:  the number of generations of descendents to return
        """
        if not isinstance( max_depth, int ) or max_depth >= 1:
            for child in element.getchildren():
                child_data = self.element_as_dict( child )

                next_depth = max_depth - 1 if isinstance( max_depth, int ) else None
                grand_children = list( self.get_children( child, next_depth ) )
                if grand_children:
                    child_data[ 'children' ] = grand_children

                yield child_data

    def __iter__( self ):
        context = iterparse( self.source, events=self.ITERPARSE_ALL_EVENTS )
        context = iter( context )

        selected_element = None
        for event, element in context:
            if event == 'start-ns':
                ns, uri = element
                self.namespaces[ ns ] = uri

            elif event == 'start':
                if( ( selected_element is None ) and
                        ( self.matches_selector( element, self.selector ) ) ):
                    # start tag of selected element - wait for 'end' to emit/yield
                    selected_element = element

            elif event == 'end':
                if( ( selected_element is not None ) and ( element == selected_element ) ):
                    self.num_valid_data_read += 1

                    # offset
                    if self.num_valid_data_read > self.offset:
                        # convert to dict and yield
                        selected_element_dict = self.element_as_dict( selected_element )
                        children = list( self.get_children( selected_element, self.max_depth ) )
                        if children:
                            selected_element_dict[ 'children' ] = children
                        yield selected_element_dict

                        # limit
                        self.num_data_returned += 1
                        if self.limit is not None and self.num_data_returned >= self.limit:
                            break

                    selected_element.clear()
                    selected_element = None

                self.num_data_read += 1
