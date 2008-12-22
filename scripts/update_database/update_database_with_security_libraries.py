#!/usr/bin/env python
#Dan Blankenberg
"""
Backup your database before running.

Updates a pre-security/library database with necessary schema changes 
and sets default roles/permissions for users and their histories and datasets. 

It will reset permissions on histories and datasets if are already set.

This has been tested with Postgres, SQLite, and MySQL databases.

Due to limitations of SQLite this script is unable to add
foreign keys to existing SQLite tables (fks are ignored anyway).

Remember to backup your database before running.
"""

import sys, os, ConfigParser, tempfile
import galaxy.app, galaxy.model
import sqlalchemy

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    def print_warning( warning_text ):
        print "\nWarning: %s\n" % ( warning_text )
    
    print
    print "The purpose of this script is to update an existing Galaxy database that does not have Library or Security settings to a version that does."
    print
    print "This script will set default roles for users (If run on an already updated database this will reset all datasets to initial permissions - public)."
    print
    print "*** It is important to backup your database before you continue. ***"
    print
    print "If you have backed up your database and would like to run this script, type 'yes'."
    print
    should_continue = raw_input("enter 'yes' to continue>")
    if should_continue.lower() != "yes":
        print "Script aborted by user."
        sys.exit(0)
    
    #Load Configuration from file
    ini_file = sys.argv.pop(1)
    conf_parser = ConfigParser.ConfigParser({'here':os.getcwd()})
    conf_parser.read(ini_file)
    configuration = {}
    for key, value in conf_parser.items("app:main"): configuration[key] = value
    
    #if we don't load the tools, the app will startup much faster
    empty_xml = tempfile.NamedTemporaryFile()
    empty_xml.write( "<root/>" )
    empty_xml.flush()
    configuration['tool_config_file'] = empty_xml.name
    #No need to load job runners
    configuration['enable_job_running'] = False
    
    print
    print "Loading app, with database_create_tables=False, to add Columns to existing tables"
    print
    #we set database_create_tables to False, then load the app
    configuration['database_create_tables'] = False
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    
    #try to guess the database type that we have, in order to execute the proper raw SQL commands
    if app.config.database_connection:
        dialect = galaxy.model.mapping.guess_dialect_for_url( app.config.database_connection )
    else:
        dialect = "sqlite" #default dialect is sqlite
    
    #Now we alter exisiting tables
    #Unfortunately SQLAlchemy does not support this
    #SQLite is very lacking in its implementation of the ALTER command, we'll do what we can...
    
    #we cannot check with SA to see if new columns exist, so we will try and except (trying to access the table with our current SA Metadata which references missing columns will cause exception)
    #user table
    #this table needs to be altered differently depending on if we are using sqlite or not
    if dialect == "sqlite":
        try:
            app.model.session.execute( "ALTER TABLE 'galaxy_user' ADD COLUMN 'deleted' BOOLEAN default 0" ) #'true' and 'false' doesn't work properly in SQLite --> both are always True (is sqlite actually storing a string here, which is always true when not empty?)
        except sqlalchemy.exceptions.OperationalError, e:
            print_warning( "adding column 'deleted' failed: %s" % ( e ) )
        try:
            app.model.session.execute( "ALTER TABLE 'galaxy_user' ADD COLUMN 'purged' BOOLEAN default 0" )
        except sqlalchemy.exceptions.OperationalError, e:
            print_warning( "adding column 'purged' failed: %s" % ( e ) )
    else:
        try:
            app.model.session.execute( "ALTER TABLE galaxy_user ADD COLUMN deleted BOOLEAN default false" )
        except ( sqlalchemy.exceptions.ProgrammingError, sqlalchemy.exceptions.OperationalError ), e: #Postgres and MySQL raise different Exceptions for this same failure.
            print_warning( "adding column 'deleted' failed: %s" % ( e ) )
        try:
            app.model.session.execute( "ALTER TABLE galaxy_user ADD COLUMN purged BOOLEAN default false" )
        except ( sqlalchemy.exceptions.ProgrammingError, sqlalchemy.exceptions.OperationalError ), e:
            print_warning( "adding column 'purged' failed: %s" % ( e ) )
    
    #these alters are the same, regardless if we are using sqlite
    #hda table
    try:
        app.model.session.execute( "ALTER TABLE history_dataset_association ADD COLUMN copied_from_library_folder_dataset_association_id INTEGER" )
    except ( sqlalchemy.exceptions.ProgrammingError, sqlalchemy.exceptions.OperationalError ), e:
        print_warning( "adding column 'copied_from_library_folder_dataset_association_id' failed: %s" % ( e ) )
    
    #MetadataFile table
    try:
        app.model.session.execute( "ALTER TABLE metadata_file ADD COLUMN lda_id INTEGER" )
    except ( sqlalchemy.exceptions.ProgrammingError, sqlalchemy.exceptions.OperationalError ), e:
        print_warning( "adding column 'lda_id' failed: %s" % ( e ) )
    
    
    #now create indexes for new columns in user and metadata file tables
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
    
    
    #Now we shutdown the app
    app.shutdown()
    del app
    print
    print "Columns added to tables, restarting app, with database_create_tables=True"
    
    #We restart the app, this time with create_tables == True
    configuration['database_create_tables'] = True
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    
    ##Now we add foreign key constraints as necessary for columns added above
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
        #Can't do this in SQLite
        #SQLite ignores (but parses on initial table creation) foreign key constraints anyway, see: http://www.sqlite.org/omitted.html (there is someway to set up behavior using triggers)
        print_warning( "Adding foreign key constraints to table is not supported in SQLite." )
    
    print "creating private roles and setting defaults for existing users and their histories and datasets"
    security_agent = app.security_agent
    # For each user:
    # 1. make sure they have a private role
    # 2. set DefauultUserPermissions
    # 3. set DefaultHisstoryPermissions on existing histories 
    # 4. set ActionDatasetRoleAssociations on each history's activatable_datasets
    default_user_action = security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action
    for user in app.model.User.query().all():
        print "Setting up user %s." % user.email
        private_role = security_agent.get_private_user_role( user )
        if not private_role:
            security_agent.create_private_user_role( user )
            print "Created private role for %s" % user.email
        else:
            print_warning( "%s already has a private role, (re)setting defaults anyway" % user.email )
        print "Setting DefaultUserPermissions for user %s" % user.email
        # Delete all of the current default permissions for the user
        for dup in user.default_permissions:
            dup.delete()
            dup.flush()
        # Add the new default permissions for the user
        dup = self.model.DefaultUserPermissions( user, default_user_action, private_role )
        dup.flush()
        print "Setting DefaultHistoryPermissions for %d histories" % len( user.active_histories )
        # Set DefaultHistoryPermissions on all of the user's active histories and associated datasets
        for history in user.active_histories:
            # Delete all of the current default permission for the history
            for dhp in history.default_permissions:
                dhp.delete()
                dhp.flush()
            # Add the new default permissions for the history
            dhp = self.model.DefaultHistoryPermissions( history, default_user_action, private_role )
            dhp.flush()
            print "Setting ActionDatasetRoleAssociations for %d datasets in history %d" % ( len( history.activatable_datasets ), history.id )
            # Set the permissions on the current history's datasets that are not purged
            for hda in history.activatable_datasets:
                dataset = hda.dataset
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
                adra = self.model.ActionDatasetRoleAssociation( default_user_action, dataset, private_role )
                adra.flush()
    app.shutdown()
    print
    print "Update finished, please review output for warnings and errors."
    empty_xml.close() #close tempfile, it will automatically be deleted off system
    

if __name__ == "__main__":
    main()
