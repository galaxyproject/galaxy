"""Dump paths to library dataset files (e.g. for backups). Caveats:

    - Does not perform any permissions checks on library *contents* (but you can restrict to "public" libraries).
    - Only the latest version of undeleted library datasets are dumped.

To use with rsync:
$ python dump_library_paths.py [options] -o libfiles.txt --relative /srv/galaxy/datasets
$ rsync -arvPR --files-from=libfiles.txt /srv/galaxy/datasets backup@backuphost:/backup/galaxy/datasets

Or all in one:
$ python dump_library_paths.py [options] --relative /srv/galaxy/datasets | rsync -arvPR \
    --files-from=- /srv/galaxy/datasets backuphost:/backup/galaxy/datasets
"""
import logging
import os
import sys

from sqlalchemy import false, not_

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

import galaxy.config
import galaxy.model.mapping
from galaxy.objectstore import build_object_store_from_config
from galaxy.util.script import main_factory

DESCRIPTION = "Locate all datasets in libraries."
ARGUMENTS = (
    (
        ('-v', '--verbose'),
        dict(
            action='store_true',
            default=False,
            help='Verbose logging output',
        ),
    ),
    (
        ('-o', '--output'),
        dict(
            default='stdout',
            help='Write output to file',
        ),
    ),
    (
        ('-p', '--public'),
        dict(
            action='store_true',
            default=False,
            help='Only dump files in "public" libraries'
        ),
    ),
    (
        ('--relative',),
        dict(
            default=None,
            help='Write paths relative to the given directory',
        ),
    ),
    (
        ('--exists',),
        dict(
            action='store_true',
            default=False,
            help='Check for dataset existence, warn if it does not exist',
        ),
    ),
)

logging.basicConfig(stream=sys.stderr)
log = logging.getLogger(__name__)


def _config_logging(args):
    if args.verbose:
        log.setLevel(logging.DEBUG)


def _get_libraries(args, model):
    log.debug('Setting up query')
    library_access_action = model.security_agent.permitted_actions.LIBRARY_ACCESS.action
    query = model.context.query(model.Library)
    query = query.filter(model.Library.table.c.deleted == false())
    if args.public:
        restricted_library_ids = {lp.library_id for lp in (
            model.context.query(model.LibraryPermissions).filter(
                model.LibraryPermissions.table.c.action == library_access_action
            ).distinct())}
        if restricted_library_ids:
            query = query.filter(not_(model.Library.table.c.id.in_(restricted_library_ids)))
    query = query.order_by(model.Library.table.c.name)
    return query


def _walk_library(folder):
    datasets = set()
    for f in folder.folders:
        datasets.update(_walk_library(f))
    for ld in folder.active_datasets:
        datasets.add(ld.library_dataset_dataset_association.dataset)
    return datasets


def _walk_libraries(args, model):
    for library in _get_libraries(args, model):
        for dataset in _walk_library(library.root_folder):
            yield (library, dataset)


def _open_output(args):
    if args.output == 'stdout':
        return sys.stdout
    else:
        return open(args.output, 'w')


def _path(path, args):
    if args.relative is not None:
        return os.path.relpath(path, args.relative)
    else:
        return path


def _get_library_dataset_paths(args, kwargs):
    _config_logging(args)
    config = galaxy.config.Configuration(**kwargs)
    object_store = build_object_store_from_config(config)
    model = galaxy.model.mapping.init('/tmp/', kwargs.get('database_connection'), object_store=object_store)
    output = _open_output(args)
    last_library = None
    log.debug('Beginning library walk')
    for library, dataset in _walk_libraries(args, model):
        if library != last_library:
            log.info('Library: %s', library.name)
        filename = object_store.get_filename(dataset)
        files_dir = dataset.get_extra_files_path()
        if (args.exists and object_store.exists(dataset)) or not args.exists:
            output.write('%s\n' % _path(filename, args))
        elif args.exists:
            log.warning('Missing %s', filename)
        if files_dir and os.path.exists(files_dir):
            output.write('%s\n' % _path(files_dir, args))
        last_library = library
    output.close()


ACTIONS = {
    "get_library_dataset_paths": _get_library_dataset_paths,
}


if __name__ == '__main__':
    main = main_factory(
        description=DESCRIPTION,
        actions=ACTIONS,
        arguments=ARGUMENTS,
        default_action="get_library_dataset_paths"
    )
    main()
