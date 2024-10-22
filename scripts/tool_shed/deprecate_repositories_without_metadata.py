#!/usr/bin/env python

import configparser
import logging
import os
import string
import sys
import textwrap
import time
from datetime import (
    datetime,
    timedelta,
)
from optparse import OptionParser
from time import strftime

import sqlalchemy as sa
from sqlalchemy import (
    and_,
    distinct,
    false,
    not_,
)

sys.path.insert(1, os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "lib"))

import tool_shed.webapp.config as tool_shed_config
import tool_shed.webapp.model.mapping
from galaxy.model.base import transaction
from galaxy.util import (
    build_url,
    send_mail as galaxy_send_mail,
)

log = logging.getLogger()
log.setLevel(10)
log.addHandler(logging.StreamHandler(sys.stdout))
assert sys.version_info[:2] >= (2, 6)


def build_citable_url(host, repository):
    return build_url(host, pathspec=["view", repository.user.username, repository.name])


def main():
    """
    Script to deprecate any repositories that are older than n days, and have been empty since creation.
    """
    parser = OptionParser()
    parser.add_option("-d", "--days", dest="days", action="store", type="int", help="number of days (14)", default=14)
    parser.add_option(
        "-i",
        "--info_only",
        action="store_true",
        dest="info_only",
        help="info about the requested action",
        default=False,
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        help="verbose mode, print the name of each repository",
        default=False,
    )
    (options, args) = parser.parse_args()
    try:
        ini_file = args[0]
    except IndexError:
        sys.exit(f"Usage: python {sys.argv[0]} <tool shed .ini file> [options]")
    config_parser = configparser.ConfigParser({"here": os.getcwd()})
    config_parser.read(ini_file)
    config_dict = {}
    for key, value in config_parser.items("app:main"):
        config_dict[key] = value
    config = tool_shed_config.Configuration(**config_dict)

    app = DeprecateRepositoriesApplication(config)
    cutoff_time = datetime.utcnow() - timedelta(days=options.days)
    now = strftime("%Y-%m-%d %H:%M:%S")
    print("\n####################################################################################")
    print("# %s - Handling stuff older than %i days" % (now, options.days))

    if options.info_only:
        print("# Displaying info only ( --info_only )")

    deprecate_repositories(app, cutoff_time, days=options.days, info_only=options.info_only, verbose=options.verbose)


def send_mail_to_owner(app, owner, email, repositories_deprecated, days=14):
    """
    Sends an email to the owner of the provided repository.
    """
    smtp_server = app.config.get("smtp_server", None)
    from_address = app.config.get("email_from", None)
    # Since there is no way to programmatically determine the URL for the tool shed from the .ini file, this method requires that
    # an environment variable named TOOL_SHED_CANONICAL_URL be set, pointing to the tool shed that is being checked.
    url = os.environ.get("TOOL_SHED_CANONICAL_URL", None)
    if None in [smtp_server, from_address]:
        print("# Mail not configured, not sending email to repository owner.")
        return
    elif url is None:
        print("# Environment variable TOOL_SHED_CANONICAL_URL not set, not sending email to repository owner.")
        return
    subject = f"Regarding your tool shed repositories at {url}"
    message_body_template = (
        "The tool shed automated repository checker has discovered that one or more of your repositories hosted "
        "at this tool shed url ${url} have remained empty for over ${days} days, so they have been marked as deprecated. If you have plans "
        "for these repositories, you can mark them as un-deprecated at any time."
    )
    message_template = string.Template(message_body_template)
    body = "\n".join(textwrap.wrap(message_template.safe_substitute(days=days, url=url), width=95))
    body += "\n\n"
    body += "Repositories that were deprecated:\n"
    body += "\n".join(build_citable_url(url, repository) for repository in repositories_deprecated)
    try:
        galaxy_send_mail(from_address, email, subject, body, app.config)
        print(
            "# An email has been sent to {}, the owner of {}.".format(
                owner, ", ".join(repository.name for repository in repositories_deprecated)
            )
        )
        return True
    except Exception as e:
        print(f"# An error occurred attempting to send email: {e}")
        return False


def deprecate_repositories(app, cutoff_time, days=14, info_only=False, verbose=False):
    # This method will get a list of repositories that were created on or before cutoff_time, but have never
    # had any metadata records associated with them. Then it will iterate through that list and deprecate the
    # repositories, sending an email to each repository owner.
    start = time.time()
    repository_ids_to_not_check = []
    # Get a unique list of repository ids from the repository_metadata table. Any repository ID found in this table is not
    # empty, and will not be checked.
    stmt = sa.select(distinct(app.model.RepositoryMetadata.table.c.repository_id))
    metadata_records = app.sa_session.execute(stmt)
    for metadata_record in metadata_records:
        repository_ids_to_not_check.append(metadata_record.repository_id)
    # Get the repositories that are A) not present in the above list, and b) older than the specified time.
    # This will yield a list of repositories that have been created more than n days ago, but never populated.
    stmt = sa.select(app.model.Repository.table.c.id).where(
        and_(
            app.model.Repository.table.c.create_time < cutoff_time,
            app.model.Repository.table.c.deprecated == false(),
            app.model.Repository.table.c.deleted == false(),
            not_(app.model.Repository.table.c.id.in_(repository_ids_to_not_check)),
        )
    )
    query_result = app.sa_session.execute(stmt)
    repositories = []
    repositories_by_owner = {}
    repository_ids = [row.id for row in query_result]
    # Iterate through the list of repository ids for empty repositories and deprecate them unless info_only is set.
    for repository_id in repository_ids:
        repository = (
            app.sa_session.query(app.model.Repository).filter(app.model.Repository.table.c.id == repository_id).one()
        )
        owner = repository.user
        if info_only:
            print(
                f"# Repository {repository.name} owned by {repository.user.username} would have been deprecated, but info_only was set."
            )
        else:
            if verbose:
                print(f"# Deprecating repository {repository.name} owned by {owner.username}.")
            if owner.username not in repositories_by_owner:
                repositories_by_owner[owner.username] = dict(owner=owner, repositories=[])
            repositories_by_owner[owner.username]["repositories"].append(repository)
            repositories.append(repository)
    # Send an email to each repository owner, listing the repositories that were deprecated.
    for repository_owner in repositories_by_owner:
        for repository in repositories_by_owner[repository_owner]["repositories"]:
            repository.deprecated = True
            app.sa_session.add(repository)
            session = app.sa_session()
            with transaction(session):
                session.commit()
        owner = repositories_by_owner[repository_owner]["owner"]
        send_mail_to_owner(
            app, owner.username, owner.email, repositories_by_owner[repository_owner]["repositories"], days
        )
    stop = time.time()
    print("# Deprecated %d repositories." % len(repositories))
    print("# Elapsed time: ", stop - start)
    print("####################################################################################")


class DeprecateRepositoriesApplication:
    """Encapsulates the state of a Universe application"""

    def __init__(self, config):
        if config.database_connection is False:
            config.database_connection = f"sqlite:///{config.database}?isolation_level=IMMEDIATE"
        # Setup the database engine and ORM
        self.model = tool_shed.webapp.model.mapping.init(
            config.file_path, config.database_connection, engine_options={}, create_tables=False
        )
        self.config = config

    @property
    def sa_session(self):
        """
        Returns a SQLAlchemy session -- currently just gets the current
        session from the threadlocal session context, but this is provided
        to allow migration toward a more SQLAlchemy 0.4 style of use.
        """
        return self.model.context.current

    def shutdown(self):
        pass


if __name__ == "__main__":
    main()
