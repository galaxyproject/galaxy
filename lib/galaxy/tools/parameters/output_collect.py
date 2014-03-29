""" Code allowing tools to define extra files associated with an output datset.
"""
import os
import glob
import json


from galaxy import jobs


def collect_primary_datatasets( tool, output, job_working_directory ):
    app = tool.app
    sa_session = tool.sa_session
    new_primary_datasets = {}
    try:
        json_file = open( os.path.join( job_working_directory, jobs.TOOL_PROVIDED_JOB_METADATA_FILE ), 'r' )
        for line in json_file:
            line = json.loads( line )
            if line.get( 'type' ) == 'new_primary_dataset':
                new_primary_datasets[ os.path.split( line.get( 'filename' ) )[-1] ] = line
    except Exception:
        # This should not be considered an error or warning condition, this file is optional
        pass
    # Loop through output file names, looking for generated primary
    # datasets in form of:
    #     'primary_associatedWithDatasetID_designation_visibility_extension(_DBKEY)'
    primary_datasets = {}
    for name, outdata in output.items():
        filenames = []
        if 'new_file_path' in app.config.collect_outputs_from:
            filenames.extend( glob.glob(os.path.join(app.config.new_file_path, "primary_%i_*" % outdata.id) ) )
        if 'job_working_directory' in app.config.collect_outputs_from:
            filenames.extend( glob.glob(os.path.join(job_working_directory, "primary_%i_*" % outdata.id) ) )
        for filename in filenames:
            if not name in primary_datasets:
                primary_datasets[name] = {}
            fields = os.path.basename(filename).split("_")
            fields.pop(0)
            parent_id = int(fields.pop(0))
            designation = fields.pop(0)
            visible = fields.pop(0).lower()
            if visible == "visible":
                visible = True
            else:
                visible = False
            ext = fields.pop(0).lower()
            dbkey = outdata.dbkey
            if fields:
                dbkey = fields[ 0 ]
            # Create new primary dataset
            primary_data = app.model.HistoryDatasetAssociation( extension=ext,
                                                                designation=designation,
                                                                visible=visible,
                                                                dbkey=dbkey,
                                                                create_dataset=True,
                                                                sa_session=sa_session )
            app.security_agent.copy_dataset_permissions( outdata.dataset, primary_data.dataset )
            sa_session.add( primary_data )
            sa_session.flush()
            # Move data from temp location to dataset location
            app.object_store.update_from_file(primary_data.dataset, file_name=filename, create=True)
            primary_data.set_size()
            primary_data.name = "%s (%s)" % ( outdata.name, designation )
            primary_data.info = outdata.info
            primary_data.init_meta( copy_from=outdata )
            primary_data.dbkey = dbkey
            # Associate new dataset with job
            job = None
            for assoc in outdata.creating_job_associations:
                job = assoc.job
                break
            if job:
                assoc = app.model.JobToOutputDatasetAssociation( '__new_primary_file_%s|%s__' % ( name, designation ), primary_data )
                assoc.job = job
                sa_session.add( assoc )
                sa_session.flush()
            primary_data.state = outdata.state
            #add tool/metadata provided information
            new_primary_datasets_attributes = new_primary_datasets.get( os.path.split( filename )[-1] )
            if new_primary_datasets_attributes:
                dataset_att_by_name = dict( ext='extension' )
                for att_set in [ 'name', 'info', 'ext', 'dbkey' ]:
                    dataset_att_name = dataset_att_by_name.get( att_set, att_set )
                    setattr( primary_data, dataset_att_name, new_primary_datasets_attributes.get( att_set, getattr( primary_data, dataset_att_name ) ) )
            primary_data.set_meta()
            primary_data.set_peek()
            sa_session.add( primary_data )
            sa_session.flush()
            outdata.history.add_dataset( primary_data )
            # Add dataset to return dict
            primary_datasets[name][designation] = primary_data
            # Need to update all associated output hdas, i.e. history was
            # shared with job running
            for dataset in outdata.dataset.history_associations:
                if outdata == dataset:
                    continue
                new_data = primary_data.copy()
                dataset.history.add_dataset( new_data )
                sa_session.add( new_data )
                sa_session.flush()
    return primary_datasets
