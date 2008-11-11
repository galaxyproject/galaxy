#!/usr/bin/env python
"""
Fetch jobs using gops_intersect, gops_merge, gops_subtract, gops_complement, gops_coverage wherein the second dataset doesn't have chr, start and end in standard columns 1,2 and 3.
"""

from galaxy import eggs
import sys, os, ConfigParser
import galaxy.app
#from galaxy.util.bunch import Bunch

import galaxy.model.mapping
import pkg_resources
        
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy as sa
#from sqlalchemy.orm import *

assert sys.version_info[:2] >= ( 2, 4 )

class TestApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, database_connection=None, file_path=None ):
        print >> sys.stderr, "python path is: " + ", ".join( sys.path )
        if database_connection is None:
            raise Exception( "CleanupDatasetsApplication requires a database_connection value" )
        if file_path is None:
            raise Exception( "CleanupDatasetsApplication requires a file_path value" )
        self.database_connection = database_connection
        self.file_path = file_path
        # Setup the database engine and ORM
        self.model = galaxy.model.mapping.init( self.file_path, self.database_connection, engine_options={}, create_tables=False )

def main():
    ini_file = sys.argv[1]
    conf_parser = ConfigParser.ConfigParser( {'here':os.getcwd()} )
    conf_parser.read( ini_file )
    configuration = {}
    for key, value in conf_parser.items( "app:main" ):
        configuration[key] = value
    database_connection = configuration['database_connection']
    file_path = configuration['file_path']
    app = TestApplication( database_connection=database_connection, file_path=file_path )
    jobs = {}
    for job in app.model.Job.filter(
        sa.and_(
             app.model.Job.table.c.create_time.between('2008-05-23','2008-11-29'),
             app.model.Job.table.c.state == 'ok',
             sa.or_(app.model.Job.table.c.tool_id == 'gops_intersect_1',
                 app.model.Job.table.c.tool_id == 'gops_subtract_1',
                 app.model.Job.table.c.tool_id == 'gops_merge_1',
                 app.model.Job.table.c.tool_id == 'gops_coverage_1',
                 app.model.Job.table.c.tool_id == 'gops_complement_1',
                ),
             sa.not_(app.model.Job.table.c.command_line.like('%-2 1,2,3%'))
            )).all():
	for od in job.output_datasets:
            ds = app.model.Dataset.get(od.dataset_id)
            if not ds.deleted:
                hda = app.model.HistoryDatasetAssociation.filter(app.model.HistoryDatasetAssociation.table.c.dataset_id == ds.id)[0]
                hist = app.model.History.get(hda.history_id)
                if hist.user_id:
                    user = app.model.User.get(hist.user_id)
                    jobs[job.id] = {}
                    jobs[job.id]['dataset_id'] = ds.id
                    jobs[job.id]['dataset_create_time'] = ds.create_time 
                    jobs[job.id]['dataset_name'] = hda.name 
                    jobs[job.id]['hda_id'] = hda.id 
                    jobs[job.id]['hist_id'] = hist.id 
                    jobs[job.id]['hist_name'] = hist.name 
                    jobs[job.id]['hist_modified_time'] = hist.update_time
		    jobs[job.id]['user_email'] = user.email 
    
    print "Number of Incorrect Jobs: %d\n"%(len(jobs))
    print "#job_id\tdataset_id\tdataset_create_time\thda_id\thistory_id\thistory_name\thistory_modified_time\tuser_email"
    for jid in jobs:
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" %(jid,jobs[jid]['dataset_id'],jobs[jid]['dataset_create_time'],jobs[jid]['dataset_name'],jobs[jid]['hda_id'],jobs[jid]['hist_id'],jobs[jid]['hist_name'],jobs[jid]['hist_modified_time'],jobs[jid]['user_email'] )
    sys.exit(0)

if __name__ == "__main__":
    main()
