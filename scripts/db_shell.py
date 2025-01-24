# This script allows easy access to Galaxy's database layer via the
# Galaxy models. For example:
# % python -i scripts/db_shell.py -c config/galaxy.ini
# >>> new_user = User("admin@gmail.com")
# >>> new_user.set_password
# >>> sa_session.add(new_user)
# >>> sa_session.commit()
# >>> sa_session.query(User).all()
#
# If you use ipython use:
# % ipython -i scripts/db_shell.py -- -c config/galaxy.ini
#
# You can also use this script as a library, for instance see https://gist.github.com/1979583
# these should maybe be refactored to remove duplication.

import datetime
import decimal
import logging
import os.path
import sys

# Setup DB scripting environment
from sqlalchemy import *  # noqa
from sqlalchemy.exc import *  # noqa
from sqlalchemy.orm import *  # noqa
from sqlalchemy.sql import label  # noqa

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.datatypes.registry import Registry
from galaxy.model import *  # noqa
from galaxy.model import set_datatypes_registry  # More explicit than `*` import
from galaxy.model.mapping import init
from galaxy.model.orm.scripts import get_config

WARNING_MODULES = ["parso", "asyncio", "galaxy.datatypes"]
for mod in WARNING_MODULES:
    logger = logging.getLogger(mod)
    logger.setLevel("WARNING")

registry = Registry()
registry.load_datatypes()
set_datatypes_registry(registry)
config = get_config(sys.argv)
db_url = config["db_url"]
sa_session = init("/tmp/", db_url).context


# Helper function for debugging sqlalchemy queries...
# http://stackoverflow.com/questions/5631078/sqlalchemy-print-the-actual-query
def printquery(statement, bind=None):
    """
    Print a query, with values filled in
    for debugging purposes *only*
    for security, you should always separate queries from their values
    please also note that this function is quite slow
    """
    import sqlalchemy.orm

    if isinstance(statement, sqlalchemy.orm.Query):
        if bind is None:
            bind = statement.session.get_bind()
        statement = statement.statement
    elif bind is None:
        bind = statement.bind

    dialect = bind.dialect
    compiler = statement._compiler(dialect)

    class LiteralCompiler(compiler.__class__):
        def visit_bindparam(self, bindparam, within_columns_clause=False, literal_binds=False, **kwargs):
            return super().render_literal_bindparam(
                bindparam, within_columns_clause=within_columns_clause, literal_binds=literal_binds, **kwargs
            )

        def render_literal_value(self, value, type_):
            """Render the value of a bind parameter as a quoted literal.

            This is used for statement sections that do not accept bind paramters
            on the target driver/database.

            This should be implemented by subclasses using the quoting services
            of the DBAPI.

            """
            if isinstance(value, str):
                value = value.replace("'", "''")
                return f"'{value}'"
            elif value is None:
                return "NULL"
            elif isinstance(value, (float, int)):
                return repr(value)
            elif isinstance(value, decimal.Decimal):
                return str(value)
            elif isinstance(value, datetime.datetime):
                return f"TO_DATE('{value.strftime('%Y-%m-%d %H:%M:%S')}','YYYY-MM-DD HH24:MI:SS')"

            else:
                raise NotImplementedError(f"Don't know how to literal-quote value {value!r}")

    compiler = LiteralCompiler(dialect, statement)
    print(compiler.process(statement))
