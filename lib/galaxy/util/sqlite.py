import sqlite3
import sqlparse
import re


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def is_read_only_query(query):
	statements = sqlparse.parse(query)
	for statement in statements:
		if statement.get_type() != "SELECT":
			return False
	return True