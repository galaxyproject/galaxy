import sqlite3
import re


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def is_read_only_query(query):
    if re.match("select ", query, re.IGNORECASE):
        if re.search("^([^\"]|\"[^\"]*\")*?;", query) or re.search("^([^\']|\'[^\']*\')*?;", query):
            return False
        else:
            return True
    return False
