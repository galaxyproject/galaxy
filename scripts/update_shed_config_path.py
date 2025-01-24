import argparse
import os
import sys
from configparser import ConfigParser

from sqlalchemy import (
    create_engine,
    MetaData,
)
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
)

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

import galaxy.model.tool_shed_install.mapping as mapping
from galaxy.model.base import transaction


def main(opts, session, model):
    """
    Find all tool shed repositories with the bad path and update with the correct path.
    """
    for row in session.query(model.ToolShedRepository).all():
        if "shed_config_filename" in row.metadata_:
            if row.metadata_["shed_config_filename"] == opts.bad_filename:
                row.metadata_["shed_config_filename"] = opts.good_filename
                session.add(row)
                with transaction(session):
                    session.commit()
    return 0


def create_database(config_file):
    parser = ConfigParser()
    parser.read(config_file)
    # Determine which database connection to use.
    database_connection = parser.get("app:main", "install_database_connection")
    if database_connection is None:
        database_connection = parser.get("app:main", "database_connection")
    if database_connection is None:
        database_connection = "sqlite:///{}".format(parser.get("app:main", "database_file"))
    if database_connection is None:
        print("Unable to determine correct database connection.")
        exit(1)

    # Initialize the database connection.
    engine = create_engine(database_connection)
    MetaData(bind=engine)
    install_session = scoped_session(sessionmaker(bind=engine, autoflush=False))
    model = mapping.init(database_connection)
    return install_session, model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config_file", dest="config_file", required=True, help="The path to your Galaxy configuration .ini file."
    )
    parser.add_argument(
        "--from",
        dest="bad_filename",
        required=True,
        help="The old, invalid path to the shed_tool_conf.xml or migrated_tools_conf.xml file.",
    )
    parser.add_argument(
        "--to",
        dest="good_filename",
        required=True,
        help="The updated path to the shed_tool_conf.xml or migrated_tools_conf.xml file.",
    )
    parser.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="Use this flag to set the new path even if the file does not (yet) exist there.",
    )
    opts = parser.parse_args()
    if not os.path.exists(opts.good_filename) and not opts.force:
        print(f"The file {opts.good_filename} does not exist, use the --force option to proceed.")
        exit(1)
    session, model = create_database(opts.config_file)
    exit(main(opts, session, model))
