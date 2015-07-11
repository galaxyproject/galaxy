"""
Module for managing jobs in Pacific Bioscience's SMRT Portal and automatically transferring files
produced by SMRT Portal.
"""
import logging, urllib2, re, shutil
from string import Template
from galaxy.util import json

from data_transfer import *

log = logging.getLogger( __name__ )

__all__ = [ 'SMRTPortalPlugin' ]

class SMRTPortalPlugin( DataTransfer ):
    api_path = '/smrtportal/api'
    def __init__( self, app ):
        super( SMRTPortalPlugin, self ).__init__( app )
    def create_job( self, trans, **kwd ):
        if 'secondary_analysis_job_id' in kwd:
            sample = kwd[ 'sample' ]
            smrt_job_id = kwd[ 'secondary_analysis_job_id' ]
            external_service = sample.request.type.get_external_service( 'pacific_biosciences_smrt_portal' )
            external_service.load_data_transfer_settings( trans )
            http_configs = external_service.data_transfer[ trans.model.ExternalService.data_transfer_protocol.HTTP ]
            if not http_configs[ 'automatic_transfer' ]:
                raise Exception( "Manual data transfer using http is not yet supported." )
            smrt_host = external_service.form_values.content[ 'host' ]
            external_service_type = external_service.get_external_service_type( trans )
            # TODO: is there a better way to store the protocol?
            # external_service_type.data_transfer looks somethng like
            # {'http': <galaxy.sample_tracking.data_transfer.HttpDataTransferFactory object at 0x1064239d0>}
            protocol = external_service_type.data_transfer.keys()[0]
            results = {}
            for k, v in external_service.form_values.content.items():
                match = self.dataset_name_re.match( k ) or self.dataset_datatype_re.match( k )
                if match:
                    id, field = match.groups()
                    if id in results:
                        results[ id ][ field ] = v
                    else:
                        results[ id ] = { field : v }
            for id, attrs in results.items():
                url_template = external_service_type.run_details[ 'results_urls' ].get( id + '_name' )
                url = Template( url_template ).substitute( host = smrt_host, secondary_analysis_job_id = kwd[ 'secondary_analysis_job_id' ] )
                results[ id ][ 'url' ] = url
                if sample.workflow:
                    # DBTODO Make sure all ds| mappings get the URL of the dataset, for linking to later.
                    for k, v in sample.workflow[ 'mappings' ].iteritems():
                        if 'ds|%s' % id in v.values():
                            sample.workflow['mappings'][k]['url'] = url
            self.sa_session.add(sample)
            self.sa_session.flush()
            params = { 'type' : 'init_transfer',
                       'protocol' : protocol,
                       'sample_id' : sample.id,
                       'results' : results,
                       'smrt_host' : smrt_host,
                       'smrt_job_id' : smrt_job_id }
            # Create a new SampleDataset for each run result dataset
            self._associate_untransferred_datasets_with_sample( sample, external_service, results )
        elif 'transfer_job_id' in kwd:
            params = { 'type' : 'finish_transfer',
                       'protocol' : kwd[ 'result' ][ 'protocol' ],
                       'sample_id' : kwd[ 'sample_id' ],
                       'result' : kwd[ 'result' ],
                       'transfer_job_id' : kwd[ 'transfer_job_id' ] }
        else:
            log.error( 'No job was created because kwd does not include "secondary_analysis_job_id" or "transfer_job_id".' )
            return
        deferred_job = self.app.model.DeferredJob( state=self.app.model.DeferredJob.states.NEW,
                                                   plugin='SMRTPortalPlugin',
                                                   params=params )
        self.sa_session.add( deferred_job )
        self.sa_session.flush()
        log.debug( 'Created a deferred job in the SMRTPortalPlugin of type: %s' % params[ 'type' ] )
        # TODO: error reporting to caller (if possible?)
    def check_job( self, job ):
        if self._missing_params( job.params, [ 'type' ] ):
            return self.job_states.INVALID
        if job.params[ 'type' ] == 'init_transfer':
            if self._missing_params( job.params, [ 'smrt_host', 'smrt_job_id' ] ):
                return self.job_states.INVALID
            url = 'http://' + job.params[ 'smrt_host' ] + self.api_path + '/Jobs/' + job.params[ 'smrt_job_id' ] + '/Status'
            r = urllib2.urlopen( url )
            status = json.loads( r.read() )
            # TODO: error handling: unexpected json or bad response, bad url, etc.
            if status[ 'Code' ] == 'Completed':
                log.debug( "SMRT Portal job '%s' is Completed.  Initiating transfer." % job.params[ 'smrt_job_id' ] )
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
            log.error( 'Unknown job type for SMRTPortalPlugin: %s' % str( job.params[ 'type' ] ) )
            return self.job_states.INVALID
    def _associate_untransferred_datasets_with_sample( self, sample, external_service, results_dict ):
        # results_dict looks something like:
        # {'dataset2': {'datatype': 'fasta', 'url': '127.0.0.1:8080/data/filtered_subreads.fa', 'name': 'Filtered reads'} }
        for key, val in results_dict.items():
            file_path = val[ 'url' ]
            status = self.app.model.SampleDataset.transfer_status.NOT_STARTED
            name = val[ 'name' ]
            size = 'unknown'
            sample_dataset = self.app.model.SampleDataset( sample=sample,
                                                           file_path=file_path,
                                                           status=status,
                                                           name=name,
                                                           error_msg='',
                                                           size=size,
                                                           external_service=external_service )
            self.sa_session.add( sample_dataset )
            self.sa_session.flush()
