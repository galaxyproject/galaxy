import re


def parse_filters(search_term, filters):
    """Support github-like filters for narrowing the results.

    Order of chunks does not matter, only recognized filter names are allowed.

    :param search_term: the original search str from user input

    :returns allow_query: whoosh Query object used for filtering
        results of searching in index
    :returns search_term_without_filters: str that represents user's
        search phrase without the filters
    """
    allow_terms = []
    search_term_without_filters = None
    search_space = search_term.replace('"', "'")
    filter_keys = "|".join(list(filters.keys()))
    pattern = fr"({filter_keys}):(?:\s+)?([\w-]+|\'.*?\')"
    reserved = re.compile(pattern)
    while True:
        match = reserved.search(search_space)
        if match is None:
            search_term_without_filters = ' '.join(search_space.split())
            break
        first_group = match.groups()[0]
        if first_group in filters:
            filter_as = filters[first_group]
            allow_terms.append((filter_as, match.groups()[1].strip().replace("'", "")))
        search_space = search_space[0:match.start()] + search_space[match.end():]
    allow_query = allow_terms if len(allow_terms) > 0 else None
    return allow_query, search_term_without_filters
