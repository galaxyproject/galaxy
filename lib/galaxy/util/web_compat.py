"""Work around for gross circular dependency between galaxy.util and galaxy.web.stack.

Provide a function that will delay to forking in a uwsgi environment but run immediately
otherwise.
"""
try:
    from galaxy.web.stack import register_postfork_function
except ImportError:
    def register_postfork_function(f, *args, **kwargs):
        f(*args, **kwargs)
