from urllib.parse import (
    quote_plus,
    urlencode,
    urljoin,
)

from galaxy.util import commands


def count_special_lines(word, filename, invert=False):
    """
    searching for special 'words' using the grep tool
    grep is used to speed up the searching and counting
    The number of hits is returned.
    """
    cmd = ["grep", "-c", "-E"]
    if invert:
        cmd.append("-v")
    cmd.extend([word, filename])
    try:
        out = commands.execute(cmd)
    except commands.CommandLineException:
        return 0
    return int(out)


def display_as_url(app, base_url: str, dataset_id: str, display_app: str) -> str:
    """Generate a link to the ``display_as`` action the the ``root`` controller, encoded for use as a query param."""
    display_base_url = urljoin(base_url, app.url_for(controller="root", action="display_as"))
    display_query = urlencode(
        {
            "id": dataset_id,
            "display_app": display_app,
            "authz_method": "display_at",
        }
    )
    display_url = quote_plus(f"{display_base_url}?{display_query}")
    return display_url
