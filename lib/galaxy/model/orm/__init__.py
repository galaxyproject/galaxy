import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.interfaces import *
import sqlalchemy.exc

from sqlalchemy.ext.orderinglist import ordering_list

dialect_to_egg = {
    "sqlite"   : "pysqlite>=2",
    "postgres" : "psycopg2",
    "postgresql" : "psycopg2",
    "mysql"    : "MySQL_python"
}
