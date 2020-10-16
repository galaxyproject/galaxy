"""
Decorators for docker
"""
import json
from functools import wraps


def docker_columns(f):
    @wraps(f)
    def parse_docker_column_output(*args, **kwargs):
        """Many docker commands do not provide an option to format the output
        or output in a machine-readily-parseable format (e.g. json). In order
        to deal with such output and hopefully stay compatible with future
        column order changes, key returned rows based on column headers.

        An assumption is made that a single space in the header row does not
        separate columns - column names can have spaces in them, and columns
        are separated by at least 2 spaces. This seems to be true as of Docker
        1.13.1.
        """
        output = f(*args, **kwargs)
        parsed = []
        output = output.splitlines()
        header = output[0]
        colstarts = [0]
        colidx = 0
        spacect = 0
        if not output:
            return parsed
        for i, c in enumerate(header):
            if c != ' ' and spacect > 1:
                colidx += 1
                colstarts.append(i)
                spacect = 0
            elif c == ' ':
                spacect += 1
        colstarts.append(None)
        colheadings = []
        for i in range(0, len(colstarts) - 1):
            colheadings.append(header[colstarts[i]:colstarts[i + 1]].strip())
        for line in output[1:]:
            row = {}
            for i, key in enumerate(colheadings):
                row[key] = line[colstarts[i]:colstarts[i + 1]].strip()
            parsed.append(row)
        return parsed
    return parse_docker_column_output


def docker_json(f):
    @wraps(f)
    def json_loads(*args, **kwargs):
        return json.loads(f(*args, **kwargs))
    return json_loads
