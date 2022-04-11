# Galaxy's Migrations System

## Overview

Starting with release 22.05, to manage its database migrations, Galaxy uses [Alembic](https://alembic.sqlalchemy.org). 

Galaxy's data model is split into the [galaxy model](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/model/__init__.py) and the [install model](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/model/tool_shed_install/__init__.py). These two models may be persisted in one combined database (which is the default) or two separate databases (which is enabled by setting the [`install_database_connection`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/webapps/galaxy/config_schema.yml#L157) configuration option). 

To accommodate this setup, the Alembic-based migrations system uses [branches](https://alembic.sqlalchemy.org/en/latest/branches.html#working-with-branches). A branch is a versioning lineage that starts at a common base revision and represents part of Galaxy's data model. These branches are identified by labels (`gxy` for the galaxy model and `tsi` for the install model) and may share the same Alembic version table (if they share the same database; otherwise, each database has its own version table). Each branch has its own version history, represented by revision scripts located in the branch version directory (`migrations/alembic/versions_gxy` for `gxy` and `migrations/alembic/versions_tsi` for `tsi`). 

## Administering Galaxy: upgrading and downgrading the database

To create a database or initialize an empty database, simply start Galaxy. You may also use the `create_db.sh script`. For usage and options, see the inline documentation in that file. Note that this will create and/or initialize new databases (or one combined database) for the `gxy` and `tsi` models. This script does not handle the Tool Shed database, for which you need to use the `create_toolshed_db.sh` script.

To upgrade or downgrade an existing database that has been initialized, use the `manage_db.sh` script. For usage and options, see the inline documentation in the file. This script supports a subset of command line options offered previously by SQLAlchemy Migrate. It takes care of adjusting the path, initializing the Python virtual environment, retrieving necessary configuration values, and invoking Alembic with appropriate arguments.

For advanced usage and access to the full scope of command line options provided by Alembic, you may use the `run_alembic.sh` script, which is a thin wrapper around the Alembic runner. For usage options, see the inline documentation in that file, as well as [Alembic's documentation](https://alembic.sqlalchemy.org). Keep in mind, that since Galaxy uses branch labels to distinguish between the galaxy and the install models, in most cases, you'll need to identify the target branch to which your command should be applied. Use branch labels: `gxy` for the galaxy model, and `tsi` for install model.

### Examples of usage:

Remember to first backup your database(s).

#### manage_db.sh:

Example 1: upgrade "galaxy" database to version "abc123" using default configuration:
`sh manage_db.sh upgrade --version=abc123`

Example 2: downgrade "install" database to version "xyz789" passing configuration file "mygalaxy.yml":
`sh manage_db.sh downgrade --version=xyz789 -c mygalaxy.yml install`

Example 3: upgrade "galaxy" database to latest version using default configuration:
`sh manage_db.sh upgrade`

#### run_alembic.sh:

##### upgrading

upgrade gxy to head revision
`sh run_alembic.sh upgrade gxy@head`

upgrade gxy to 1 revision above current
`sh run_alembic.sh upgrade gxy@+1`

upgrade branch to a specific revision
`sh run_alembic.sh upgrade [revision identifier]`

upgrade branch to 1 revision above specific revision
`sh run_alembic.sh upgrade [revision identifier]+1`

upgrade gxy and tsi to head revisions
`sh run_alembic.sh upgrade heads`
 
###### downgrading

downgrade gxy to base (empty db with empty alembic table)
`sh run_alembic.sh downgrade gxy@base`

downgrade gxy to 1 revision below current
`sh run_alembic.sh downgrade gxy@-1`

downgrade branch to a specific revision
`sh run_alembic.sh downgrade [revision identifier]`

downgrade branch to 1 revision below specific revision
`sh run_alembic.sh downgrade [revision identifier]-1 `
 
Check Alembic documentation for more examples.
Note: relative upgrades and downgrades without a revision identifier are not supported - i.e., you cannot upgrade +1 or downgrade -1 without providing a revision identifier. However, you can upgrade both branches to their latest versions (head revisions) without providing a branch label: upgrade heads.

### Upgrading from SQLAlchemy Migrate

Galaxy no longer supports SQLAlchemy Migrate. To upgrade to Alembic, follow these steps:

1. Backup your database(s).

2. Verify that your database is at the latest SQLAlchemy Migrate version. If you have a combined database, it should be version 180 (check the `migrate_version` table). If you have separate galaxy model and install model databases, your galaxy version should be 180, and your install model version should be 17.

3. If your database is not current, before upgrading to the 22.05 release, run `manage_db.sh upgrade` to upgrade your database. Once your database has the latest SQLAlchemy Migrate version, you can check out the new code base (22.05 release or the current dev branch) and proceed to migrating to Alembic.

4. If you want Alembic to upgrade your database automatically, you can set the [`database_auto_migrate`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/webapps/galaxy/config_schema.yml#L170) configuration option and simply start Galaxy. Otherwise, use the `manage_db.sh` script.

## Developing Galaxy: creating new revisions

When creating new revisions, as with upgrading/downgrading, you need to indicate the target branch. You use the `run_alembic.sh` script.

To create a revision for the galaxy model:
```./run_alembic.sh revision --head=gxy@head -m "your description"```

To create a revision for the install model:
```./run_alembic.sh revision --head=tsi@head -m "your description"```

Alembic will generate a revision script in the appropriate version directory (the location of the version directories is specified in the `alembic.ini` file). You'll need to fill out the `upgrade()` and `downgrade` functions. Use Alembic documentation for examples:
- [https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script](https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script)
- [https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html)

We encourage you to use Galaxy-specific utility functions (`galaxy/model/migrations/util.py`) when appropriate. Don't forget to provide tests for any modifications you make to the model (most likely, you will need to add them to the appropriate `test/unit/data/model/mapping/test_*model_mapping.py` module.
 
After that, you may run the upgrade script: `manage_sb.sh` upgrade (or `run_alembic.sh` upgrade heads). And you're done! (NOTE: This step should be taken after updating the model and adding appropriate tests.)

## Troubleshooting

[todo]
