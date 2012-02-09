"""
Manage automatic installation of tools configured in tool_shed_install.xml, all of which were
at some point included in the Galaxy distribution, but are now hosted in the main Galaxy tool
shed.  Tools included in tool_shed_install.xml that have already been installed will not be
re-installed.
"""
import urllib2
from galaxy.tools import ToolSection
from galaxy.util.json import from_json_string, to_json_string
from galaxy.util.shed_util import *

log = logging.getLogger( __name__ )

class InstallManager( object ):
    def __init__( self, app, tool_shed_install_config, install_tool_config ):
        """
        Check tool settings in tool_shed_install_config and install all tools that are
        not already installed.  The tool panel configuration file is the received
        shed_tool_config, which defaults to shed_tool_conf.xml.
        """
        self.app = app
        self.sa_session = self.app.model.context.current
        self.install_tool_config = install_tool_config
        # Parse shed_tool_config to get the install location (tool_path).
        tree = util.parse_xml( install_tool_config )
        root = tree.getroot()
        self.tool_path = root.get( 'tool_path' )
        # Keep an in-memory list of xml elements to enable persistence of the changing tool config.
        config_elems = []
        # Parse tool_shed_install_config to check each of the tools.
        log.debug( "Parsing tool shed install configuration %s" % tool_shed_install_config )
        self.tool_shed_install_config = tool_shed_install_config
        tree = util.parse_xml( tool_shed_install_config )
        root = tree.getroot()
        self.tool_shed = clean_tool_shed_url( root.get( 'name' ) )
        log.debug( "Repositories will be installed from tool shed '%s' into configured tool_path location '%s'" % ( str( self.tool_shed ), str( self.tool_path ) ) )
        self.repository_owner = 'devteam'
        for elem in root:
            config_elems.append( elem )
            if elem.tag == 'repository':
                self.install_repository( elem )
            elif elem.tag == 'section':
                self.install_section( elem )
        shed_tool_conf_dict = dict( config_filename=install_tool_config,
                                    tool_path=self.tool_path,
                                    config_elems=config_elems )
        self.app.toolbox.shed_tool_confs.append( shed_tool_conf_dict )
    def install_repository( self, elem, section_name='', section_id='' ):
        # Install a single repository into the tool config.  If outside of any sections, the entry looks something like:
        # <repository name="cut_wrapper" description="Galaxy wrapper for the Cut tool" installed_changeset_revision="f3ed6cfe6402">
        #    <tool id="Cut1" version="1.0.1" />
        # </repository>
        name = elem.get( 'name' )
        description = elem.get( 'description' )
        changeset_revision = elem.get( 'changeset_revision' )
        # Install path is of the form: <tool path>/<tool shed>/repos/<repository owner>/<repository name>/<installed changeset revision>
        clone_dir = os.path.join( self.tool_path, self.tool_shed, 'repos', self.repository_owner, name, changeset_revision )
        if self.__isinstalled( clone_dir ):
            log.debug( "Skipping automatic install of repository '%s' because it has already been installed in location '%s'" % ( name, clone_dir ) )
        else:
            if section_name and section_id:
                section_key = 'section_%s' % str( section_id )
                if section_key in self.app.toolbox.tool_panel:
                    # Appending a tool to an existing section in self.app.toolbox.tool_panel
                    log.debug( "Appending to tool panel section: %s" % section_name )
                    tool_section = self.app.toolbox.tool_panel[ section_key ]
                else:
                    # Appending a new section to self.app.toolbox.tool_panel
                    log.debug( "Loading new tool panel section: %s" % section_name )
                    new_section_elem = Element( 'section' )
                    new_section_elem.attrib[ 'name' ] = section_name
                    new_section_elem.attrib[ 'id' ] = section_id
                    new_section_elem.attrib[ 'version' ] = ''
                    tool_section = ToolSection( new_section_elem )
                    self.app.toolbox.tool_panel[ section_key ] = tool_section
            else:
                tool_section = None
            current_working_dir = os.getcwd()
            tool_shed_url = self.__get_url_from_tool_shed( self.tool_shed )
            repository_clone_url = os.path.join( tool_shed_url, 'repos', self.repository_owner, name )
            relative_install_dir = os.path.join( clone_dir, name )
            returncode, tmp_name = clone_repository( name, clone_dir, current_working_dir, repository_clone_url )
            if returncode == 0:
                returncode, tmp_name = update_repository( current_working_dir, relative_install_dir, changeset_revision )
                if returncode == 0:
                    tool_shed_repository, metadata_dict = load_repository_contents( app=self.app,
                                                                                    repository_name=name,
                                                                                    description=description,
                                                                                    owner=self.repository_owner,
                                                                                    changeset_revision=changeset_revision,
                                                                                    tool_path=self.tool_path,
                                                                                    repository_clone_url=repository_clone_url,
                                                                                    relative_install_dir=relative_install_dir,
                                                                                    current_working_dir=current_working_dir,
                                                                                    tmp_name=tmp_name,
                                                                                    tool_shed=self.tool_shed,
                                                                                    tool_section=tool_section,
                                                                                    shed_tool_conf=self.install_tool_config,
                                                                                    new_install=True,
                                                                                    dist_to_shed=True )
                    if 'tools' in metadata_dict:
                        # Get the tool_versions from the tool shed for each tool in the installed change set.
                        url = '%s/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy' % \
                            ( tool_shed_url, name, self.repository_owner, changeset_revision )
                        response = urllib2.urlopen( url )
                        text = response.read()
                        response.close()
                        if text:
                            tool_version_dicts = from_json_string( text )
                            handle_tool_versions( self.app, tool_version_dicts, tool_shed_repository )
                        else:
                            # Set the tool versions since they seem to be missing for this repository in the tool shed.
                            # CRITICAL NOTE: These default settings may not properly handle all parent/child associations.
                            for tool_dict in metadata_dict[ 'tools' ]:
                                flush_needed = False
                                tool_id = tool_dict[ 'guid' ]
                                old_tool_id = tool_dict[ 'id' ]
                                tool_version = tool_dict[ 'version' ]
                                tool_version_using_old_id = get_tool_version( self.app, old_tool_id )
                                tool_version_using_guid = get_tool_version( self.app, tool_id )
                                if not tool_version_using_old_id:
                                    tool_version_using_old_id = self.app.model.ToolVersion( tool_id=old_tool_id,
                                                                                            tool_shed_repository=tool_shed_repository )
                                    self.sa_session.add( tool_version_using_old_id )
                                    self.sa_session.flush()
                                if not tool_version_using_guid:
                                    tool_version_using_guid = self.app.model.ToolVersion( tool_id=tool_id,
                                                                                          tool_shed_repository=tool_shed_repository )
                                    self.sa_session.add( tool_version_using_guid )
                                    self.sa_session.flush()
                                # Associate the two versions as parent / child.
                                tool_version_association = get_tool_version_association( self.app,
                                                                                         tool_version_using_old_id,
                                                                                         tool_version_using_guid )
                                if not tool_version_association:
                                    tool_version_association = self.app.model.ToolVersionAssociation( tool_id=tool_version_using_guid.id,
                                                                                                      parent_id=tool_version_using_old_id.id )
                                    self.sa_session.add( tool_version_association )
                                    self.sa_session.flush()
                else:
                    tmp_stderr = open( tmp_name, 'rb' )
                    log.debug( "Error updating repository '%s': %s" % ( name, tmp_stderr.read() ) )
                    tmp_stderr.close()
            else:
                tmp_stderr = open( tmp_name, 'rb' )
                log.debug( "Error cloning repository '%s': %s" % ( name, tmp_stderr.read() ) )
                tmp_stderr.close()
    def install_section( self, elem ):
        # Install 1 or more repositories into a section in the tool config.  An entry looks something like:
        # <section name="EMBOSS" id="EMBOSSLite">
        #    <repository name="emboss_5" description="Galaxy wrappers for EMBOSS version 5 tools" installed_changeset_revision="bdd88ae5d0ac">
        #        <tool file="emboss_5/emboss_antigenic.xml" id="EMBOSS: antigenic1" version="5.0.0" />
        #        ...
        #    </repository>
        # </section>
        section_name = elem.get( 'name' )
        section_id = elem.get( 'id' )
        for repository_elem in elem:
            self.install_repository( repository_elem, section_name=section_name, section_id=section_id )
    def __get_url_from_tool_shed( self, tool_shed ):
        # The value of tool_shed is something like: toolshed.g2.bx.psu.edu
        # We need the URL to this tool shed, which is something like:
        # http://toolshed.g2.bx.psu.edu/
        for shed_name, shed_url in self.app.tool_shed_registry.tool_sheds.items():
            if shed_url.find( tool_shed ) >= 0:
                if shed_url.endswith( '/' ):
                    shed_url = shed_url.rstrip( '/' )
                return shed_url
        # The tool shed from which the repository was originally
        # installed must no longer be configured in tool_sheds_conf.xml.
        return None
    def __isinstalled( self, clone_dir ):
        full_path = os.path.abspath( clone_dir )
        if os.path.exists( full_path ):
            for root, dirs, files in os.walk( full_path ):
                if '.hg' in dirs:
                    # Assume that the repository has been installed if we find a .hg directory.
                    return True
        return False
