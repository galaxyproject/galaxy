import os

try:
    import lib2to3
    from lib2to3.pgen2 import driver as lib2to3_driver
except ImportError:
    # lib2to3 was removed in Python 3.13. galaxy.util.template falls back to
    # fissix there, which writes its grammar cache atomically.
    lib2to3 = None


def _pregenerate_lib2to3_grammar():
    """Write lib2to3's grammar pickles once, before pytest-xdist starts its workers.

    ``lib2to3.pygram`` (imported via ``galaxy.util.template``) generates the
    pickles next to ``Grammar.txt`` on first import, and does not write them
    atomically. xdist workers collecting in parallel can then load a pickle
    that another worker is still writing and fail with ``EOFError: Ran out of input``.
    """
    grammar_dir = os.path.dirname(lib2to3.__file__)
    for grammar_file in ("Grammar.txt", "PatternGrammar.txt"):
        # Loads the pickle if it is current, otherwise generates and saves it.
        lib2to3_driver.load_grammar(os.path.join(grammar_dir, grammar_file))


def pytest_configure(config):
    try:
        import sqlalchemy.exc  # noqa: F401
    except ImportError:
        pass
    else:
        config.addinivalue_line("filterwarnings", "error::sqlalchemy.exc.SAWarning")
    # The xdist controller configures before it spawns workers (in pytest_sessionstart).
    # Workers have ``workerinput``; they must not race each other here.
    if lib2to3 is not None and not hasattr(config, "workerinput"):
        _pregenerate_lib2to3_grammar()
