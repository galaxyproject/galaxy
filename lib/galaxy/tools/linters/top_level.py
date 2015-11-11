import re


def lint_top_level(tree, lint_ctx):
    root = tree.getroot()
    if "version" not in root.attrib:
        lint_ctx.error("Tool does not define a version attribute.")
    else:
        lint_ctx.valid("Tool defines a version.")

    if "name" not in root.attrib:
        lint_ctx.error("Tool does not define a name attribute.")
    else:
        lint_ctx.valid("Tool defines a name.")

    if "id" not in root.attrib:
        lint_ctx.error("Tool does not define an id attribute.")
    else:
        lint_ctx.valid("Tool defines an id name.")

    id = root.attrib["id"]
    if re.search(r"\s", id):
        lint_ctx.warn("Tool id contains a space - this is discouraged.")
