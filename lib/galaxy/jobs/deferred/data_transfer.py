"""
Module for managing data transfer jobs.
"""
import logging, urllib2, re, shutil

from galaxy import eggs
from sqlalchemy import and_

from galaxy.util.odict import odict
from galaxy.workflow.modules import module_factory
from galaxy.jobs.actions.post import ActionBox
from galaxy.jobs.deferred import FakeTrans

from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.basic import DataToolParameter
from galaxy.datatypes import sniff

log = logging.getLogger( __name__ )

__all__ = [ 'DataTransfer' ]

class DataTransfer( object ):
    check_interval = 15
    dataset_name_re = re.compile( '(dataset\d+)_(name)' )
    dataset_datatype_re = re.compile( '(dataset\d+)_(datatype)' )
    def __init__( self, app ):
        self.app = app
        self.sa_session = app.model.context.current
    def create_job( self, trans, **kwd ):
        raise Exception( "Unimplemented Method" )
    def check_job( self, job ):
        raise Exception( "Unimplemented Method" )
    def run_job( self, job ):
        if job.params[ 'type' ] == 'init_transfer':
            # TODO: don't create new downloads on restart.
            if job.params[ 'protocol' ] in [ 'http', 'https' ]:
                results = []
                for result in job.params[ 'results' ].values():
                    result[ 'transfer_job' ] = self.app.transfer_manager.new( protocol=job.params[ 'protocol' ],
                                                                              name=result[ 'name' ],
                                                                              datatype=result[ 'datatype' ],
                                                                              url=result[ 'url' ] )
                    results.append( result )
            elif job.params[ 'protocol' ] == 'scp':
                results = []
                result = {}
                sample_datasets_dict = job.params[ 'sample_datasets_dict' ]
                # sample_datasets_dict looks something like the following.  The outer dictionary keys are SampleDataset ids.
                # {'7': {'status': 'Not started', 'name': '3.bed', 'file_path': '/tmp/library/3.bed', 'sample_id': 7,
                #        'external_service_id': 2, 'error_msg': '', 'size': '8.0K'}}
                for sample_dataset_id, sample_dataset_info_dict in sample_datasets_dict.items():
                    result = {}
                    result[ 'transfer_job' ] = self.app.transfer_manager.new( protocol=job.params[ 'protocol' ],
                                                                              host=job.params[ 'host' ],
                                                                              user_name=job.params[ 'user_name' ],
                                                                              password=job.params[ 'password' ],
                                                                              sample_dataset_id=sample_dataset_id,
                                                                              status=sample_dataset_info_dict[ 'status' ],
                                                                              name=sample_dataset_info_dict[ 'name' ],
                                                                              file_path=sample_dataset_info_dict[ 'file_path' ],
                                                                              sample_id=sample_dataset_info_dict[ 'sample_id' ],
                                                                              external_service_id=sample_dataset_info_dict[ 'external_service_id' ],
                                                                              error_msg=sample_dataset_info_dict[ 'error_msg' ],
                                                                              size=sample_dataset_info_dict[ 'size' ] )
                    results.append( result )
            self.app.transfer_manager.run( [ r[ 'transfer_job' ] for r in results ] )
            for result in results:
                transfer_job = result.pop( 'transfer_job' )
                self.create_job( None,
                                 transfer_job_id=transfer_job.id,
                                 result=transfer_job.params,
                                 sample_id=job.params[ 'sample_id' ] )
                # Update the state of the relevant SampleDataset
                new_status = self.app.model.SampleDataset.transfer_status.IN_QUEUE
                self._update_sample_dataset_status( protocol=job.params[ 'protocol' ],
                                                    sample_id=job.params[ 'sample_id' ],
                                                    result_dict=transfer_job.params,
                                                    new_status=new_status,
                                                    error_msg='' )
            job.state = self.app.model.DeferredJob.states.OK
            self.sa_session.add( job )
            self.sa_session.flush()
            # TODO: Error handling: failure executing, or errors returned from the manager 
        if job.params[ 'type' ] == 'finish_transfer':
            protocol = job.params[ 'protocol' ]
            # Update the state of the relevant SampleDataset
            new_status = self.app.model.SampleDataset.transfer_status.ADD_TO_LIBRARY
            if protocol in [ 'http', 'https' ]:
                result_dict = job.params[ 'result' ]
                library_dataset_name = result_dict[ 'name' ]
                extension = result_dict[ 'datatype' ]
            elif protocol in [ 'scp' ]:
                # In this case, job.params will be a dictionary that contains a key named 'result'.  The value
                # of the result key is a dictionary that looks something like:
                # {'sample_dataset_id': '8', 'status': 'Not started', 'protocol': 'scp', 'name': '3.bed', 
                #  'file_path': '/data/library/3.bed', 'host': '127.0.0.1', 'sample_id': 8, 'external_service_id': 2,
                #  'local_path': '/tmp/kjl2Ss4', 'password': 'galaxy', 'user_name': 'gvk', 'error_msg': '', 'size': '8.0K'}
                try:
                    tj = self.sa_session.query( self.app.model.TransferJob ).get( int( job.params['transfer_job_id'] ) )
                    result_dict = tj.params
                    result_dict['local_path'] = tj.path
                except Exception, e:
                    log.error( "Updated transfer result unavailable, using old result.  Error was: %s" % str( e ) )
                    result_dict = job.params[ 'result' ]
                library_dataset_name = result_dict[ 'name' ]
                # Determine the data format (see the relevant TODO item in the manual_data_transfer plugin)..
                extension = sniff.guess_ext( result_dict[ 'local_path' ], sniff_order=self.app.datatypes_registry.sniff_order )
            self._update_sample_dataset_status( protocol=job.params[ 'protocol' ],
                                                sample_id=int( job.params[ 'sample_id' ] ),
                                                result_dict=result_dict,
                                                new_status=new_status,
                                                error_msg='' )
            sample = self.sa_session.query( self.app.model.Sample ).get( int( job.params[ 'sample_id' ] ) )
            ld = self.app.model.LibraryDataset( folder=sample.folder, name=library_dataset_name )
            self.sa_session.add( ld )
            self.sa_session.flush()
            self.app.security_agent.copy_library_permissions( FakeTrans( self.app ), sample.folder, ld )
            ldda = self.app.model.LibraryDatasetDatasetAssociation( name = library_dataset_name,
                                                                    extension = extension,
                                                                    dbkey = '?',
                                                                    library_dataset = ld,
                                                                    create_dataset = True,
                                                                    sa_session = self.sa_session )
            ldda.message = 'Transferred by the Data Transfer Plugin'
            self.sa_session.add( ldda )
            self.sa_session.flush()
            ldda.state = ldda.states.QUEUED # flushed in the set property
            ld.library_dataset_dataset_association_id = ldda.id
            self.sa_session.add( ld )
            self.sa_session.flush()
            try:
                # Move the dataset from its temporary location
                shutil.move( job.transfer_job.path, ldda.file_name )
                ldda.init_meta()
                for name, spec in ldda.metadata.spec.items():
                    if name not in [ 'name', 'info', 'dbkey', 'base_name' ]:
                        if spec.get( 'default' ):
                            setattr( ldda.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                if self.app.config.set_metadata_externally:
                    self.app.datatypes_registry.set_external_metadata_tool.tool_action.execute( self.app.datatypes_registry.set_external_metadata_tool,
                                                                                                FakeTrans( self.app,
                                                                                                           history=sample.history,
                                                                                                           user=sample.request.user ),
                                                                                                incoming = { 'input1':ldda } )
                else:
                    ldda.set_meta()
                    ldda.datatype.after_setting_metadata( ldda )
                ldda.state = ldda.states.OK
                # TODO: not sure if this flush is necessary
                self.sa_session.add( ldda )
                self.sa_session.flush()
            except Exception, e:
                log.exception( 'Failure preparing library dataset for finished transfer job (id: %s) via deferred job (id: %s):' % \
                               ( str( job.transfer_job.id ), str( job.id ) ) )
                ldda.state = ldda.states.ERROR
            if sample.workflow:
                log.debug( "\n\nLogging sample mappings as: %s" % sample.workflow[ 'mappings' ] )
                log.debug( "job.params: %s" % job.params )
                # We have a workflow.  Update all mappings to ldda's, and when the final one is done
                # execute_workflow with either the provided history, or a new one.
                sub_done = True
                rep_done = False
                for k, v in sample.workflow[ 'mappings' ].iteritems():
                    if not 'hda' in v and v[ 'ds_tag' ].startswith( 'hi|' ):
                        sample.workflow[ 'mappings' ][ k ][ 'hda' ] = self.app.security.decode_id( v[ 'ds_tag' ][3:] )
                for key, value in sample.workflow[ 'mappings' ].iteritems():
                    if 'url' in value and value[ 'url' ] == job.params[ 'result' ][ 'url' ]:
                        # DBTODO Make sure all ds| mappings get the URL of the dataset, for linking to later.
                        # If this dataset maps to what we just finished, update the ldda id in the sample.
                        sample.workflow[ 'mappings' ][ key ][ 'ldda' ] = ldda.id
                        rep_done = True
                    # DBTODO replace the hi| mappings with the hda here.  Just rip off the first three chars.
                    elif not 'ldda' in value and not 'hda' in value:
                        # We're not done if some mappings still don't have ldda or hda mappings.
                        sub_done = False
                if sub_done and rep_done:
                    if not sample.history:
                        new_history = self.app.model.History( name="New History From %s" % sample.name, user=sample.request.user )
                        self.sa_session.add( new_history )
                        sample.history = new_history
                        self.sa_session.flush()
                    self._execute_workflow( sample )
                # Check the workflow for substitution done-ness
                self.sa_session.add( sample )
                self.sa_session.flush()
            elif sample.history:
                # We don't have a workflow, but a history was provided.
                # No processing, go ahead and chunk everything in the history.
                if ldda.dataset.state in [ 'new', 'upload', 'queued', 'running', 'empty', 'discarded' ]:
                    log.error("Cannot import dataset '%s' to user history since its state is '%s'.  " % ( ldda.name, ldda.dataset.state ))
                elif ldda.dataset.state in [ 'ok', 'error' ]:
                    ldda.to_history_dataset_association( target_history=sample.history, add_to_history=True )
            # Finished
            job.state = self.app.model.DeferredJob.states.OK
            self.sa_session.add( job )
            self.sa_session.flush()
            # Update the state of the relevant SampleDataset
            new_status = self.app.model.SampleDataset.transfer_status.COMPLETE
            self._update_sample_dataset_status( protocol=job.params[ 'protocol' ],
                                                sample_id=int( job.params[ 'sample_id' ] ),
                                                result_dict=job.params[ 'result' ],
                                                new_status=new_status,
                                                error_msg='' )
            if sample.datasets and not sample.untransferred_dataset_files:
                # Update the state of the sample to the sample's request type's final state.
                new_state = sample.request.type.final_sample_state
                self._update_sample_state( sample.id, new_state )
                # Update the state of the request, if possible
                self._update_request_state( sample.request.id )
    def _missing_params( self, params, required_params ):
        missing_params = filter( lambda x: x not in params, required_params )
        if missing_params:
            log.error( 'Job parameters missing required keys: %s' % ', '.join( missing_params ) )
            return True
        return False
    def _update_sample_dataset_status( self, protocol, sample_id, result_dict, new_status, error_msg=None ):
        # result_dict looks something like:
        # {'url': '127.0.0.1/data/filtered_subreads.fa', 'name': 'Filtered reads'}
        # Check if the new status is a valid transfer status
        valid_statuses = [ v[1] for v in self.app.model.SampleDataset.transfer_status.items() ] 
        # TODO: error checking on valid new_status value
        if protocol in [ 'http', 'https' ]:
            sample_dataset = self.sa_session.query( self.app.model.SampleDataset ) \
                                            .filter( and_( self.app.model.SampleDataset.table.c.sample_id == sample_id,
                                                           self.app.model.SampleDataset.table.c.name == result_dict[ 'name' ],
                                                           self.app.model.SampleDataset.table.c.file_path == result_dict[ 'url' ] ) ) \
                                            .first()
        elif protocol in [ 'scp' ]:
            sample_dataset = self.sa_session.query( self.app.model.SampleDataset ).get( int( result_dict[ 'sample_dataset_id' ] ) )
        sample_dataset.status = new_status
        sample_dataset.error_msg = error_msg
        self.sa_session.add( sample_dataset )
        self.sa_session.flush()
    def _update_sample_state( self, sample_id, new_state, comment=None ):
        sample = self.sa_session.query( self.app.model.Sample ).get( sample_id )
        if comment is None:
            comment = 'Sample state set to %s' % str( new_state )
        event = self.app.model.SampleEvent( sample, new_state, comment )
        self.sa_session.add( event )
        self.sa_session.flush()
    def _update_request_state( self, request_id ):
        request = self.sa_session.query( self.app.model.Request ).get( request_id )
        # Make sure all the samples of the current request have the same state
        common_state = request.samples_have_common_state
        if not common_state:
            # If the current request state is complete and one of its samples moved from
            # the final sample state, then move the request state to In-progress
            if request.is_complete:
                message = "At least 1 sample state moved from the final sample state, so now the request's state is (%s)" % request.states.SUBMITTED
                event = self.app.model.RequestEvent( request, request.states.SUBMITTED, message )
                self.sa_session.add( event )
                self.sa_session.flush()
        else:
            final_state = False
            request_type_state = request.type.final_sample_state
            if common_state.id == request_type_state.id:
                # Since all the samples are in the final state, change the request state to 'Complete'
                comment = "All samples of this sequencing request are in the final sample state (%s). " % request_type_state.name
                state = request.states.COMPLETE
                final_state = True
            else:
                comment = "All samples of this sequencing request are in the (%s) sample state. " % common_state.name
                state = request.states.SUBMITTED
            event = self.app.model.RequestEvent( request, state, comment )
            self.sa_session.add( event )
            self.sa_session.flush()
            # TODO: handle email notification if it is configured to be sent when the samples are in this state.
    def _execute_workflow( self, sample):
        for key, value in sample.workflow['mappings'].iteritems():
            if 'hda' not in value and 'ldda' in value:
                # If HDA is already here, it's an external input, we're not copying anything.
                ldda = self.sa_session.query( self.app.model.LibraryDatasetDatasetAssociation ).get( value['ldda'] )
                if ldda.dataset.state in [ 'new', 'upload', 'queued', 'running', 'empty', 'discarded' ]:
                    log.error("Cannot import dataset '%s' to user history since its state is '%s'.  " % ( ldda.name, ldda.dataset.state ))
                elif ldda.dataset.state in [ 'ok', 'error' ]:
                    hda = ldda.to_history_dataset_association( target_history=sample.history, add_to_history=True )
                    sample.workflow['mappings'][key]['hda'] = hda.id
                    self.sa_session.add( sample )
                    self.sa_session.flush()
        workflow_dict = sample.workflow
        import copy
        new_wf_dict = copy.deepcopy(workflow_dict)
        for key in workflow_dict['mappings']:
            if not isinstance(key, int):
                new_wf_dict['mappings'][int(key)] = workflow_dict['mappings'][key]
        workflow_dict = new_wf_dict
        fk_trans = FakeTrans(self.app, history = sample.history, user=sample.request.user)
        workflow = self.sa_session.query(self.app.model.Workflow).get(workflow_dict['id'])
        if not workflow:
            log.error("Workflow mapping failure.")
            return
        if len( workflow.steps ) == 0:
            log.error( "Workflow cannot be run because it does not have any steps" )
            return
        if workflow.has_cycles:
            log.error( "Workflow cannot be run because it contains cycles" )
            return
        if workflow.has_errors:
            log.error( "Workflow cannot be run because of validation errors in some steps" )
            return
        # Build the state for each step
        errors = {}
        has_upgrade_messages = False
        has_errors = False
        # Build a fake dictionary prior to execution.
        # Prepare each step
        for step in workflow.steps:
            step.upgrade_messages = {}
            # Contruct modules
            if step.type == 'tool' or step.type is None:
                # Restore the tool state for the step
                step.module = module_factory.from_workflow_step( fk_trans, step )
                # Fix any missing parameters
                step.upgrade_messages = step.module.check_and_update_state()
                if step.upgrade_messages:
                    has_upgrade_messages = True
                # Any connected input needs to have value DummyDataset (these
                # are not persisted so we need to do it every time)
                step.module.add_dummy_datasets( connections=step.input_connections )
                # Store state with the step
                step.state = step.module.state
                # Error dict
                if step.tool_errors:
                    has_errors = True
                    errors[step.id] = step.tool_errors
            else:
                ## Non-tool specific stuff?
                step.module = module_factory.from_workflow_step( fk_trans, step )
                step.state = step.module.get_runtime_state()
            # Connections by input name
            step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )
        for step in workflow.steps:
            step.upgrade_messages = {}
            # Connections by input name
            step.input_connections_by_name = \
                dict( ( conn.input_name, conn ) for conn in step.input_connections )
            # Extract just the arguments for this step by prefix
            step_errors = None
            if step.type == 'tool' or step.type is None:
                module = module_factory.from_workflow_step( fk_trans, step )
                # Fix any missing parameters
                step.upgrade_messages = module.check_and_update_state()
                if step.upgrade_messages:
                    has_upgrade_messages = True
                # Any connected input needs to have value DummyDataset (these
                # are not persisted so we need to do it every time)
                module.add_dummy_datasets( connections=step.input_connections )
                # Get the tool
                tool = module.tool
                # Get the state
                step.state = state = module.state
                # Get old errors
                old_errors = state.inputs.pop( "__errors__", {} )
            if step_errors:
                errors[step.id] = state.inputs["__errors__"] = step_errors
        # Run each step, connecting outputs to inputs
        workflow_invocation = self.app.model.WorkflowInvocation()
        workflow_invocation.workflow = workflow
        outputs = odict()
        for i, step in enumerate( workflow.steps ):
            job = None
            if step.type == 'tool' or step.type is None:
                tool = self.app.toolbox.tools_by_id[ step.tool_id ]
                def callback( input, value, prefixed_name, prefixed_label ):
                    if isinstance( input, DataToolParameter ):
                        if prefixed_name in step.input_connections_by_name:
                            conn = step.input_connections_by_name[ prefixed_name ]
                            return outputs[ conn.output_step.id ][ conn.output_name ]
                visit_input_values( tool.inputs, step.state.inputs, callback )
                job, out_data = tool.execute( fk_trans, step.state.inputs, history=sample.history)
                outputs[ step.id ] = out_data
                for pja in step.post_job_actions:
                    if pja.action_type in ActionBox.immediate_actions:
                        ActionBox.execute(self.app, self.sa_session, pja, job, replacement_dict)
                    else:
                        job.add_post_job_action(pja)
            else:
                job, out_data = step.module.execute( fk_trans, step.state)
                outputs[ step.id ] = out_data
                if step.id in workflow_dict['mappings']:
                    data = self.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( workflow_dict['mappings'][str(step.id)]['hda'] )
                    outputs[ step.id ]['output'] = data
            workflow_invocation_step = self.app.model.WorkflowInvocationStep()
            workflow_invocation_step.workflow_invocation = workflow_invocation
            workflow_invocation_step.workflow_step = step
            workflow_invocation_step.job = job
        self.sa_session.add( workflow_invocation )
        self.sa_session.flush()
