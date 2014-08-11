import copy
import logging

log = logging.getLogger( __name__ )


class TagAttributeHandler( object ):

    def __init__( self, app, rdd, unpopulate ):
        self.app = app
        self.altered = False
        self.rdd = rdd
        self.unpopulate = unpopulate

    def process_action_tag_set( self, elem, message ):
        # Here we're inside of an <actions> tag set.  See http://localhost:9009/view/devteam/package_r_2_11_0 .
        # <action>
        #    <repository name="package_readline_6_2" owner="devteam">
        #        <package name="readline" version="6.2" />
        #    </repository>
        # </action>
        elem_altered = False
        new_elem = copy.deepcopy( elem )
        for sub_index, sub_elem in enumerate( elem ):
            altered = False
            error_message = ''
            if sub_elem.tag == 'repository':
                altered, new_sub_elem, error_message = \
                    self.process_repository_tag_set( parent_elem=elem,
                                                     elem_index=sub_index,
                                                     elem=sub_elem,
                                                     message=message )
            if error_message:
                message += error_message
            if altered:
                if not self.altered:
                    self.altered = True
                if not elem_altered:
                    elem_altered = True
                new_elem[ sub_index ] = new_sub_elem
        return elem_altered, new_elem, message

    def process_actions_tag_set( self, elem, message ):
        # <actions>
        #     <package name="libgtextutils" version="0.6">
        #         <repository name="package_libgtextutils_0_6" owner="test" prior_installation_required="True" />
        #     </package>
        from tool_shed.util import xml_util
        elem_altered = False
        new_elem = copy.deepcopy( elem )
        for sub_index, sub_elem in enumerate( elem ):
            altered = False
            error_message = ''
            if sub_elem.tag == 'package':
                altered, new_sub_elem, error_message = self.process_package_tag_set( elem=sub_elem,
                                                                                     message=message )
            elif sub_elem.tag == 'action':
                # <action type="set_environment_for_install">
                #    <repository name="package_readline_6_2" owner="devteam"">
                #        <package name="readline" version="6.2" />
                #    </repository>
                # </action>
                altered, new_sub_elem, error_message = self.process_action_tag_set( elem=sub_elem,
                                                                                    message=message )
            else:
                # Inspect the sub elements of elem to locate all <repository> tags and
                # populate them with toolshed and changeset_revision attributes if necessary.
                altered, new_sub_elem, error_message = self.rdd.handle_sub_elem( parent_elem=elem,
                                                                                 elem_index=sub_index,
                                                                                 elem=sub_elem )
            if error_message:
                message += error_message
            if altered:
                if not self.altered:
                    self.altered = True
                if not elem_altered:
                    elem_altered = True
                new_elem[ sub_index ] = new_sub_elem
        return elem_altered, new_elem, message

    def process_actions_group_tag_set( self, elem, message, skip_actions_tags=False ):
        # Inspect all entries in the <actions_group> tag set, skipping <actions>
        # tag sets that define os and architecture attributes.  We want to inspect
        # only the last <actions> tag set contained within the <actions_group> tag
        # set to see if a complex repository dependency is defined.
        elem_altered = False
        new_elem = copy.deepcopy( elem )
        for sub_index, sub_elem in enumerate( elem ):
            altered = False
            error_message = ''
            if sub_elem.tag == 'actions':
                if skip_actions_tags:
                    # Skip all actions tags that include os or architecture attributes.
                    system = sub_elem.get( 'os' )
                    architecture = sub_elem.get( 'architecture' )
                    if system or architecture:
                        continue
                altered, new_sub_elem, error_message = \
                    self.process_actions_tag_set( elem=sub_elem,
                                                  message=message )
            if error_message:
                message += error_message
            if altered:
                if not self.altered:
                    self.altered = True
                if not elem_altered:
                    elem_altered = True
                new_elem[ sub_index ] = new_sub_elem
        return elem_altered, new_elem, message
        
    def process_config( self, root ):
        error_message = ''
        new_root = copy.deepcopy( root )
        if root.tag == 'tool_dependency':
            for elem_index, elem in enumerate( root ):
                altered = False
                if elem.tag == 'package':
                    # <package name="eigen" version="2.0.17">
                    altered, new_elem, error_message = \
                        self.process_package_tag_set( elem=elem,
                                                      message=error_message )
                if altered:
                    if not self.altered:
                        self.altered = True
                    new_root[ elem_index ] = new_elem
        else:
            error_message = "Invalid tool_dependencies.xml file."
        return self.altered, new_root, error_message

    def process_install_tag_set( self, elem, message ):
        # <install version="1.0">
        elem_altered = False
        new_elem = copy.deepcopy( elem )
        for sub_index, sub_elem in enumerate( elem ):
            altered = False
            error_message = ''
            if sub_elem.tag == 'actions_group':
                altered, new_sub_elem, error_message = \
                    self.process_actions_group_tag_set( elem=sub_elem,
                                                        message=message,
                                                        skip_actions_tags=True )
            elif sub_elem.tag == 'actions':
                altered, new_sub_elem, error_message = \
                    self.process_actions_tag_set( elem=sub_elem,
                                                  message=message )
            else:
                package_name = elem.get( 'name', '' )
                package_version = elem.get( 'version', '' )
                error_message += 'Version %s of the %s package cannot be installed because ' % \
                    ( str( package_version ), str( package_name ) )
                error_message += 'the recipe for installing the package is missing either an '
                error_message += '&lt;actions&gt; tag set or an &lt;actions_group&gt; tag set.'
            if error_message:
                message += error_message
            if altered:
                if not self.altered:
                    self.altered = True
                if not elem_altered:
                    elem_altered = True
                new_elem[ sub_index ] = new_sub_elem
        return elem_altered, new_elem, message

    def process_package_tag_set( self, elem, message ):
        elem_altered = False
        new_elem = copy.deepcopy( elem )
        for sub_index, sub_elem in enumerate( elem ):
            altered = False
            error_message = ''
            if sub_elem.tag == 'install':
                altered, new_sub_elem, error_message = \
                    self.process_install_tag_set( elem=sub_elem,
                                                  message=message )
            elif sub_elem.tag == 'repository':
                altered, new_sub_elem, error_message = \
                    self.process_repository_tag_set( parent_elem=elem,
                                                     elem_index=sub_index,
                                                     elem=sub_elem,
                                                     message=message )
            if error_message:
                message += error_message
            if altered:
                if not self.altered:
                    self.altered = True
                if not elem_altered:
                    elem_altered = True
                new_elem[ sub_index ] = new_sub_elem
        return elem_altered, new_elem, message

    def process_repository_tag_set( self, parent_elem, elem_index, elem, message ):
        # We have a complex repository dependency.
        altered, new_elem, error_message = self.rdd.handle_complex_dependency_elem( parent_elem=parent_elem,
                                                                                    elem_index=elem_index,
                                                                                    elem=elem )
        if error_message:
            message += error_message
        if altered:
            if not self.altered:
                self.altered = True
        return altered, new_elem, message
