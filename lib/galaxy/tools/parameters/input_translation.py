"""
Tool Input Translation.
"""

import logging
from galaxy.util.bunch import Bunch

log = logging.getLogger( __name__ )

class ToolInputTranslator( object ):
    """
    Handles Tool input translation.
    This is used for data source tools

    >>> from galaxy.util import Params
    >>> from elementtree.ElementTree import XML
    >>> translator = ToolInputTranslator.from_element( XML(
    ... '''
    ... <request_param_translation>
    ...  <request_param galaxy_name="URL_method" remote_name="URL_method" missing="post" />
    ...  <request_param galaxy_name="URL" remote_name="URL" missing="" >
    ...     <append_param separator="&amp;" first_separator="?" join="=">
    ...         <value name="_export" missing="1" />
    ...         <value name="GALAXY_URL" missing="0" />
    ...     </append_param>
    ...  </request_param>
    ...  <request_param galaxy_name="dbkey" remote_name="db" missing="?" />
    ...  <request_param galaxy_name="organism" remote_name="org" missing="unknown species" />
    ...  <request_param galaxy_name="table" remote_name="hgta_table" missing="unknown table" />
    ...  <request_param galaxy_name="description" remote_name="hgta_regionType" missing="no description" />
    ...  <request_param galaxy_name="data_type" remote_name="hgta_outputType" missing="tabular" >
    ...   <value_translation>
    ...    <value galaxy_value="tabular" remote_value="primaryTable" />
    ...    <value galaxy_value="tabular" remote_value="selectedFields" />
    ...    <value galaxy_value="wig" remote_value="wigData" />
    ...    <value galaxy_value="interval" remote_value="tab" />
    ...    <value galaxy_value="html" remote_value="hyperlinks" />
    ...    <value galaxy_value="fasta" remote_value="sequence" />
    ...   </value_translation>
    ...  </request_param>
    ... </request_param_translation>
    ... ''' ) )
    >>> params = Params( { 'db':'hg17', 'URL':'URL_value', 'org':'Human', 'hgta_outputType':'primaryTable'  } )
    >>> translator.translate( params )
    >>> print params
    {'hgta_outputType': 'primaryTable', 'data_type': 'tabular', 'table': 'unknown table', 'URL': 'URL_value?GALAXY_URL=0&_export=1', 'org': 'Human', 'URL_method': 'post', 'db': 'hg17', 'organism': 'Human', 'dbkey': 'hg17', 'description': 'no description'}
    """
    @classmethod
    def from_element( cls, elem ):
        """Loads the proper filter by the type attribute of elem"""
        rval = ToolInputTranslator()
        for req_param in elem.findall( "request_param" ):
            # req_param tags must look like <request_param galaxy_name="dbkey" remote_name="GENOME" missing="" />
            #trans_list = []
            remote_name = req_param.get( "remote_name" )
            galaxy_name = req_param.get( "galaxy_name" )
            missing = req_param.get( "missing" )
            value_trans = {}
            append_param = None

            value_trans_elem = req_param.find( 'value_translation' )
            if value_trans_elem:
                for value_elem in value_trans_elem.findall( 'value' ):
                    remote_value = value_elem.get( "remote_value" )
                    galaxy_value = value_elem.get( "galaxy_value" )
                    if None not in [ remote_value, galaxy_value ]:
                        value_trans[ remote_value ] = galaxy_value

            append_param_elem = req_param.find( "append_param" )
            if append_param_elem:
                separator = append_param_elem.get( 'separator', ',' )
                first_separator = append_param_elem.get( 'first_separator', None )
                join_str = append_param_elem.get( 'join', '=' )
                append_dict = {}
                for value_elem in append_param_elem.findall( 'value' ):
                    value_name = value_elem.get( 'name' )
                    value_missing = value_elem.get( 'missing' )
                    if None not in [ value_name, value_missing ]:
                        append_dict[ value_name ] = value_missing
                append_param = Bunch( separator = separator, first_separator = first_separator, join_str = join_str, append_dict = append_dict )

            rval.param_trans_dict[ remote_name ] = Bunch( galaxy_name = galaxy_name, missing = missing, value_trans = value_trans, append_param = append_param  )

        return rval

    def __init__( self ):
        self.param_trans_dict = {}

    def translate( self, params ):
        """
        update params in-place
        """
        for remote_name, translator in self.param_trans_dict.iteritems():
            galaxy_name = translator.galaxy_name #NB: if a param by name galaxy_name is provided, it is always thrown away unless galaxy_name == remote_name
            value = params.get( remote_name, translator.missing ) #get value from input params, or use default value specified in tool config
            if translator.value_trans and value in translator.value_trans:
                value = translator.value_trans[ value ]
            if translator.append_param:
                for param_name, missing_value in translator.append_param.append_dict.iteritems():
                    param_value = params.get( param_name, missing_value )
                    if translator.append_param.first_separator and translator.append_param.first_separator not in value:
                        sep = translator.append_param.first_separator
                    else:
                        sep = translator.append_param.separator
                    value += '%s%s%s%s' % ( sep, param_name, translator.append_param.join_str, param_value )
            params.update( { galaxy_name: value } )
