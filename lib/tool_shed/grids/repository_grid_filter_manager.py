import logging

from galaxy.util.bunch import Bunch

log = logging.getLogger(__name__)


class RepositoryGridFilterManager:
    """Provides filtered views of the many Tool SHed repository grids."""

    filters = Bunch(
        CERTIFIED_LEVEL_ONE="certified_level_one",
        CERTIFIED_LEVEL_TWO="certified_level_two",
        CERTIFIED_LEVEL_ONE_SUITES="certified_level_one_suites",
        CERTIFIED_LEVEL_TWO_SUITES="certified_level_two_suites",
        SUITES="suites",
    )

    def get_grid_title(self, trans, trailing_string="", default=""):
        filter = self.get_filter(trans)
        if filter == self.filters.CERTIFIED_LEVEL_ONE:
            return f"Certified 1 Repositories {trailing_string}"
        if filter == self.filters.CERTIFIED_LEVEL_TWO:
            return f"Certified 2 Repositories {trailing_string}"
        if filter == self.filters.CERTIFIED_LEVEL_ONE_SUITES:
            return f"Certified 1 Repository Suites {trailing_string}"
        if filter == self.filters.CERTIFIED_LEVEL_TWO_SUITES:
            return f"Certified 2 Repository Suites {trailing_string}"
        if filter == self.filters.SUITES:
            return f"Repository Suites {trailing_string}"
        return f"{default} {trailing_string}"

    def get_filter(self, trans):
        filter = trans.get_cookie(name="toolshedrepogridfilter")
        return filter or None

    def is_valid_filter(self, filter):
        if filter is None:
            return True
        for valid_filter in self.filters.values():
            if filter == valid_filter:
                return True
        return False

    def set_filter(self, trans, **kwd):
        # Set a session cookie value with the selected filter.
        filter = kwd.get("filter", None)
        if filter is not None and self.is_valid_filter(filter):
            trans.set_cookie(value=filter, name="toolshedrepogridfilter")
        # if the filter is not valid, expire the cookie.
        trans.set_cookie(value=filter, name="toolshedrepogridfilter", age=-1)
