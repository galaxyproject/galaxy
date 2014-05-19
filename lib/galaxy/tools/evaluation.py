import os
import tempfile

from galaxy import model
from galaxy.util.bunch import Bunch
from galaxy.util.none_like import NoneDataset
from galaxy.util.template import fill_template
from galaxy.tools.wrappers import (
    DatasetFilenameWrapper,
    DatasetListWrapper,
    DatasetCollectionWrapper,
    LibraryDatasetValueWrapper,
    SelectToolParameterWrapper,
    InputValueWrapper,
    RawObjectWrapper
)
from galaxy.tools.parameters.basic import (
    DataToolParameter,
    DataCollectionToolParameter,
    LibraryDatasetToolParameter,
    SelectToolParameter,
)
from galaxy.tools.parameters.grouping import Conditional, Repeat
from galaxy.jobs.datasets import dataset_path_rewrites

import logging
log = logging.getLogger( __name__ )


class ToolEvaluator( object ):
    """ An abstraction linking together a tool and a job runtime to evaluate
    tool inputs in an isolated, testable manner.
    """

    def __init__( self, app, tool, job, local_working_directory ):
        self.app = app
        self.job = job
        self.tool = tool
        self.local_working_directory = local_working_directory

    def set_compute_environment( self, compute_environment, get_special=None ):
        """
        Setup the compute environment and established the outline of the param_dict
        for evaluating command and config cheetah templates.
        """
        self.compute_environment = compute_environment
        self.unstructured_path_rewriter = compute_environment.unstructured_path_rewriter()

        job = self.job
        incoming = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        incoming = self.tool.params_from_strings( incoming, self.app )
        # Do any validation that could not be done at job creation
        self.tool.handle_unvalidated_param_values( incoming, self.app )
        # Restore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )

        if get_special:

            # Set up output dataset association for export history jobs. Because job
            # uses a Dataset rather than an HDA or LDA, it's necessary to set up a
            # fake dataset association that provides the needed attributes for
            # preparing a job.
            class FakeDatasetAssociation ( object ):
                def __init__( self, dataset=None ):
                    self.dataset = dataset
                    self.file_name = dataset.file_name
                    self.metadata = dict()
                    self.children = []

            special = get_special()
            if special:
                out_data[ "output_file" ] = FakeDatasetAssociation( dataset=special.dataset )

        # These can be passed on the command line if wanted as $__user_*__
        incoming.update( model.User.user_template_environment( job.history and job.history.user ) )

        # Build params, done before hook so hook can use
        param_dict = self.build_param_dict(
            incoming,
            inp_data,
            out_data,
            output_paths=compute_environment.output_paths(),
            job_working_directory=compute_environment.working_directory(),
            input_paths=compute_environment.input_paths()
        )

        # Certain tools require tasks to be completed prior to job execution
        # ( this used to be performed in the "exec_before_job" hook, but hooks are deprecated ).
        self.tool.exec_before_job( self.app, inp_data, out_data, param_dict )
        # Run the before queue ("exec_before_job") hook
        self.tool.call_hook( 'exec_before_job', self.app, inp_data=inp_data,
                             out_data=out_data, tool=self.tool, param_dict=incoming)

        self.param_dict = param_dict

    def build_param_dict( self, incoming, input_datasets, output_datasets, output_paths, job_working_directory, input_paths=[] ):
        """
        Build the dictionary of parameters for substituting into the command
        line. Each value is wrapped in a `InputValueWrapper`, which allows
        all the attributes of the value to be used in the template, *but*
        when the __str__ method is called it actually calls the
        `to_param_dict_string` method of the associated input.
        """
        param_dict = dict()
        param_dict.update(self.tool.template_macro_params)
        # All parameters go into the param_dict
        param_dict.update( incoming )

        input_dataset_paths = dataset_path_rewrites( input_paths )
        self.__populate_wrappers(param_dict, input_dataset_paths)
        self.__populate_input_dataset_wrappers(param_dict, input_datasets, input_dataset_paths)
        self.__populate_output_dataset_wrappers(param_dict, output_datasets, output_paths, job_working_directory)
        self.__populate_unstructured_path_rewrites(param_dict)
        self.__populate_non_job_params(param_dict)

        # Return the dictionary of parameters
        return param_dict

    def __walk_inputs(self, inputs, input_values, func):

        def do_walk( inputs, input_values ):
            """
            Wraps parameters as neccesary.
            """
            for input in inputs.itervalues():
                if isinstance( input, Repeat ):
                    for d in input_values[ input.name ]:
                        do_walk( input.inputs, d )
                elif isinstance( input, Conditional ):
                    values = input_values[ input.name ]
                    current = values["__current_case__"]
                    do_walk( input.cases[current].inputs, values )
                else:
                    func( input_values, input )

        do_walk( inputs, input_values )

    def __populate_wrappers(self, param_dict, input_dataset_paths):

        def wrap_input( input_values, input ):
            if isinstance( input, DataToolParameter ) and input.multiple:
                dataset_instances = input_values[ input.name ]
                if isinstance( dataset_instances, model.HistoryDatasetCollectionAssociation ):
                    dataset_instances = dataset_instances.collection.dataset_instances[:]
                input_values[ input.name ] = \
                    DatasetListWrapper( dataset_instances,
                                        dataset_paths=input_dataset_paths,
                                        datatypes_registry=self.app.datatypes_registry,
                                        tool=self.tool,
                                        name=input.name )
            elif isinstance( input, DataToolParameter ):
                ## FIXME: We're populating param_dict with conversions when
                ##        wrapping values, this should happen as a separate
                ##        step before wrapping (or call this wrapping step
                ##        something more generic) (but iterating this same
                ##        list twice would be wasteful)
                # Add explicit conversions by name to current parent
                for conversion_name, conversion_extensions, conversion_datatypes in input.conversions:
                    # If we are at building cmdline step, then converters
                    # have already executed
                    conv_ext, converted_dataset = input_values[ input.name ].find_conversion_destination( conversion_datatypes )
                    # When dealing with optional inputs, we'll provide a
                    # valid extension to be used for None converted dataset
                    if not conv_ext:
                        conv_ext = conversion_extensions[0]
                    # input_values[ input.name ] is None when optional
                    # dataset, 'conversion' of optional dataset should
                    # create wrapper around NoneDataset for converter output
                    if input_values[ input.name ] and not converted_dataset:
                        # Input that converter is based from has a value,
                        # but converted dataset does not exist
                        raise Exception( 'A path for explicit datatype conversion has not been found: %s --/--> %s'
                            % ( input_values[ input.name ].extension, conversion_extensions ) )
                    else:
                        # Trick wrapper into using target conv ext (when
                        # None) without actually being a tool parameter
                        input_values[ conversion_name ] = \
                            DatasetFilenameWrapper( converted_dataset,
                                                    datatypes_registry=self.app.datatypes_registry,
                                                    tool=Bunch( conversion_name=Bunch( extensions=conv_ext ) ),
                                                    name=conversion_name )
                # Wrap actual input dataset
                dataset = input_values[ input.name ]
                wrapper_kwds = dict(
                    datatypes_registry=self.app.datatypes_registry,
                    tool=self,
                    name=input.name
                )
                if dataset:
                    #A None dataset does not have a filename
                    real_path = dataset.file_name
                    if real_path in input_dataset_paths:
                        wrapper_kwds[ "dataset_path" ] = input_dataset_paths[ real_path ]
                input_values[ input.name ] = \
                    DatasetFilenameWrapper( dataset, **wrapper_kwds )
            elif isinstance( input, DataCollectionToolParameter ):
                dataset_collection = input_values[ input.name ]
                wrapper_kwds = dict(
                    datatypes_registry=self.app.datatypes_registry,
                    dataset_paths=input_dataset_paths,
                    tool=self,
                    name=input.name
                )
                wrapper = DatasetCollectionWrapper(
                    dataset_collection,
                    **wrapper_kwds
                )
                input_values[ input.name ] = wrapper
            elif isinstance( input, SelectToolParameter ):
                input_values[ input.name ] = SelectToolParameterWrapper(
                    input, input_values[ input.name ], self.app, other_values=param_dict, path_rewriter=self.unstructured_path_rewriter )
            elif isinstance( input, LibraryDatasetToolParameter ):
                # TODO: Handle input rewrites in here? How to test LibraryDatasetToolParameters?
                input_values[ input.name ] = LibraryDatasetValueWrapper(
                    input, input_values[ input.name ], param_dict )
            else:
                input_values[ input.name ] = InputValueWrapper(
                    input, input_values[ input.name ], param_dict )

        # HACK: only wrap if check_values is not false, this deals with external
        #       tools where the inputs don't even get passed through. These
        #       tools (e.g. UCSC) should really be handled in a special way.
        if self.tool.check_values:
            self.__walk_inputs( self.tool.inputs, param_dict, wrap_input )

    def __populate_input_dataset_wrappers(self, param_dict, input_datasets, input_dataset_paths):
        # TODO: Update this method for dataset collections? Need to test. -John.

        ## FIXME: when self.check_values==True, input datasets are being wrapped
        ##        twice (above and below, creating 2 separate
        ##        DatasetFilenameWrapper objects - first is overwritten by
        ##        second), is this necessary? - if we get rid of this way to
        ##        access children, can we stop this redundancy, or is there
        ##        another reason for this?
        ## - Only necessary when self.check_values is False (==external dataset
        ##   tool?: can this be abstracted out as part of being a datasouce tool?)
        ## - But we still want (ALWAYS) to wrap input datasets (this should be
        ##   checked to prevent overhead of creating a new object?)
        # Additionally, datasets go in the param dict. We wrap them such that
        # if the bare variable name is used it returns the filename (for
        # backwards compatibility). We also add any child datasets to the
        # the param dict encoded as:
        #   "_CHILD___{dataset_name}___{child_designation}",
        # but this should be considered DEPRECATED, instead use:
        #   $dataset.get_child( 'name' ).filename
        for name, data in input_datasets.items():
            param_dict_value = param_dict.get(name, None)
            if not isinstance(param_dict_value, (DatasetFilenameWrapper, DatasetListWrapper)):
                wrapper_kwds = dict(
                    datatypes_registry=self.app.datatypes_registry,
                    tool=self,
                    name=name,
                )
                if data:
                    real_path = data.file_name
                    if real_path in input_dataset_paths:
                        dataset_path = input_dataset_paths[ real_path ]
                        wrapper_kwds[ 'dataset_path' ] = dataset_path
                param_dict[name] = DatasetFilenameWrapper( data, **wrapper_kwds )
            if data:
                for child in data.children:
                    param_dict[ "_CHILD___%s___%s" % ( name, child.designation ) ] = DatasetFilenameWrapper( child )

    def __populate_output_dataset_wrappers(self, param_dict, output_datasets, output_paths, job_working_directory):
        output_dataset_paths = dataset_path_rewrites( output_paths )
        for name, hda in output_datasets.items():
            # Write outputs to the working directory (for security purposes)
            # if desired.
            real_path = hda.file_name
            if real_path in output_dataset_paths:
                dataset_path = output_dataset_paths[ real_path ]
                param_dict[name] = DatasetFilenameWrapper( hda, dataset_path=dataset_path )
                try:
                    open( dataset_path.false_path, 'w' ).close()
                except EnvironmentError:
                    pass  # May well not exist - e.g. LWR.
            else:
                param_dict[name] = DatasetFilenameWrapper( hda )
            # Provide access to a path to store additional files
            # TODO: path munging for cluster/dataset server relocatability
            param_dict[name].files_path = os.path.abspath(os.path.join( job_working_directory, "dataset_%s_files" % (hda.dataset.id) ))
            for child in hda.children:
                param_dict[ "_CHILD___%s___%s" % ( name, child.designation ) ] = DatasetFilenameWrapper( child )
        for out_name, output in self.tool.outputs.iteritems():
            if out_name not in param_dict and output.filters:
                # Assume the reason we lack this output is because a filter
                # failed to pass; for tool writing convienence, provide a
                # NoneDataset
                param_dict[ out_name ] = NoneDataset( datatypes_registry=self.app.datatypes_registry, ext=output.format )

    def __populate_non_job_params(self, param_dict):
        # -- Add useful attributes/functions for use in creating command line.

        # Function for querying a data table.
        def get_data_table_entry(table_name, query_attr, query_val, return_attr):
            """
            Queries and returns an entry in a data table.
            """

            if table_name in self.app.tool_data_tables:
                return self.app.tool_data_tables[ table_name ].get_entry( query_attr, query_val, return_attr )

        param_dict['__get_data_table_entry__'] = get_data_table_entry

        # We add access to app here, this allows access to app.config, etc
        param_dict['__app__'] = RawObjectWrapper( self.app )
        # More convienent access to app.config.new_file_path; we don't need to
        # wrap a string, but this method of generating additional datasets
        # should be considered DEPRECATED
        # TODO: path munging for cluster/dataset server relocatability
        param_dict['__new_file_path__'] = os.path.abspath(self.compute_environment.new_file_path())
        # The following points to location (xxx.loc) files which are pointers
        # to locally cached data
        param_dict['__tool_data_path__'] = param_dict['GALAXY_DATA_INDEX_DIR'] = self.app.config.tool_data_path
        # For the upload tool, we need to know the root directory and the
        # datatypes conf path, so we can load the datatypes registry
        param_dict['__root_dir__'] = param_dict['GALAXY_ROOT_DIR'] = os.path.abspath( self.app.config.root )
        param_dict['__datatypes_config__'] = param_dict['GALAXY_DATATYPES_CONF_FILE'] = self.app.datatypes_registry.integrated_datatypes_configs
        param_dict['__admin_users__'] = self.app.config.admin_users
        param_dict['__user__'] = RawObjectWrapper( param_dict.get( '__user__', None ) )

    def __populate_unstructured_path_rewrites(self, param_dict):

        def rewrite_unstructured_paths( input_values, input ):
            if isinstance( input, SelectToolParameter ):
                input_values[ input.name ] = SelectToolParameterWrapper(
                    input, input_values[ input.name ], self.app, other_values=param_dict, path_rewriter=self.unstructured_path_rewriter )

        if not self.tool.check_values and self.unstructured_path_rewriter:
            # The tools weren't "wrapped" yet, but need to be in order to get
            #the paths rewritten.
            self.__walk_inputs( self.tool.inputs, param_dict, rewrite_unstructured_paths )

    def build( self ):
        """
        Build runtime description of job to execute, evaluate command and
        config templates corresponding to this tool with these inputs on this
        compute environment.
        """
        self.extra_filenames = []
        self.command_line = None

        self.__build_config_files( )
        self.__build_param_file( )
        self.__build_command_line( )

        return self.command_line, self.extra_filenames

    def __build_command_line( self ):
        """
        Build command line to invoke this tool given a populated param_dict
        """
        command = self.tool.command
        param_dict = self.param_dict
        interpreter = self.tool.interpreter
        command_line = None
        if not command:
            return
        try:
            # Substituting parameters into the command
            command_line = fill_template( command, context=param_dict )
            # Remove newlines from command line, and any leading/trailing white space
            command_line = command_line.replace( "\n", " " ).replace( "\r", " " ).strip()
        except Exception:
            # Modify exception message to be more clear
            #e.args = ( 'Error substituting into command line. Params: %r, Command: %s' % ( param_dict, self.command ), )
            raise
        if interpreter:
            # TODO: path munging for cluster/dataset server relocatability
            executable = command_line.split()[0]
            tool_dir = os.path.abspath( self.tool.tool_dir )
            abs_executable = os.path.join( tool_dir, executable )
            command_line = command_line.replace(executable, abs_executable, 1)
            command_line = interpreter + " " + command_line
        self.command_line = command_line

    def __build_config_files( self ):
        """
        Build temporary file for file based parameter transfer if needed
        """
        param_dict = self.param_dict
        config_filenames = []
        for name, filename, template_text in self.tool.config_files:
            # If a particular filename was forced by the config use it
            directory = self.local_working_directory
            if filename is not None:
                config_filename = os.path.join( directory, filename )
            else:
                fd, config_filename = tempfile.mkstemp( dir=directory )
                os.close( fd )
            f = open( config_filename, "wt" )
            f.write( fill_template( template_text, context=param_dict ) )
            f.close()
            # For running jobs as the actual user, ensure the config file is globally readable
            os.chmod( config_filename, 0644 )
            self.__register_extra_file( name, config_filename )
            config_filenames.append( config_filename )
        return config_filenames

    def __build_param_file( self ):
        """
        Build temporary file for file based parameter transfer if needed
        """
        param_dict = self.param_dict
        directory = self.local_working_directory
        command = self.tool.command
        if command and "$param_file" in command:
            fd, param_filename = tempfile.mkstemp( dir=directory )
            os.close( fd )
            f = open( param_filename, "wt" )
            for key, value in param_dict.items():
                # parameters can be strings or lists of strings, coerce to list
                if type(value) != type([]):
                    value = [ value ]
                for elem in value:
                    f.write( '%s=%s\n' % (key, elem) )
            f.close()
            self.__register_extra_file( 'param_file', param_filename )
            return param_filename
        else:
            return None

    def __register_extra_file( self, name, local_config_path ):
        """
        Takes in the local path to a config file and registers the (potentially
        remote) ultimate path of the config file with the parameter dict.
        """
        self.extra_filenames.append( local_config_path )
        config_basename = os.path.basename( local_config_path )
        compute_config_path = self.__join_for_compute(self.compute_environment.config_directory(), config_basename)
        self.param_dict[ name ] = compute_config_path

    def __join_for_compute( self, *args ):
        """
        os.path.join but with compute_environment.sep for cross-platform
        compat.
        """
        return self.compute_environment.sep().join( args )
