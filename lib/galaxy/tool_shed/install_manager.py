"""
Manage automatic installation of tools configured in tool_shed_install.xml, all of which were
at some point included in the Galaxy distribution, but are now hosted in the main Galaxy tool
shed.  Tools included in tool_shed_install.xml that have already been installed will not be
re-installed.
"""
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
        self.app.toolbox.shed_tool_confs[ install_tool_config ] = self.tool_path
        # Parse tool_shed_install_config to check each of the tools.
        log.debug( "Parsing tool shed install configuration %s" % tool_shed_install_config )
        self.tool_shed_install_config = tool_shed_install_config
        tree = util.parse_xml( tool_shed_install_config )
        root = tree.getroot()
        self.tool_shed = clean_tool_shed_url( root.get( 'name' ) )
        log.debug( "Repositories will be installed from tool shed '%s' into configured tool_path location '%s'" % ( str( self.tool_shed ), str( self.tool_path ) ) )
        self.repository_owner = 'devteam'
        for elem in root:
            if elem.tag == 'repository':
                self.install_repository( elem )
            elif elem.tag == 'section':
                self.install_section( elem )
    def install_repository( self, elem, section_name='', section_id='' ):
        # Install a single repository into the tool config.  If outside of any sections, the entry looks something like:
        # <repository name="cut_wrapper" description="Galaxy wrapper for the Cut tool" changeset_revision="f3ed6cfe6402">
        #    <tool id="Cut1" version="1.0.1" />
        # </repository>
        name = elem.get( 'name' )
        description = elem.get( 'description' )
        changeset_revision = elem.get( 'changeset_revision' )
        # Install path is of the form: <tool path>/<tool shed>/repos/<repository owner>/<repository name>/<changeset revision>
        clone_dir = os.path.join( self.tool_path, self.tool_shed, 'repos', self.repository_owner, name, changeset_revision )
        if self.__isinstalled( elem, clone_dir ):
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
                    metadata_dict = load_repository_contents( app=self.app,
                                                              name=name,
                                                              description=description,
                                                              owner=self.repository_owner,
                                                              changeset_revision=changeset_revision,
                                                              tool_path=self.tool_path,
                                                              repository_clone_url=repository_clone_url,
                                                              relative_install_dir=relative_install_dir,
                                                              current_working_dir=current_working_dir,
                                                              tmp_name=tmp_name,
                                                              tool_section=tool_section,
                                                              shed_tool_conf=self.install_tool_config,
                                                              new_install=True )
                    # Add a new record to the tool_id_guid_map table for each
                    # tool in the repository if one doesn't already exist.
                    if 'tools' in metadata_dict:
                        tools_mapped = 0
                        for tool_dict in metadata_dict[ 'tools' ]:
                            flush_needed = False
                            tool_id = tool_dict[ 'id' ]
                            tool_version = tool_dict[ 'version' ]
                            guid = tool_dict[ 'guid' ]
                            tool_id_guid_map = get_tool_id_guid_map( self.app, tool_id, tool_version, self.tool_shed, self.repository_owner, name )
                            if tool_id_guid_map:
                                if tool_id_guid_map.guid != guid:
                                    tool_id_guid_map.guid = guid
                                    flush_needed = True
                            else:
                                tool_id_guid_map = self.app.model.ToolIdGuidMap( tool_id=tool_id,
                                                                                 tool_version=tool_version,
                                                                                 tool_shed=self.tool_shed,
                                                                                 repository_owner=self.repository_owner,
                                                                                 repository_name=name,
                                                                                 guid=guid )
                                flush_needed = True
                            if flush_needed:
                                self.sa_session.add( tool_id_guid_map )
                                self.sa_session.flush()
                                tools_mapped += 1
                        log.debug( "Mapped tool ids to guids for %d tools included in repository '%s'." % ( tools_mapped, name ) )
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
        #    <repository name="emboss_5" description="Galaxy wrappers for EMBOSS version 5 tools" changeset_revision="bdd88ae5d0ac">
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
    def __isinstalled( self, repository_elem, clone_dir ):
        name = repository_elem.get( 'name' )
        installed = False
        for tool_elem in repository_elem:
            tool_config = tool_elem.get( 'file' )
            tool_id = tool_elem.get( 'id' )
            tool_version = tool_elem.get( 'version' )
            tigm = get_tool_id_guid_map( self.app, tool_id, tool_version, self.tool_shed, self.repository_owner, name )
            if tigm:
                # A record exists in the tool_id_guid_map table, so see if the repository is installed.
                if os.path.exists( clone_dir ):
                    installed = True
                    break
        if not installed:
            full_path = os.path.abspath( clone_dir )
            # We may have a repository that contains no tools.
            if os.path.exists( full_path ):
                for root, dirs, files in os.walk( full_path ):
                    if '.hg' in dirs:
                        # Assume that the repository has been installed if we find a .hg directory.
                        installed = True
                        break
        return installed
