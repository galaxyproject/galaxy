# This script allows easy access to Galaxy's database layer via the
# Galaxy models. For example:
# % python -i scripts/db_shell.py
# >>> new_user = User("admin@gmail.com")
# >>> new_user.set_password
# >>> sa_session.add(new_user)
# >>> sa_session.commit()
# >>> sa_session.query(User).all()
#
# You can also use this script as a library, for instance see https://gist.github.com/1979583
# TODO: This script overlaps a lot with manage_db.py and create_db.py,
# these should maybe be refactored to remove duplication.
import sys
import os.path

db_shell_path = __file__
new_path = [ os.path.join( os.path.dirname( db_shell_path ), os.path.pardir,  "lib" ) ]
new_path.extend( sys.path[1:] )  # remove scripts/ from the path
sys.path = new_path

from galaxy.model.orm.scripts import get_config

from galaxy import eggs
eggs.require( "decorator" )
eggs.require( "Tempita" )
eggs.require( "SQLAlchemy" )

db_url = get_config( sys.argv )['db_url']


# Setup DB scripting environment
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *

from galaxy.model.mapping import init
sa_session = init( '/tmp/', db_url ).context
from galaxy.model import *

# Helper function for debugging sqlalchemy queries...
# http://stackoverflow.com/questions/5631078/sqlalchemy-print-the-actual-query
import decimal
import datetime


def printquery(statement, bind=None):
    """
    print a query, with values filled in
    for debugging purposes *only*
    for security, you should always separate queries from their values
    please also note that this function is quite slow
    """
    import sqlalchemy.orm
    if isinstance(statement, sqlalchemy.orm.Query):
        if bind is None:
            bind = statement.session.get_bind(
                    statement._mapper_zero_or_none()
            )
        statement = statement.statement
    elif bind is None:
        bind = statement.bind

    dialect = bind.dialect
    compiler = statement._compiler(dialect)

    class LiteralCompiler(compiler.__class__):
        def visit_bindparam(
                self, bindparam, within_columns_clause=False,
                literal_binds=False, **kwargs
        ):
            return super(LiteralCompiler, self).render_literal_bindparam(
                bindparam,
                within_columns_clause=within_columns_clause,
                literal_binds=literal_binds,
                **kwargs
            )

        def render_literal_value(self, value, type_):
            """Render the value of a bind parameter as a quoted literal.

            This is used for statement sections that do not accept bind paramters
            on the target driver/database.

            This should be implemented by subclasses using the quoting services
            of the DBAPI.

            """
            if isinstance(value, basestring):
                value = value.replace("'", "''")
                return "'%s'" % value
            elif value is None:
                return "NULL"
            elif isinstance(value, (float, int, long)):
                return repr(value)
            elif isinstance(value, decimal.Decimal):
                return str(value)
            elif isinstance(value, datetime.datetime):
                return "TO_DATE('%s','YYYY-MM-DD HH24:MI:SS')" % value.strftime("%Y-%m-%d %H:%M:%S")

            else:
                raise NotImplementedError(
                    "Don't know how to literal-quote value %r" % value
                )

    compiler = LiteralCompiler(dialect, statement)
    print compiler.process(statement)

