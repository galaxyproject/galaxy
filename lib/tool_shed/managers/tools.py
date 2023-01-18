from collections import namedtuple

from galaxy import exceptions
from tool_shed.context import SessionRequestContext
from tool_shed.webapp.search.tool_search import ToolSearch


def search(trans: SessionRequestContext, q: str, page: int = 1, page_size: int = 10) -> dict:
    """
    Perform the search over TS tools index.
    Note that search works over the Whoosh index which you have
    to pre-create with scripts/tool_shed/build_ts_whoosh_index.sh manually.
    Also TS config option toolshed_search_on has to be True and
    whoosh_index_dir has to be specified.
    """
    app = trans.app
    conf = app.config
    if not conf.toolshed_search_on:
        raise exceptions.ConfigDoesNotAllowException(
            "Searching the TS through the API is turned off for this instance."
        )
    if not conf.whoosh_index_dir:
        raise exceptions.ConfigDoesNotAllowException(
            "There is no directory for the search index specified. Please contact the administrator."
        )
    search_term = q.strip()
    if len(search_term) < 1:
        raise exceptions.RequestParameterInvalidException("The search term has to be at least one character long.")

    tool_search = ToolSearch()

    Boosts = namedtuple(
        "Boosts", ["tool_name_boost", "tool_description_boost", "tool_help_boost", "tool_repo_owner_username_boost"]
    )
    boosts = Boosts(
        float(conf.get("tool_name_boost", 1.2)),
        float(conf.get("tool_description_boost", 0.6)),
        float(conf.get("tool_help_boost", 0.4)),
        float(conf.get("tool_repo_owner_username_boost", 0.3)),
    )

    results = tool_search.search(trans.app, search_term, page, page_size, boosts)
    results["hostname"] = trans.repositories_hostname
    return results
