"""
Handle postfork functions under uWSGI
"""

# The uwsgi module is automatically injected by the parent uwsgi
# process and only exists that way.  If anything works, this is a
# uwsgi-managed process.
try:
    import uwsgi
    from uwsgidecorators import postfork
    if uwsgi.numproc:
        process_is_uwsgi = True
except ImportError:
    # This is not a uwsgi process, or something went horribly wrong.
    process_is_uwsgi = False

    def pf_dec(func):
        return func
    postfork = pf_dec


postfork_functions = []


@postfork
def do_postfork():
    for f, args, kwargs in [ t for t in postfork_functions ]:
        f(*args, **kwargs)


def register_postfork_function(f, *args, **kwargs):
    if process_is_uwsgi:
        postfork_functions.append((f, args, kwargs))
    else:
        f(*args, **kwargs)
