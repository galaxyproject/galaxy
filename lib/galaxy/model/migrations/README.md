# Galaxy's Migrations System

## Overview

To manage its database migrations, Galaxy uses [Alembic](https://alembic.sqlalchemy.org). 

Galaxy's data model is split into the [galaxy model](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/model/__init__.py) and the [install model](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/model/tool_shed_install/__init__.py). These two models may be persisted in one combined database (which is the default) or two separate databases (which is enabled by setting the [`install_database_connection`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/webapps/galaxy/config_schema.yml#L157) configuration option). 

To accommodate this setup, the Alembic-based migrations system uses [branches](https://alembic.sqlalchemy.org/en/latest/branches.html#working-with-branches). A branch is a versioning lineage that starts at a common base revision and represents part of Galaxy's data model. These branches are identified by labels (`gxy` for the galaxy model and `tsi` for the install model) and may share the same Alembic version table (if they share the same database; otherwise, each database has its own version table). Each branch has its own version history, represented by revision scripts located in the branch version directory (`migrations/alembic/versions_gxy` for `gxy` and `migrations/alembic/versions_tsi` for `tsi`). 

## Administering Galaxy: upgrading and downgrading the database

To create a database or initialize an empty database, use the `create_db.sh` script. For usage and options, see the inline documentation in the file. Note that this will create and/or initialize new databases (or one combined database) for the `gxy` and `tsi` models. This script does not handle the Tool Shed database.

To upgrade or downgrade an existing database ***that has been migrated to Alembic***, use the `run_alembic.sh` script. For usage and options, see the inline documentation in the file. This script is a thin wrapper around the Alembic runner. It takes care of adjusting the path, initializing the Python virtual environtment, retrieving necessary configuration values, and invoking Alembic with appropriate arguments.

Since Galaxy uses branch labels to distinguish between the galaxy and the install models, in most cases, you'll need to identify the target branch to which your command should be applied. Use branch labels: `gxy` for the galaxy model, and `tsi` for install model.

### Examples of usage:

Remember to first backup your database(s).

#### To upgrade:
```
./run_alembic.sh upgrade gxy@head  # upgrade gxy to head revision
./run_alembic.sh upgrade gxy@+1  # upgrade gxy to 1 revision above current
./run_alembic.sh upgrade [revision identifier]  # upgrade branch to a specific revision
./run_alembic.sh upgrade [revision identifier]+1  # upgrade branch to 1 revision above specific revision
./run_alembic.sh upgrade heads  # upgrade gxy and tsi to head revisions
```

#### To downgrade:
```
./run_alembic.sh downgrade gxy@base  # downgrade gxy to base (empty db with empty alembic table)
./run_alembic.sh downgrade gxy@-1  # downgrade gxy to 1 revision below current
./run_alembic.sh downgrade [revision identifier]  # downgrade branch to a specific revision
./run_alembic.sh downgrade [revision identifier]-1  # downgrade branch to 1 revision below specific revision
```
Check [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/branches.html#working-with-branches) for more examples.

Note: relative upgrades and downgrades without a revision identifier are not supported - i.e., you cannot `upgrade +1` or `downgrade -1` without providing a revision identifier. However, you can upgrade both branches to their latest versions (head revisions) without providing a branch label: `upgrade heads`.

### Legacy script

The `manage_db.sh` script is still available, but is considered legacy. The script supports a subset of command line options offered previously by SQLAlchemy Migrate. For usage, see documentation in the file.


### Upgrading from SQLAlchemy Migrate

Galaxy no longer supports SQLAlchemy Migrate. To upgrade to Alembic, follow these steps:

1. Backup your database(s).

2. Verify that your database is at the latest SQLAlchemy Migrate version. If you have a combined database, it should be version 179 (check the `migrate_version` table). If you have separate galaxy model and install model databases, your galaxy version should be 179, and your install model version should be 17. 

3. If your database is not current, before upgrading to the 22.01 release or the current dev branch, run `manage_db.sh upgrade` to upgrade your database. 
Once your database has the latest SQLAlchemy Migrate version, you can check out the new code base (22.01 release or the current dev branch) and proceed to migrating to Alembic.

4. If you want Alembic to upgrade your database automatically, you can set the [`database_auto_migrate`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/webapps/galaxy/config_schema.yml#L170) configuration option and simply start Galaxy. Otherwise, use the `run_alembic.sh` script.

## Developing Galaxy: creating new revisions

When creating new revisions, as with upgrading/downgrading, you need to indicate the target branch. You use the same `run_alembic.sh` script; however, the syntax is slightly different:

To create a revision for the galaxy model:
```./run_alembic.sh revision --head=gxy@head -m "your description"```

To create a revision for the install model:
```./run_alembic.sh revision --head=tsi@head -m "your description"```

Alembic will generate a revision script in the appropriate version directory (the location of the version directories is specified in the `alembic.ini` file). You'll need to fill out the `upgrade()` and `downgrade` functions. Use Alembic documentation for examples:
- [https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script](https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script)
- [https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html)

After that, you may run the upgrade script: `manage_sb.sh upgrade heads`. And you're done!
(*NOTE: This step should be taken after updating the model and adding appropriate tests.*)
