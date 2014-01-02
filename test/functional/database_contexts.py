# Global variables to pass database contexts around. Fairly hackish that they
# are shared this way, but at least they have been moved out of Galaxy's lib/
# code base.
galaxy_context = None
tool_shed_context = None
install_context = None
