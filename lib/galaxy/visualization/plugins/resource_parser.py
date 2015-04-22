import galaxy.util

import logging
log = logging.getLogger( __name__ )


class ResourceParser( object ):
    """
    Given a parameter dictionary (often a converted query string) and a
    configuration dictionary (curr. only VisualizationsRegistry uses this),
    convert the entries in the parameter dictionary into resources (Galaxy
    models, primitive types, lists of either, etc.) and return
    in a new dictionary.

    The keys used to store the new values can optionally be re-mapped to
    new keys (e.g. dataset_id="NNN" -> hda=<HistoryDatasetAsscoation>).
    """
    primitive_parsers = {
        'str'   : lambda param: galaxy.util.sanitize_html.sanitize_html( param, 'utf-8' ),
        'bool'  : lambda param: galaxy.util.string_as_bool( param ),
        'int'   : lambda param: int( param ),
        'float' : lambda param: float( param ),
        # 'date'  : lambda param: ,
        'json'  : ( lambda param: galaxy.util.json.loads(
            galaxy.util.sanitize_html.sanitize_html( param ) ) ),
    }

    # TODO: kinda torn as to whether this belongs here or in controllers.visualization
    #   taking the (questionable) design path of passing a controller in
    #       (which is the responsible party for getting model, etc. resources )
    # consider making this a base controller? use get_object for the model resources
    #   don't like passing in the app, tho
    def parse_parameter_dictionary( self, trans, controller, param_config_dict, query_params, param_modifiers=None ):
        """
        Parse all expected params from the query dictionary `query_params`.

        If param is required and not present, raises a `KeyError`.
        """
        # log.debug( 'parse_parameter_dictionary, query_params:\n%s', query_params )

        # parse the modifiers first since they modify the params coming next
        # TODO: this is all really for hda_ldda - which we could replace with model polymorphism
        params_that_modify_other_params = self.parse_parameter_modifiers(
            trans, controller, param_modifiers, query_params )

        resources = {}
        for param_name, param_config in param_config_dict.items():
            # optionally rename the variable returned, defaulting to the original name
            var_name_in_template = param_config.get( 'var_name_in_template', param_name )

            # if the param is present, get its value, any param modifiers for that param, and parse it into a resource
            # use try catch here and not caller to fall back on the default value or re-raise if required
            resource = None
            query_val = query_params.get( param_name, None )
            if query_val is not None:
                try:
                    target_param_modifiers = params_that_modify_other_params.get( param_name, None )
                    resource = self.parse_parameter( trans, controller, param_config,
                        query_val, param_modifiers=target_param_modifiers )

                except Exception, exception:
                    if trans.debug:
                        raise
                    else:
                        log.warn( 'Exception parsing visualization param from query: %s, %s, (%s) %s',
                                  param_name, query_val, str( type( exception ) ), str( exception ) )
                    resource = None

            # here - we've either had no value in the query_params or there was a failure to parse
            #   so: error if required, otherwise get a default (which itself defaults to None)
            if resource is None:
                if param_config[ 'required' ]:
                    raise KeyError( 'required param %s not found in URL' % ( param_name ) )
                resource = self.parse_parameter_default( trans, controller, param_config )

            resources[ var_name_in_template ] = resource

        return resources

    def parse_config( self, trans, controller, param_config_dict, query_params ):
        """
        Return `query_params` dict parsing only JSON serializable params.
        Complex params such as models, etc. are left as the original query value.
        Keys in `query_params` not found in the `param_config_dict` will not be
        returned.
        """
        # log.debug( 'parse_config, query_params:\n%s', query_params )
        config = {}
        for param_name, param_config in param_config_dict.items():
            config_val = query_params.get( param_name, None )
            if config_val is not None and param_config[ 'type' ] in self.primitive_parsers:
                try:
                    config_val = self.parse_parameter( trans, controller, param_config, config_val )

                except Exception, exception:
                    log.warn( 'Exception parsing visualization param from query: '
                        + '%s, %s, (%s) %s' % ( param_name, config_val, str( type( exception ) ), str( exception ) ))
                    config_val = None

            # here - we've either had no value in the query_params or there was a failure to parse
            #   so: if there's a default and it's not None, add it to the config
            if config_val is None:
                if param_config.get( 'default', None ) is None:
                    continue
                config_val = self.parse_parameter_default( trans, controller, param_config )

            config[ param_name ] = config_val

        return config

    # TODO: I would LOVE to rip modifiers out completely
    def parse_parameter_modifiers( self, trans, controller, param_modifiers, query_params ):
        """
        Parse and return parameters that are meant to modify other parameters,
        be grouped with them, or are needed to successfully parse other parameters.
        """
        # only one level of modification - down that road lies madness
        # parse the modifiers out of query_params first since they modify the other params coming next
        parsed_modifiers = {}
        if not param_modifiers:
            return parsed_modifiers
        # precondition: expects a two level dictionary
        # { target_param_name -> { param_modifier_name -> { param_modifier_data }}}
        for target_param_name, modifier_dict in param_modifiers.items():
            parsed_modifiers[ target_param_name ] = target_modifiers = {}

            for modifier_name, modifier_config in modifier_dict.items():
                query_val = query_params.get( modifier_name, None )
                if query_val is not None:
                    modifier = self.parse_parameter( trans, controller, modifier_config, query_val )
                    target_modifiers[ modifier_name ] = modifier
                else:
                    # TODO: required attr?
                    target_modifiers[ modifier_name ] = self.parse_parameter_default( trans, controller, modifier_config )

        return parsed_modifiers

    def parse_parameter_default( self, trans, controller, param_config ):
        """
        Parse any default values for the given param, defaulting the default
        to `None`.
        """
        # currently, *default* default is None, so this is quaranteed to be part of the dictionary
        default = param_config[ 'default' ]
        # if default is None, do not attempt to parse it
        if default is None:
            return default
        # otherwise, parse (currently param_config['default'] is a string just like query param and needs to be parsed)
        #   this saves us the trouble of parsing the default when the config file is read
        #   (and adding this code to the xml parser)
        return self.parse_parameter( trans, controller, param_config, default )

    def parse_parameter( self, trans, controller, expected_param_data, query_param,
                         recurse=True, param_modifiers=None ):
        """
        Use data in `expected_param_data` to parse `query_param` from a string into
        a resource usable directly by a template.

        'Primitive' types (string, int, etc.) are parsed here and more complex
        resources (such as ORM models) are parsed via the `controller` passed
        in.
        """
        param_type = expected_param_data.get( 'type' )
        # constrain_to = expected_param_data.get( 'constrain_to' )
        csv = expected_param_data.get( 'csv' )

        parsed_param = None

        # handle recursion for csv values
        if csv and recurse:
            parsed_param = []
            query_param_list = galaxy.util.listify( query_param )
            for query_param in query_param_list:
                parsed_param.append( self._parse_param( trans, expected_param_data, query_param, recurse=False ) )
            return parsed_param

        if param_type in self.primitive_parsers:
            # TODO: what about param modifiers on primitives?
            parsed_param = self.primitive_parsers[ param_type ]( query_param )

        # TODO: constrain_to: this gets complicated - remove?

        # db models
        # TODO: subclass here?
        elif param_type == 'visualization':
            encoded_visualization_id = query_param
            # log.debug( 'visualization param, id : %s', encoded_visualization_id )
            # TODO:?? some fallback if there's no get_X in controller that's passed?
            parsed_param = controller.get_visualization( trans, encoded_visualization_id,
                check_ownership=False, check_accessible=True )

        elif param_type == 'dataset':
            decoded_dataset_id = trans.security.decode_id( query_param )
            parsed_param = controller.hda_manager.get_accessible( decoded_dataset_id, trans.user )

        elif param_type == 'hda_or_ldda':
            encoded_dataset_id = query_param
            # needs info from another param...
            hda_ldda = param_modifiers.get( 'hda_ldda' )
            parsed_param = controller.get_hda_or_ldda( trans, hda_ldda, encoded_dataset_id )

        # TODO: ideally this would check v. a list of valid dbkeys
        elif param_type == 'dbkey':
            dbkey = query_param
            parsed_param = galaxy.util.sanitize_html.sanitize_html( dbkey, 'utf-8' )

        return parsed_param
