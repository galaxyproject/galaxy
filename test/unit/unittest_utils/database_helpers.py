import os

from sqlalchemy.engine.url import make_url
from sqlalchemy.sql.compiler import IdentifierPreparer

from galaxy.model.database_utils import sqlalchemy_engine


def drop_database(db_url, database):
    """Drop database; connect with db_url.

    Used only for test purposes to cleanup after creating a test database.
    """
    if db_url.startswith('postgresql'):
        with sqlalchemy_engine(db_url) as engine:
            preparer = IdentifierPreparer(engine.dialect)
            database = preparer.quote(database)
            stmt = f'DROP DATABASE IF EXISTS {database}'
            with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
                conn.execute(stmt)
    else:
        url = make_url(db_url)
        os.remove(url.database)
