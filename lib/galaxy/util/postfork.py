"""
Handle postfork functions under uWSGI
"""

# The uwsgi module is automatically injected by the parent uwsgi
# process and only exists that way.  If anything works, this is a
# uwsgi-managed process.
try:
    import uwsgi
    if hasattr(uwsgi, "numproc"):
        process_is_uwsgi = True
    else:
        process_is_uwsgi = False
except ImportError:
    # This is not a uwsgi process, or something went horribly wrong.
    process_is_uwsgi = False

try:
    from uwsgidecorators import postfork
except:
    def pf_dec(func):
        return func
    postfork = pf_dec
    if process_is_uwsgi:
        print("WARNING: This is a uwsgi process but the uwsgidecorators library"
              " is unavailable.  This is likely due to using an external (not"
              " in Galaxy's virtualenv) uwsgi and you may experience errors.")


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
