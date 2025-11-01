"""Helper functions for accessing story example data files."""

from pathlib import Path


def get_data_directory() -> Path:
    """Get the path to the stories data directory.

    Returns:
        Path to lib/galaxy/selenium/stories/data/examples/
    """
    return Path(__file__).parent / "examples"


def get_example_path(filename: str) -> str:
    """Get the absolute path to a story example file.

    Args:
        filename: Name of the example file (e.g., 'workbook_example_1.tsv')

    Returns:
        Absolute path to the example file

    Example:
        >>> path = get_example_path('workbook_example_1.tsv')
        >>> # Use in tests: self.workbook_upload(path)
    """
    return str(get_data_directory() / filename)


__all__ = [
    "get_data_directory",
    "get_example_path",
]
