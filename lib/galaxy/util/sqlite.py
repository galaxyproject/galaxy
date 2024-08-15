import re
import sqlite3

try:
    import sqlparse

    def is_read_only_query(query):
        statements = sqlparse.parse(query)
        for statement in statements:
            if statement.get_type() != "SELECT":
                return False
        return True

except ImportError:
    # Without sqlparse we use a very weak regex check
    def is_read_only_query(query):
        if re.match("select ", query, re.IGNORECASE):
            if re.search('^([^"]|"[^"]*")*?;', query) or re.search("^([^']|'[^']*')*?;", query):
                return False
            else:
                return True
        return False


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection
