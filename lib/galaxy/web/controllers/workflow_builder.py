from galaxy.web.base.controller import *

from galaxy.tools.parameters import DataToolParameter
from galaxy.tools import DefaultToolState
from galaxy.tools.grouping import Repeat, Conditional
from galaxy.datatypes.data import Data
from galaxy.workflow import Workflow, WorkflowStep

from galaxy.util.odict import odict

import simplejson

class WorkflowBuilder( BaseController ):
    
    def __get_job_dict( self, trans ):
        """
        Return a dictionary of Job -> [ Dataset ] mappings, for all finished
        active Datasets in the current history and the jobs that created them.
        """
        history = trans.get_history()
        # Get the jobs that created the datasets
        warnings = set()
        jobs = odict()
        for dataset in history.active_datasets:
            # FIXME: Create "Dataset.is_finished"
            if dataset.state in ( 'new', 'running', 'queued' ):
                warnings.add( "Some datasets still queued or running were ignored" )
                continue
            for assoc in dataset.creating_job_associations:
                job = assoc.job
                if job in jobs:
                    jobs[ job ].append( ( assoc.name, dataset ) )
                else:
                    jobs[ job ] = [ ( assoc.name, dataset ) ]
        return jobs, warnings    
    
    def __cleanup_param_values( self, inputs, values ):
        """
        Remove 'Data' values from `param_values` but track the associations
        """
        associations = []
        names_to_clean = []
        # dbkey is pushed in by the framework
        if 'dbkey' in values:
            del values['dbkey']
        root_values = values
        # Cleanup all data inputs
        def cleanup( prefix, inputs, values ):
            for key, input in inputs.items():
                if isinstance( input, DataToolParameter ):
                    tmp = values[key]
                    values[key] = None
                    # HACK: Nested associations are not yet working, but we
                    #       still need to clean them up so we can serialize
                    if not( prefix ):
                        associations.append( ( tmp.hid, prefix + key ) )
                    # Cleanup the other deprecated crap associated with datasets
                    # as well. Worse, for nested datasets all the metadata is
                    # being pushed into the root. FIXME: MUST REMOVE SOON
                    key = prefix + key + "_"
                    for k in root_values.keys():
                        if k.startswith( key ):
                            del root_values[k]            
                elif isinstance( input, Repeat ):
                    group_values = values[key]
                    for i in range( len( group_values ) ):
                        prefix = "%s_%d|" % ( key, i )
                        cleanup( prefix, input.inputs, group_values[i] )
                elif isinstance( input, Conditional ):
                    group_values = values[input.name]
                    current_case = group_values['__current_case__']
                    prefix = "%s|" % ( key )
                    cleanup( prefix, input.cases[current_case].inputs, group_values )
        cleanup( "", inputs, values )
        return associations
    
    @web.expose
    def workflow_from_current_history( self, trans, job_ids=None, workflow_name=None ):
        if trans.request.method == 'POST':
            return self.workflow_from_current_history_post( trans, job_ids, workflow_name )
        user = trans.get_user()
        if not user:
            return trans.show_error_message( "Must be logged in to create workflows" )
        jobs, warnings = self.__get_job_dict( trans )
        # Render
        return trans.fill_template(
                    "workflow_builder/workflow_from_current_history.mako", 
                    jobs=jobs,
                    warnings=warnings )
    
    def workflow_from_current_history_post( self, trans, job_ids, workflow_name ):
        user = trans.get_user()
        if not user:
            return trans.show_error_message( "Must be logged in to create workflows" )
        # Ensure a list
        if type( job_ids ) == str:
            job_ids = [ job_ids ]
        job_ids = [ int( id ) for id in job_ids ]
        # Find each job, for security we (implicately) check that they are
        # associated witha job in the current history. 
        jobs, warnings = self.__get_job_dict( trans )
        # Create a mapping from hid to ( job_id, output_name )
        hid_to_output_pair = {}
        for job, datasets in jobs.iteritems():
            for assoc_name, data in datasets:
                hid_to_output_pair[ data.hid ] = ( job.id, assoc_name )
        # Mapping from job ids to workflow step ids (0, 1, 2, ...)
        job_id_to_step_id = dict( ( job_id, i ) for ( i, job_id ) in enumerate( job_ids ) )
        # Workflow to populate
        workflow = Workflow()
        # Back-translate each job
        jobs_by_id = dict( ( job.id, job ) for job in jobs.keys() )
        for step_id, job_id in enumerate( job_ids ):
            assert job_id in jobs_by_id, "Attempt to create workflow with job not connected to current history"
            job = jobs_by_id[ job_id ]
            tool = trans.app.toolbox.tools_by_id[ job.tool_id ]
            param_values = job.get_param_values( trans.app )
            associations = self.__cleanup_param_values( tool.inputs, param_values )
            step = WorkflowStep()
            step.id = step_id
            step.tool_id = job.tool_id
            step.tool_inputs = param_values
            for other_hid, input_name in associations:
                other_job_id, other_name = hid_to_output_pair[ other_hid ]
                # Only create association if the associated output dataset
                # is being included in this workflow
                if other_job_id in job_id_to_step_id:
                    step.input_connections[input_name] = ( job_id_to_step_id[ other_job_id ], other_name )
                else:
                    step.input_connections[input_name] = None
            workflow.steps[ step_id ] = step
        # Try to order the nodes
        workflow.order_nodes()
        # And let's try to set up some reasonable locations
        levorder = workflow.order_nodes_levels()
        base_pos = 2510
        for i, steps_at_level in enumerate( levorder ):
            for j, step_id in enumerate( steps_at_level ):
                step = workflow.steps[step_id]
                step.position = dict( top = ( base_pos + 120 * j ),
                                      left = ( base_pos + 220 * i ) )
        # Store it
        stored = model.StoredWorkflow.get_by( user = user, name = workflow_name )
        if stored is None:
            stored = model.StoredWorkflow()
            stored.user = user
            stored.name = workflow_name
        stored.encoded_value = simplejson.dumps( workflow.to_simple() )
        stored.flush()
        # 
        return trans.show_ok_message( "Workflow '%s' created.<br/><a target='_top' href='%s'>Click to load in workflow editor</a>"
            % ( workflow_name, web.url_for( controller='workflow_editor', action=None, workflow_name=workflow_name ) ) )
            
            
            
        
        
        