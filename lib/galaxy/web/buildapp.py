"""For backward compatibility only, pulls app_factor from galaxy.webapps.main"""

from galaxy.webapps.galaxy.buildapp import app_factory

__all__ = ('app_factory', )
