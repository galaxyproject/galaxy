"""
Use this context handler to profile slow parts of the code.
http://docs.sqlalchemy.org/en/latest/faq/performance.html#code-profiling
"""
import contextlib
import cProfile
import pstats
import StringIO


@contextlib.contextmanager
def profiled():
    pr = cProfile.Profile()
    pr.enable()
    yield
    pr.disable()
    s = StringIO.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    # uncomment this to see who's calling what
    # ps.print_callers()
    print(s.getvalue())
