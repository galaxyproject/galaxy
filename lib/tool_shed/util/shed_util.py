import os, tempfile, shutil, logging, urllib2, threading
from galaxy.datatypes import checkers
from galaxy.web import url_for
from galaxy import util
from galaxy.util import json
from galaxy.webapps.tool_shed.util import container_util
from tool_shed.galaxy_install.tool_dependencies.install_util import install_package, set_environment
from galaxy.model.orm import and_
import tool_shed.util.shed_util_common as suc
from tool_shed.util import encoding_util, repository_dependency_util, tool_dependency_util

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude
from elementtree.ElementTree import Element, SubElement

log = logging.getLogger( __name__ )


