import argparse
import difflib
import sys

from lxml import etree

DESCRIPTION = """Format Galaxy tool XML files with consistent indentation."""


def format_xml(content: str, tab_size: int = 4) -> str:
    """Format XML content with consistent indentation.

    Used by planemo's format command and the Galaxy Language Server
    to apply uniform formatting to Galaxy tool XML files.
    """
    try:
        parser = etree.XMLParser(strip_cdata=False)
        xml = etree.fromstring(content, parser=parser)
        etree.indent(xml, space=" " * tab_size)
        return etree.tostring(xml, pretty_print=True, encoding=str)
    except etree.XMLSyntaxError:
        return content


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("xml_files", nargs="+", metavar="FILE", help="Galaxy tool XML file(s) to format")
    parser.add_argument(
        "-t", "--tab-size", type=int, default=4, help="Number of spaces per indentation level (default: 4)"
    )
    parser.add_argument("-d", "--diff", action="store_true", help="Show diff of changes instead of formatting in-place")
    return parser


def main(argv=None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = arg_parser().parse_args(argv)
    has_diff = False

    for path in args.xml_files:
        with open(path) as f:
            original = f.read()

        formatted = format_xml(original, tab_size=args.tab_size)
        changed = original != formatted

        if args.diff:
            if changed:
                has_diff = True
                diff = difflib.unified_diff(
                    original.splitlines(keepends=True),
                    formatted.splitlines(keepends=True),
                    fromfile=path,
                    tofile=path,
                )
                sys.stdout.writelines(diff)
        else:
            if changed:
                with open(path, "w") as f:
                    f.write(formatted)
                print(f"reformatted {path}")
            else:
                print(f"{path} already formatted")

    if args.diff and has_diff:
        sys.exit(1)


if __name__ == "__main__":
    main()
