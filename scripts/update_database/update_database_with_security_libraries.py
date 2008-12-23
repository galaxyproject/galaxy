#!/usr/bin/env python
#Dan Blankenberg
"""
BACKUP YOUR DATABASE BEFORE RUNNING THIS SCRIPT!

This script has been tested with Postgres, SQLite, and MySQL databases.

This script updates a pre-security/library database with necessary schema changes and sets default roles/permissions
for users and their histories and datasets.  It will reset permissions on histories and datasets if they are already set.
Due to limitations of SQLite this script is unable to add foreign keys to existing SQLite tables (foreign keys are
ignored by SQLite anyway).

REMEMBER TO BACKUP YOUR DATABASE BEFORE RUNNING THIS SCRIPT!
"""

import sys, os, ConfigParser, tempfile
import galaxy.app, galaxy.model
import sqlalchemy
from galaxy.model.orm import *

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    def print_warning( warning_text ):
        print "\nWarning: %s\n" % ( warning_text )
    
    print
    print "The purpose of this script is to update an existing Galaxy database that does not have Library or Security settings to a version that does."
    print
    print "This script will do the following:"
    print "1) Create new tables that do not exist in a pre-security/library database"
    print "2) Alter existing tables as necessary ( add new columns, indexes, etc )"
    print "3) Create a private role for each user"
    print "4) Set default permissions for each user ( set as 'manage permissions' and associated with the user's private role )"
    print "5) Set default permissions for each user's history that has not been purged ( set as 'manage permissions' and associated with the user's private role )"
    print "6) Set permissions on all appropriate datasets ( in each user's history ) that have not been purged ( set as 'manage permissions' and associated with the user's private role )"
    print
    print "*** It is critically important to backup your database before you continue. ***"
    print
    print "If you have backed up your database and would like to run this script, enter 'yes'."
    print
    should_continue = raw_input("enter 'yes' to continue>")
    if should_continue.lower() != "yes":
        print "Script aborted by user."
        sys.exit(0)
    
    # Load Configuration from file
    ini_file = sys.argv.pop(1)
    conf_parser = ConfigParser.ConfigParser({'here':os.getcwd()})
    conf_parser.read(ini_file)
    configuration = {}
    for key, value in conf_parser.items("app:main"): configuration[key] = value
    
    # If we don't load the tools, the app will startup much faster
    empty_xml = tempfile.NamedTemporaryFile()
    empty_xml.write( "<root/>" )
    empty_xml.flush()
    configuration['tool_config_file'] = empty_xml.name
    # No need to load job runners
    configuration['enable_job_running'] = False
    
    print
    print "Loading app, with database_create_tables=False, to add Columns to existing tables"
    print
    # Set database_create_tables to False, then load the app
    configuration['database_create_tables'] = False
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    
    # Try to guess the database type that we have, in order to execute the proper raw SQL commands
    if app.config.database_connection:
        dialect = galaxy.model.mapping.guess_dialect_for_url( app.config.database_connection )
    else:
        # default dialect is sqlite
        dialect = "sqlite"
    
    # Now we alter existing tables, unfortunately SQLAlchemy does not support this.
    # SQLite is very lacking in its implementation of the ALTER command, we'll do what we can...
    # We cannot check with SA to see if new columns exist, so we will try and except (trying to 
    # access the table with our current SA Metadata which references missing columns will throw 
    # exceptions )

    # galaxy_user table - must be altered differently depending on if we are using sqlite or not
    if dialect == "sqlite":
        try:
            # 'true' and 'false' doesn't work properly in SQLite --> both are always True (is sqlite actually 
            # storing a string here, which is always true when not empty?)
            app.model.session.execute( "ALTER TABLE 'galaxy_user' ADD COLUMN 'deleted' BOOLEAN default 0" )
        except sqlalchemy.exceptions.OperationalError, e:
            print_warning( "adding column 'deleted' failed: %s" % ( e ) )
        try:
            app.model.session.execute( "ALTER TABLE 'galaxy_user' ADD COLUMN 'purged' BOOLEAN default 0" )
        except sqlalchemy.exceptions.OperationalError, e:
            print_warning( "adding column 'purged' failed: %s" % ( e ) )
    else:
        try:
            app.model.session.execute( "ALTER TABLE galaxy_user ADD COLUMN deleted BOOLEAN default false" )
        except ( sqlalchemy.exceptions.ProgrammingError, sqlalchemy.exceptions.OperationalError ), e:
            # Postgres and MySQL raise different Exceptions for this same failure.
            print_warning( "adding column 'deleted' failed: %s" % ( e ) )
        try:
            app.model.session.execute( "ALTER TABLE galaxy_user ADD COLUMN purged BOOLEAN default false" )
        except ( sqlalchemy.exceptions.ProgrammingError, sqlalchemy.exceptions.OperationalError ), e:
            print_warning( "adding column 'purged' failed: %s" % ( e ) )
    
    # history_dataset_association table - these alters are the same, regardless if we are using sqlite
    try:
        app.model.session.execute( "ALTER TABLE history_dataset_association ADD COLUMN copied_from_library_folder_dataset_association_id INTEGER" )
    except ( sqlalchemy.exceptions.ProgrammingError, sqlalchemy.exceptions.OperationalError ), e:
        print_warning( "adding column 'copied_from_library_folder_dataset_association_id' failed: %s" % ( e ) )
    
    # metadata_file table
    try:
        app.model.session.execute( "ALTER TABLE metadata_file ADD COLUMN lda_id INTEGER" )
    except ( sqlalchemy.exceptions.ProgrammingError, sqlalchemy.exceptions.OperationalError ), e:
        print_warning( "adding column 'lda_id' failed: %s" % ( e ) )
    
    
    # Create indexes for new columns in the galaxy_user and metadata_file tables
    try:
        i = sqlalchemy.Index( 'ix_galaxy_user_deleted', app.model.User.table.c.deleted )
        i.create()
    except Exception, e:
        print_warning( "Adding index failed: %s" % ( e ) )
    try:
        i = sqlalchemy.Index( 'ix_galaxy_user_purged', app.model.User.table.c.purged )
        i.create()
    except Exception, e:
        print_warning( "Adding index failed: %s" % ( e ) )
    try:
        i = sqlalchemy.Index( 'ix_metadata_file_lda_id', app.model.MetadataFile.table.c.lda_id )
        i.create()
    except Exception, e:
        print_warning( "Adding index failed: %s" % ( e ) )
    
    
    # Shutdown the app
    app.shutdown()
    del app
    print
    print "Columns added to tables, restarting app, with database_create_tables=True"
    
    # Restart the app, this time with create_tables == True
    configuration['database_create_tables'] = True
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    
    # Add foreign key constraints as necessary for new columns added above
    print "Adding foreign key constraints"
    if dialect != "sqlite":
        try:
            app.model.session.execute( "ALTER TABLE history_dataset_association ADD FOREIGN KEY (copied_from_library_folder_dataset_association_id) REFERENCES library_folder_dataset_association(id)" )
        except Exception, e:
            print_warning( "Adding foreign key constraint to table has failed for an unknown reason: %s" % ( e ) )
        try:
            app.model.session.execute( "ALTER TABLE metadata_file ADD FOREIGN KEY (lda_id) REFERENCES library_folder_dataset_association(id)" )
        except Exception, e:
            print_warning( "Adding foreign key constraint to table has failed for an unknown reason: %s" % ( e ) )

    else:
        # SQLite ignores ( but parses on initial table creation ) foreign key constraints anyway
        # See: http://www.sqlite.org/omitted.html (there is some way to set up behavior using triggers)
        print_warning( "Adding foreign key constraints to table is not supported in SQLite." )
    
    print "creating private roles and setting defaults for existing users and their histories and datasets"
    security_agent = app.security_agent
    # For each user:
    # 1. make sure they have a private role
    # 2. set DefaultUserPermissions
    # 3. set DefaultHisstoryPermissions on existing histories 
    # 4. set ActionDatasetRoleAssociations on each history's activatable_datasets
    default_user_action = security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
    
    for user in app.model.User.query().all():
        print "################"
        print "Setting up user %s." % user.email
        private_role = security_agent.get_private_user_role( user )
        if not private_role:
            security_agent.create_private_user_role( user )
            print "Created private role for %s" % user.email
        else:
            print_warning( "%s already has a private role, re-setting defaults anyway" % user.email )
        print "Setting DefaultUserPermissions for user %s" % user.email
        # Delete all of the current default permissions for the user
        for dup in user.default_permissions:
            dup.delete()
            dup.flush()
        # Add the new default permissions for the user
        dup = app.model.DefaultUserPermissions( user, default_user_action, private_role )
        dup.flush()
        # Set DefaultHistoryPermissions on all of the user's active histories and associated datasets
        histories = app.model.History.filter( and_( app.model.History.table.c.user_id==user.id,
                                                    app.model.History.table.purged==False ) ) \
                                     .options( eagerload( 'activatable_datasets' ) ).all()
        print "Setting DefaultHistoryPermissions for %d un-purged histories associated with %s" % ( len( histories ), user.email )
        for history in histories:
            print "Working on history %d" % history.id
            # Delete all of the current default permissions for the history
            for dhp in history.default_permissions:
                dhp.delete()
                dhp.flush()
            # Add the new default permissions for the history
            dhp = app.model.DefaultHistoryPermissions( history, default_user_action, private_role )
            dhp.flush()
            print "Setting ActionDatasetRoleAssociations for %d un-purged datasets in history %d" % ( len( history.activatable_datasets ), history.id )
            # Set the permissions on the current history's datasets that are not purged
            for hda in history.activatable_datasets:
                dataset = hda.dataset
                print "Working on dataset %d" % dataset.id
                if dataset.library_associations:
                    # Don't change permissions on a dataset associated with a library
                    continue
                if [ assoc for assoc in dataset.history_associations if assoc.history not in user.histories ]:
                    # Don't change permissions on a dataset associated with a history not owned by the user
                    continue
                # Delete all of the current permissions on the dataset
                for adra in dataset.actions:
                    adra.delete()
                    adra.flush()
                # Add the new permissions on the dataset
                adra = app.model.ActionDatasetRoleAssociation( default_user_action, dataset, private_role )
                adra.flush()
    app.shutdown()
    print
    print "Update finished, please review output for warnings and errors."
    empty_xml.close() #close tempfile, it will automatically be deleted off system
    

if __name__ == "__main__":
    main()
