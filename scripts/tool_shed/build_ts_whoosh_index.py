"""
Build indexes for searching the Tool Shed.
Run this script from the root folder, example:

$ python scripts/tool_shed/build_ts_whoosh_index.py -c config/tool_shed.yml

Make sure you adjust your Toolshed config to:
 * turn on searching with "toolshed_search_on"
 * specify "whoosh_index_dir" where the indexes will be placed

This script expects the Tool Shed's runtime virtualenv to be active.
"""
from __future__ import print_function

import argparse
import logging
import os
import sys

import profilehooks
from mercurial import hg, ui
from whoosh import index
from whoosh.writing import AsyncWriter

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

import tool_shed.webapp.model.mapping as ts_mapping
from galaxy.tool_util.loader_directory import load_tool_elements_from_path
from galaxy.util import (
    directory_hash_id,
    ExecutionTimer,
    pretty_print_time_interval,
    unicodify
)
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args
)
from tool_shed.webapp import (
    config as ts_config,
    model as ts_model
)
from tool_shed.webapp.search.repo_search import schema as repo_schema
from tool_shed.webapp.search.tool_search import schema as tool_schema
from tool_shed.webapp.util.hgweb_config import HgWebConfigManager

if sys.version_info > (3,):
    long = int

log = logging.getLogger()
log.addHandler(logging.StreamHandler(sys.stdout))


def parse_arguments():
    parser = argparse.ArgumentParser(description='Build a disk-backed Toolshed repository index and tool index for searching.')
    populate_config_args(parser)
    parser.add_argument('-d', '--debug',
                        action='store_true',
                        default=False,
                        help='Print extra info')
    args = parser.parse_args()
    app_properties = app_properties_from_args(args)
    config = ts_config.ToolShedAppConfiguration(**app_properties)
    args.dburi = config.database_connection
    args.hgweb_config_dir = config.hgweb_config_dir
    args.whoosh_index_dir = config.whoosh_index_dir
    args.file_path = config.file_path
    if args.debug:
        log.setLevel(logging.DEBUG)
        log.debug('Full options:')
        for i in vars(args).items():
            log.debug('%s: %s' % i)
    return args


def get_or_create_index(whoosh_index_dir):
    tool_index_dir = os.path.join(whoosh_index_dir, 'tools')
    if not os.path.exists(whoosh_index_dir):
        os.makedirs(whoosh_index_dir)
        os.makedirs(tool_index_dir)
    return _get_or_create_index(whoosh_index_dir, repo_schema), _get_or_create_index(tool_index_dir, tool_schema)


def _get_or_create_index(index_dir, schema):
    try:
        return index.open_dir(index_dir, schema=schema)
    except index.EmptyIndexError:
        return index.create_in(index_dir, schema=schema)


@profilehooks.profile
def build_index(whoosh_index_dir, file_path, hgweb_config_dir, dburi, **kwargs):
    """
    Build two search indexes simultaneously
    One is for repositories and the other for tools.
    """
    model = ts_mapping.init(file_path, dburi, engine_options={}, create_tables=False)
    sa_session = model.context.current
    repo_index, tool_index = get_or_create_index(whoosh_index_dir)

    repo_index_writer = AsyncWriter(repo_index)
    tool_index_writer = AsyncWriter(tool_index)
    repos_indexed = 0
    tools_indexed = 0

    execution_timer = ExecutionTimer()
    with repo_index.searcher() as searcher:
        for repo in get_repos(sa_session, file_path, hgweb_config_dir, **kwargs):
            tools_list = repo.pop('tools_list')
            repo_id = repo['id']
            indexed_document = searcher.document(id=repo_id)
            if indexed_document:
                if indexed_document['full_last_updated'] == repo.get('full_last_updated'):
                    # We're done, since we sorted repos by update time
                    break
                else:
                    # Got an update, delete the previous document
                    repo_index_writer.delete_by_term('id', repo_id)

            repo_index_writer.add_document(**repo)

            #  Tools get their own index
            for tool in tools_list:
                tool_index_writer.add_document(**tool)
                tools_indexed += 1

            repos_indexed += 1

    tool_index_writer.commit()
    repo_index_writer.commit()

    log.info("Indexed repos: %s, tools: %s", repos_indexed, tools_indexed)
    log.info("Toolbox index finished %s", execution_timer)


def get_repos(sa_session, file_path, hgweb_config_dir, update_time=None, **kwargs):
    """
    Load repos from DB and included tools from .xml configs.
    """
    hgwcm = HgWebConfigManager()
    hgwcm.hgweb_config_dir = hgweb_config_dir
    # Do not index deleted, deprecated, or "tool_dependency_definition" type repositories.
    q = sa_session.query(ts_model.Repository).filter_by(deleted=False).filter_by(deprecated=False).order_by(ts_model.Repository.update_time.desc())
    q = q.filter(ts_model.Repository.type != 'tool_dependency_definition')

    for repo in q:
        category_names = []
        for rca in sa_session.query(ts_model.RepositoryCategoryAssociation).filter(ts_model.RepositoryCategoryAssociation.repository_id == repo.id):
            for category in sa_session.query(ts_model.Category).filter(ts_model.Category.id == rca.category.id):
                category_names.append(category.name.lower())
        categories = (",").join(category_names)
        repo_id = repo.id
        name = repo.name
        description = repo.description
        long_description = repo.long_description
        homepage_url = repo.homepage_url
        remote_repository_url = repo.remote_repository_url

        times_downloaded = repo.times_downloaded or 0

        repo_owner_username = ''
        if repo.user_id is not None:
            user = sa_session.query(ts_model.User).filter(ts_model.User.id == repo.user_id).one()
            repo_owner_username = user.username.lower()

        approved = 'no'
        for review in repo.reviews:
            if review.approved == 'yes':
                approved = 'yes'
                break

        last_updated = pretty_print_time_interval(repo.update_time)
        full_last_updated = repo.update_time.strftime("%Y-%m-%d %I:%M %p")

        # Load all changesets of the repo for lineage.
        repo_path = hgwcm.get_entry(os.path.join("repos", repo.user.username, repo.name))
        hg_repo = hg.repository(ui.ui(), repo_path.encode('utf-8'))
        lineage = []
        for changeset in hg_repo.changelog:
            lineage.append(unicodify(changeset) + ":" + unicodify(hg_repo[changeset]))
        repo_lineage = str(lineage)

        #  Parse all the tools within repo for a separate index.
        tools_list = []
        path = os.path.join(file_path, *directory_hash_id(repo.id))
        path = os.path.join(path, "repo_%d" % repo.id)
        if os.path.exists(path):
            tools_list.extend(load_one_dir(path))
            for root, dirs, files in os.walk(path):
                if '.hg' in dirs:
                    dirs.remove('.hg')
                for dirname in dirs:
                    tools_in_dir = load_one_dir(os.path.join(root, dirname))
                    tools_list.extend(tools_in_dir)

        yield (dict(id=repo_id,
                    name=name,
                    description=description,
                    long_description=long_description,
                    homepage_url=homepage_url,
                    remote_repository_url=remote_repository_url,
                    repo_owner_username=repo_owner_username,
                    times_downloaded=times_downloaded,
                    approved=approved,
                    last_updated=last_updated,
                    full_last_updated=full_last_updated,
                    tools_list=tools_list,
                    repo_lineage=repo_lineage,
                    categories=categories))


def load_one_dir(path):
    tools_in_dir = []
    tool_elems = load_tool_elements_from_path(path, load_exception_handler=debug_handler)
    if tool_elems:
        for elem in tool_elems:
            root = elem[1].getroot()
            if root.tag == 'tool':
                tool = {}
                if root.find('help') is not None:
                    tool.update(dict(help=root.find('help').text))
                if root.find('description') is not None:
                    tool.update(dict(description=root.find('description').text))
                tool.update(dict(id=root.attrib.get('id'),
                                 name=root.attrib.get('name'),
                                 version=root.attrib.get('version')))
                tools_in_dir.append(tool)
    return tools_in_dir


def debug_handler(path, exc_info):
    """
    By default the underlying tool parsing logs warnings for each exception.
    This is very chatty hence this metod changes it to debug level.
    """
    log.debug("Failed to load tool with path %s." % path, exc_info=exc_info)


def main():
    args = parse_arguments()
    build_index(**vars(args))


if __name__ == "__main__":
    main()
