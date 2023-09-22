import os
import string
import sys

SCRIPTS_DIRECTORY = os.path.dirname(__file__)
TEMPLATE_PATH = os.path.join(SCRIPTS_DIRECTORY, "slideshow_template.html")
TEMPLATE = string.Template(open(TEMPLATE_PATH).read())


def main(argv=None):
    if argv is None:
        argv = sys.argv
    title = argv[1]
    markdown_source = argv[2]
    output = os.path.splitext(markdown_source)[0] + ".html"
    with open(markdown_source) as s:
        content = s.read()
    html = TEMPLATE.safe_substitute(
        **{
            "title": title,
            "content": content,
        }
    )
    print(html)
    open(output, "w").write(html)


if __name__ == "__main__":
    main()
