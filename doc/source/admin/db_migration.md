# Galaxy Database Schema Migrations

Galaxy's database schema migration system is built on top of [Alembic](https://alembic.sqlalchemy.org) - a lightweight database migration tool for usage with SQLAlchemy. 
(This documentation applies to release 22.05 and up. Prior to 22.05, Galaxy used SQLAlchemy Migrate.)

## Administering Galaxy: upgrading and downgrading the database

To initialize an empty database (or create a new SQLite database) start Galaxy. However, this approach is safe only if booting to a single process. A better approach is to use the [*init*](#init) command: `manage_db.sh init`.

To upgrade or downgrade an existing database, you'll need to use the `manage_db.sh` script, which is the recommended way to interact with Galaxy's database schema migration system.

### manage_db.sh

```
usage: manage_db.sh [-h] [-c CONFIG] {upgrade,downgrade,version,v,dbversion,dv,init} ...

positional arguments:
  {upgrade,downgrade,version,v,dbversion,dv,init}
    upgrade             Upgrade to a later version
    downgrade           Revert to a previous version
    version (v)         Show the head revision in the migrations script directory
    dbversion (dv)      Show the current revision for Galaxy's database
    init                Initialize empty database(s)

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --galaxy-config CONFIG
                        Alternate Galaxy configuration file
```

#### Subcommands

##### upgrade

Upgrade to a later version. The revision argument is optional.

```
usage: manage_db.sh upgrade [-h] [--sql] [revision]

positional arguments:
  revision    Revision identifier or release tag

optional arguments:
  -h, --help  show this help message and exit
  --sql       Don't emit SQL to database - dump to standard output/file instead.
```

If you are upgrading a database that has not been version-controlled by Alembic, you should run this
command for the first time without the revision argument: `./manage_db.sh upgrade` - this will ensure
proper initialization of the migration system for your database(s).

If you are upgrading to a specific release, you may use a release tag as the revision argument:

```
./manage_db.sh upgrade release_22.05
./manage_db.sh upgrade 22.05
```

You can upgrade to releases 22.05 and up.

For the `--sql` option, see [Alembic documentation on offline mode](https://alembic.sqlalchemy.org/en/latest/offline.html).

##### downgrade

Revert to a previous version.

```
usage: manage_db.sh downgrade [-h] [--sql] revision

positional arguments:
  revision    Revision identifier or release tag

optional arguments:
  -h, --help  show this help message and exit
  --sql       Don't emit SQL to database - dump to standard output/file instead.
```

If you are downgrading to a specific release, you may use a release tag as the revision argument:

```
./manage_db.sh downgrade release_22.01
./manage_db.sh downgrade 22.01
```

The oldest release you can downgrade to is 22.01.

*Note that when you downgrade to 22.01, your database should be under version control by
SQLAlchemy Migrate (the migrations tool used prior to release 22.05). Your database should have a
table `migrate_version` that contains version 180.*

For the `--sql` option, see [Alembic documentation on offline mode](https://alembic.sqlalchemy.org/en/latest/offline.html). 
Note that in this mode, instead of specifying a revision identifier, you have to specify a range of revisions using the following format: `<from-rev>:<to-ref>`.

##### version

Show the latest (i.e., head) revisions in the codebase.

```
Activating virtualenv at .venv
\usage: manage_db.sh version [-h] [-v]

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Display more detailed output
```


##### dbversion

Show the current revision for Galaxy's database. If the database revision corresponds to the head revision in the codebase, it will be marked as `(head)`.

```
usage: manage_db.sh dbversion [-h] [-v]

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Display more detailed output
```

##### init

Initialize an empty database (or create a new SQLite database).

```
usage: manage_db.sh init [-h]

optional arguments:
  -h, --help  show this help message and exit
```

## Advanced usage

The following sections provide more details on the migration system and describe commands that are relevant for development scenarios.

### Overview

The purpose of the database schema migration system is to support automated, incremental, reversible changes to Galaxy's database schema. Central to this is the concept of a database version (more specifically, database *schema* version). A version is represented by a revision script (the terms *version* and *revision* may be used interchangeably). Executing a revision script will upgrade, or downgrade, the database schema by applying the changes specified in the script.

Galaxy keeps track of the database schema version in two places: one is a directory we refer to as "the migration environment" (located at `lib/galaxy/model/migrations/alembic`), the other is the `alembic_version` table in the database. For Galaxy to run, these versions must be the same, which, essentially, means that the version of the database matches the version expected by the codebase.

On startup, the system checks if the version in the database matches the version in the codebase. If they do not match, and the `database_auto_migrate` configuration option is not set, Galaxy will fail with an error message explaining how to proceed. In most cases, you'll need to upgrade the database schema to the current version, which is represented by the latest revision script in the migration environment.

#### A note on models and branch labels

Galaxy's data model includes the [galaxy model](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/model/__init__.py) and the [install model](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/model/tool_shed_install/__init__.py).
These two models may be persisted in one combined database (which is the default) or two separate databases (which is enabled by setting the
[`install_database_connection`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/webapps/galaxy/config_schema.yml#L157) configuration option). 

These models are represented by migration [branches](https://alembic.sqlalchemy.org/en/latest/branches.html) (versioning lineages with a common base) labeled as *gxy* for the galaxy model and *tsi* for the install model. If both models are hosted in the same databases, the branches will share the same Alembic version table; otherwise, each database has its own version table. 

Each branch has its own version history, represented by revision scripts located in the branch version directory (`migrations/alembic/versions_gxy` for *gxy* and `migrations/alembic/versions_tsi` for *tsi*). 

For a more detailed description of the system's internals, see pull request [#13108](https://github.com/galaxyproject/galaxy/pull/13108).

### Migration management scripts

The **`manage_db.sh`** script is the recommended way to interact with Galaxy's database schema migration system.
It provides access to a subset of commands offered by Alembic's CLI, while hiding some of the
implementation complexity of Galaxy's model. The provided commands and options should be
sufficient for most use cases involving Galaxy development or system and database administration.

Additionally, Galaxy provides two scripts for advanced usage: `db_dev.sh` and `run_alembic.sh`. Both are located in the `scripts` directory.

The **`db_dev.sh`** script is similar to `manage_db.sh`, but provides additional commands and options.

The **`run_alembic.sh`** script is a thin wrapper around the Alembic CLI runner. It offers more
flexibility and the full scope of Alembic's CLI commands and options; however, it requires more detailed command arguments, as well as basic familiarity with [Alembic branches](https://alembic.sqlalchemy.org/en/latest/branches.html). 

#### Revision identifiers

Some of the commands accept revision identifiers as arguments. A revision is usually identified by a
12-digit hexadecimal number (i.e., `6a67bf27e6a6`). Anytime you need to refer to a specific
revision, you have the option to use a partial number.

For example, you may use `./db_dev.sh upgrade 6a` instead of `./db_dev.sh upgrade 6a67bf27e6a6` if `6a` is sufficient to uniquely identify that revision.

(Ref: [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/tutorial.html#partial-revision-identifiers))

#### Relative migration identifiers

You may also use Alembic's syntax for relative migration identifiers for the upgrade/downgrade commands:

To move 2 versions from the current version, a decimal value `+N` can be supplied: 

`./db_dev.sh upgrade +2`

Negative values are accepted for downgrades: 

`./db_dev.sh downgrade -2`

Relative identifiers may also be in terms of a specific revision. For example, to upgrade to
revision 6a67bf27e6a6 plus two additional steps:

`./db_dev.sh upgrade 6a67bf27e6a6+2`.

You may also combine relative migration identifiers with partial revision identifiers:

`./db_dev.sh upgrade 6a+2`. 

(Ref: [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/tutorial.html#relative-migration-identifiers))

*Revision identifiers and relative migration identifiers can be used with all the provided scripts.*

### db_dev.sh

This script offers a set of common database schema migration operations that are executed on the *gxy* branch, which, in the vast majority of cases, is all you need to develop and administer Galaxy.
To run operations on the *tsi* branch, you need to use `run_alembic.sh`.

```
usage: db_dev.sh [-h] [-c CONFIG] [--raiseerr] {upgrade,downgrade,version,v,
       dbversion,dv,history,h,show,s,revision,init} ...

positional arguments:
  {upgrade,downgrade,version,v,dbversion,dv,history,h,show,s,revision,init}
    upgrade             Upgrade to a later version
    downgrade           Revert to a previous version
    version (v)         Show the head revision in the migrations script directory
    dbversion (dv)      Show the current revision for Galaxy's database
    history (h)         List revision scripts in chronological order
    show (s)            Show the revision(s) denoted by the given symbol
    revision            Create a new revision file
    init                Initialize empty database(s)

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --galaxy-config CONFIG
                        Alternate Galaxy configuration file
  --raiseerr            Raise a full stack trace on error
```

#### Subcommands

##### upgrade

This command is identical to the *upgrade* command in the `manage_db.sh` script.

Upgrade to a later version. The revision argument is optional.

```
usage: db_dev.sh upgrade [-h] [--sql] [revision]

positional arguments:
  revision    Revision identifier or release tag

optional arguments:
  -h, --help  show this help message and exit
  --sql       Don't emit SQL to database - dump to standard output/file instead.
```

Omitting the revision argument is equivalent to specifying `heads` as the revision identifier; in
that case, the database(s) will be upgraded to the latest revisions in both branches, *gxy* and
*tsi*.

If you are upgrading a database that has not been version-controlled by Alembic, you should run this
command for the first time without the revision argument: `./db_dev.sh upgrade` - this will ensure
proper initialization of the migration system for your database(s).

If you are upgrading to a specific release, you may use a release tag as the revision argument:

```
./manage_db.sh upgrade release_22.05
./manage_db.sh upgrade 22.05
```

You can upgrade to releases 22.05 and up.

For the `--sql` option, see [Alembic documentation on offline mode](https://alembic.sqlalchemy.org/en/latest/offline.html).

##### downgrade

This command is identical to the *upgrade* command in the `manage_db.sh` script.

Revert to a previous version.

```
usage: db_dev.sh downgrade [-h] [--sql] revision

positional arguments:
  revision    Revision identifier or release tag

optional arguments:
  -h, --help  show this help message and exit
  --sql       Don't emit SQL to database - dump to standard output/file instead.
```

Specifying `base` as the revision identifier will downgrade both branches, *gxy* and *tsi*, to their
initial state prior to any revisions; the `alembic_version` table will be empty.

If you are downgrading to a specific release, you may use a release tag as the revision argument:

```
./manage_db.sh downgrade release_22.01
./manage_db.sh downgrade 22.01
```

The oldest release you can downgrade to is 22.01. Downgrading to 22.01 is the same as specifying
`base` as the revision identifier.

*Note that when you downgrade to 22.01, your database should be under version control by
SQLAlchemy Migrate (the migrations tool used prior to release 22.05). Your database should have a
table `migrate_version` that contains version 180.*

For the `--sql` option, see [Alembic documentation on offline mode](https://alembic.sqlalchemy.org/en/latest/offline.html). 
Note that in this mode, instead of specifying a revision identifier, you have to specify a range of revisions using the following format: `<from-rev>:<to-ref>`*.

*You cannot use this script to downgrade past the initial Alembic revisions that created the *gxy* and *tsi* branches.


##### version

This command is identical to the *upgrade* command in the `manage_db.sh` script.

Show the latest (i.e., head) revisions in the codebase.

```
Activating virtualenv at .venv
\usage: db_dev.sh version [-h] [-v]

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Display more detailed output
```

The output of this command will include the head revisions for both branches:

```
$ .db_dev.sh version
186d4835587b (gxy) (head)
d4a650f47a3c (tsi) (head)
```

##### dbversion

This command is identical to the *upgrade* command in the `manage_db.sh` script.

Show the current revision for Galaxy's database.

```
usage: db_dev.sh dbversion [-h] [-v]

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Display more detailed output
```

If the database revision corresponds to the head revision
in the codebase, it will be marked as `(head)`. The output will be slightly more verbose and will vary
depending on the database.

```
$ ./db_dev.sh dbversion
INFO:alembic.runtime.migration:Context impl PostgresqlImpl.
INFO:alembic.runtime.migration:Will assume transactional DDL.
d4a650f47a3c (head)
6a67bf27e6a6
```

##### history

List revision scripts in chronological order.

```
usage: db_dev.sh history [-h] [-v] [-i]

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Display more detailed output
  -i, --indicate-current
                        Indicate current revision
```

Depending on your setup, the list may include revision histories for both branches. The oldest
revisions are the ones that created the *gxy* and *tsi* branches (introduced in 22.05). The
`--indicate-current` option is particularly useful when you need to determine how far behind (or
ahead) your database version is compared to the version expected by your codebase:

```
$ ./db_dev.sh history --indicate-current
6a67bf27e6a6 -> 186d4835587b (gxy) (head), drop job_state_history.update_time column
b182f655505f -> 6a67bf27e6a6 (gxy) (current), deferred data tables
e7b6dcb09efd -> b182f655505f (gxy), add workflow.source_metadata column
<base> -> e7b6dcb09efd (gxy), create gxy branch
<base> -> d4a650f47a3c (tsi) (head), create tsi branch
```

##### show

Show the revision(s) denoted by the given revision identifier.

```
usage: db_dev.sh show [-h] revision

positional arguments:
  revision    Revision identifier

optional arguments:
  -h, --help  show this help message and exit
```

##### revision

Create a new revision file.

```
usage: db_dev.sh revision [-h] -m MESSAGE [--rev-id REV_ID]

optional arguments:
  -h, --help            show this help message and exit
  -m MESSAGE, --message MESSAGE
                        Message string to use with 'revision'
  --rev-id REV_ID       Specify a revision id instead of generating one
                        (This option is for testing purposes only)
```

The `--message` argument is required: this ensures a readable revision history. The message is
appended to the new revision identifier to form the filename for the new revision script, so it
should be a succinct description of the change:

```
$ ./db_dev.sh revision --message "add column foo to table bar"
[output omitted]

$ ls lib/galaxy/model/migrations/alembic/versions_gxy/
a2e418ad6a15_add_column_foo_to_table_bar.py
```

##### init

Initialize an empty database (or create a new SQLite database) for both branches, *gxy* and *tsi*.

```
usage: db_dev.sh init [-h]

optional arguments:
  -h, --help  show this help message and exit
```

### run_alembic.sh

If you need to run operations on the *tsi* branch, or you need access to the full scope of command
line options provided by Alembic, you should use the `run_alembic.sh` script, which is a thin
wrapper around Alembic's CLI runner. The script modifies the path, initializes the Python virtual
environment, retrieves any necessary configuration values, and invokes the Alembic CLI runner with
appropriate arguments.

Keep in mind that since Galaxy uses branch labels to distinguish between the galaxy and the install
models, in most cases, you'll need to identify the target branch to which your command should be
applied.

#### Examples of usage

Remember to first backup your database(s).

##### Upgrading

Upgrade to the head revision (both, *gxy* and *tsi* branches):

`./run_alembic.sh upgrade heads`

Upgrade to the head revision (*gxy* branch):

`./run_alembic.sh upgrade gxy@head`

Upgrade to 1 revision above the current (*tsi* branch):

`./run_alembic.sh upgrade tsi@+1`

Upgrade to a specific revision:

`./run_alembic.sh upgrade [revision identifier]`

Upgrade to 1 revision above a specific revision:

`./run_alembic.sh upgrade [revision identifier]+1`
 
##### Downgrading

Downgrade to base revision (*gxy* branch):

`./run_alembic.sh downgrade gxy@base`

Downgrade to 1 revision below current (*tsi* branch):

`./run_alembic.sh downgrade tsi@-1`

Downgrade to a specific revision:

`./run_alembic.sh downgrade [revision identifier]`

Downgrade to 1 revision below specific revision:

`./run_alembic.sh downgrade [revision identifier]-1 `

##### Creating new revisions

To create a revision for the galaxy model:

`./run_alembic.sh revision --head=gxy@head --message "your description"`

To create a revision for the install model:

`./run_alembic.sh revision --head=tsi@head --message "your description"`

Check [Alembic's documentation](https://alembic.sqlalchemy.org) for more examples.

*Note: the `run_alembic.sh` script does not support relative upgrades and downgrades without a
revision identifier: you cannot `upgrade +1` or `downgrade -1` without providing a revision identifier.*

### Upgrading from SQLAlchemy Migrate

Galaxy no longer supports SQLAlchemy Migrate. To upgrade to Alembic, follow these steps:

1. Backup your database(s).

2. Make sure your codebase is in pre-22.05 state: you will need to use the old `manage_db.sh` script which invokes the SQLAlchemy Migrate tool, which is not available in 22.05 and up. Checking out the 22.01 release branch is the simplest step.

3. Verify that your database is at the latest SQLAlchemy Migrate version. If you have a combined database, it should be version 180 (check the `migrate_version` table). If you have separate galaxy model and install model databases, your galaxy version should be 180, and your install model version should be 17.

   If your database is not current, run `manage_db.sh upgrade` to upgrade your database.

   Once your database has the latest SQLAlchemy Migrate version, switch back to your current branch (22.05 or more recent).

5. Run `manage_db.sh upgrade`.

## Developing Galaxy: creating new revisions

Make sure you have updated the model and have added appropriate tests before creating a new
revision.

You create a new revision file by running the `revision` subcommand of the `manage_db.sh` or the
`run_alembic.sh` script (see sections above for usage information). Alembic generates a revision
script in the appropriate version directory (`migrations/alembic/versions_gxy` for *gxy* and
`migrations/alembic/versions_tsi` for *tsi*). You'll need to fill out the `upgrade` and `downgrade`
functions. Use Alembic documentation for examples:

- [https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script](https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script)
- [https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html)

We encourage you to use Galaxy-specific utility functions (`galaxy/model/migrations/util.py`) when appropriate. Don't forget to provide tests for any modifications you make to the model (most likely, you will need to add them to the appropriate `test/unit/data/model/mapping/test_*model_mapping.py` module.

After that, run the upgrade script: `./manage_db.sh upgrade`. And you're done!

## Troubleshooting

### Deadlock detected

If you see a deadlock error, that may have been caused by a migration script requiring exclusive access
to a database object, such as a row or a table. To avoid this error, it is recommended to shut down
all Galaxy processes during database migration.

### How to handle migrations.IncorrectVersionError

If you see this error, you'll need to upgrade or downgrade your database *before* upgrading to
Alembic. Whether you need to upgrade or downgrade depends on what version number is stored in 
the `migrate_version` table in your database. Alembic expects version 180, so you will need to
upgrade if your version is less than that or, in very rare circumstances, downgrade if your version
is 181. Please see [this issue](https://github.com/galaxyproject/galaxy/issues/13528) for more details.

#### Please help us improve this page:
If you encounter any migration-related errors or issues, please [open an issue](https://github.com/galaxyproject/galaxy/issues/new?assignees=&labels=&template=bug_report.md&title=), and we will add the solution with any relevant context to this page.
