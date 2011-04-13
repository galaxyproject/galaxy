"""
Generic module for managing manual data transfer jobs using Galaxy's built-in file browser.
This module can be used by various external services that are configured to transfer data manually.
"""
import logging, urllib2, re, shutil
from data_transfer import *

log = logging.getLogger( __name__ )

__all__ = [ 'ManualDataTransferPlugin' ]

class ManualDataTransferPlugin( DataTransfer ):
    def __init__( self, app ):
        super( ManualDataTransferPlugin, self ).__init__( app )
    def create_job( self, trans, **kwd ):
        if 'sample' in kwd and 'sample_datasets' in kwd and 'external_service' in kwd and 'external_service_type' in kwd:
            sample = kwd[ 'sample' ]
            sample_datasets = kwd[ 'sample_datasets' ]
            external_service = kwd[ 'external_service' ]
            external_service_type = kwd[ 'external_service_type' ]
            # TODO: is there a better way to store the protocol?
            protocol = external_service_type.data_transfer.keys()[0]
            host = external_service.form_values.content[ 'host' ]
            user_name = external_service.form_values.content[ 'user_name' ]
            password = external_service.form_values.content[ 'password' ]
            # TODO: In the future, we may want to implement a way for the user to associate a selected file with one of
            # the run outputs configured in the <run_details><results> section of the external service config file.  The 
            # following was a first pass at implementing something (the datatype was included in the sample_dataset_dict),
            # but without a way for the user to associate stuff it's useless.  However, allowing the user this ability may
            # open a can of worms, so maybe we shouldn't do it???
            #
            #for run_result_file_name, run_result_file_datatype in external_service_type.run_details[ 'results' ].items():
            #     # external_service_type.run_details[ 'results' ] looks something like: {'dataset1_name': 'dataset1_datatype'}
            #     if run_result_file_datatype in external_service.form_values.content:
            #         datatype = external_service.form_values.content[ run_result_file_datatype ]
            #
            # When the transfer is automatic (the process used in the SMRT Portal plugin), the datasets and datatypes
            # can be matched up to those configured in the <run_details><results> settings in the external service type config
            # (e.g., pacific_biosciences_smrt_portal.xml).  However, that's a bit trickier here since the user is manually
            # selecting files for transfer.
            sample_datasets_dict = {}
            for sample_dataset in sample_datasets:
                sample_dataset_id = sample_dataset.id
                sample_dataset_dict = dict( sample_id = sample_dataset.sample.id,
                                            name = sample_dataset.name,
                                            file_path = sample_dataset.file_path,
                                            status = sample_dataset.status,
                                            error_msg = sample_dataset.error_msg,
                                            size = sample_dataset.size,
                                            external_service_id = sample_dataset.external_service.id )
                sample_datasets_dict[ sample_dataset_id ] = sample_dataset_dict
            params = { 'type' : 'init_transfer',
                       'sample_id' : sample.id,
                       'sample_datasets_dict' : sample_datasets_dict,
                       'protocol' : protocol,
                       'host' : host,
                       'user_name' : user_name,
                       'password' : password }
        elif 'transfer_job_id' in kwd:
            params = { 'type' : 'finish_transfer',
                       'protocol' : kwd[ 'result' ][ 'protocol' ],
                       'sample_id' : kwd[ 'sample_id' ],
                       'result' : kwd[ 'result' ],
                       'transfer_job_id' : kwd[ 'transfer_job_id' ] }
        else:
            log.error( 'No job was created because kwd does not include "samples" and "sample_datasets" or "transfer_job_id".' )
            return
        deferred_job = self.app.model.DeferredJob( state=self.app.model.DeferredJob.states.NEW,
                                                   plugin='ManualDataTransferPlugin',
                                                   params=params )
        self.sa_session.add( deferred_job )
        self.sa_session.flush()
        log.debug( 'Created a deferred job in the ManualDataTransferPlugin of type: %s' % params[ 'type' ] )
        # TODO: error reporting to caller (if possible?)
    def check_job( self, job ):
        if self._missing_params( job.params, [ 'type' ] ):
            return self.job_states.INVALID
        if job.params[ 'type' ] == 'init_transfer':
            if job.params[ 'protocol' ] in [ 'http', 'https' ]:
                raise Exception( "Manual data transfer is not yet supported for http(s)." )
            elif job.params[ 'protocol' ] == 'scp':
                if self._missing_params( job.params, [ 'protocol', 'host', 'user_name', 'password', 'sample_id', 'sample_datasets_dict' ] ):
                    return self.job_states.INVALID
                # TODO: what kind of checks do we need here?
                return self.job_states.READY
            return self.job_states.WAIT
        if job.params[ 'type' ] == 'finish_transfer':
            if self._missing_params( job.params, [ 'transfer_job_id' ] ):
                return self.job_states.INVALID
            # Get the TransferJob object and add it to the DeferredJob so we only look it up once.
            if not hasattr( job, 'transfer_job' ):
                job.transfer_job = self.sa_session.query( self.app.model.TransferJob ).get( int( job.params[ 'transfer_job_id' ] ) )
            state = self.app.transfer_manager.get_state( job.transfer_job )
            if not state:
                log.error( 'No state for transfer job id: %s' % job.transfer_job.id )
                return self.job_states.WAIT
            if state[ 'state' ] in self.app.model.TransferJob.terminal_states:
                return self.job_states.READY
            log.debug( "Checked on finish transfer job %s, not done yet." % job.id )
            return self.job_states.WAIT
        else:
            log.error( 'Unknown job type for ManualDataTransferPlugin: %s' % str( job.params[ 'type' ] ) )
            return self.job_states.INVALID
