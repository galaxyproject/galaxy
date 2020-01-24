"""For backward compatibility only, pulls app_factor from galaxy.webapps.main"""

try:
    from galaxy.webapps.galaxy.buildapp import app_factory
except ImportError:
    # when installed as a library, galaxy-web-apps may not be available - this
    # is fine - we shouldn't be using this entry point anyway.
    app_factory = None

__all__ = ('app_factory', )
