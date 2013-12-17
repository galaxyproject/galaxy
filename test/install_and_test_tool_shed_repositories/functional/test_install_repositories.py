import logging
import new
import install_and_test_tool_shed_repositories.base.test_db_util as test_db_util
from install_and_test_tool_shed_repositories.base.twilltestcase import InstallTestRepository

log = logging.getLogger(__name__)


class InstallTestRepositories( InstallTestRepository ):
    """Abstract test case that installs and uninstalls a predefined list of repositories."""

    def do_deactivate( self, repository_dict ):
        self.logout()
        self.login( email='test@bx.psu.edu', username='test' )
        admin_user = test_db_util.get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        # Get the repository defined by the received repository_dict along with all of its repository dependencies
        # from the database.
        name = repository_dict[ 'name' ]
        owner = repository_dict[ 'owner' ]
        changeset_revision = repository_dict[ 'changeset_revision' ]
        repository = test_db_util.get_installed_repository_by_name_owner_changeset_revision( name, owner, changeset_revision )
        admin_user_private_role = test_db_util.get_private_role( admin_user )
        # Uninstall the repository through the web interface using twill.
        self.deactivate_repository( repository )

    def do_install( self, repository_dict ):
        self.logout()
        self.login( email='test@bx.psu.edu', username='test' )
        admin_user = test_db_util.get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
        # Install the repository through the web interface using twill.  The install_repository() method may 
        # actually install more than this singe repository because repository dependencies can be installed.
        self.install_repository( repository_dict )

    def do_uninstall( self, repository_dict ):
        self.logout()
        self.login( email='test@bx.psu.edu', username='test' )
        admin_user = test_db_util.get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        # Get the repository defined by the received repository_dict along with all of its repository dependencies
        # from the database.
        name = repository_dict[ 'name' ]
        owner = repository_dict[ 'owner' ]
        changeset_revision = repository_dict[ 'changeset_revision' ]
        repository = test_db_util.get_installed_repository_by_name_owner_changeset_revision( name, owner, changeset_revision )
        admin_user_private_role = test_db_util.get_private_role( admin_user )
        # Uninstall the repository and all of its repository dependencies through the Galaxy web interface using twill.
        self.uninstall_repository( repository )

def generate_deactivate_method( repository_dict=None ):
    """Generate abstract test cases for the received repository_dict."""
    if repository_dict is None:
        return
    # Push all the toolbox tests to module level
    G = globals()
    # Eliminate all previous tests from G.
    for key, val in G.items():
        if key.startswith( 'TestInstallRepository_' ) or key.startswith( 'TestForTool_' ):
            del G[ key ]
    # Create a new subclass with a method named install_repository_XXX that deactivates the
    # repository specified by the received repository_dict.
    name = "TestDeactivateRepository_%s_%s" % \
        ( str( repository_dict[ 'name' ] ), str( repository_dict[ 'changeset_revision' ] ) )
    baseclasses = ( InstallTestRepositories, )
    namespace = dict()
    def make_deactivate_method( repository_dict ):
        def test_deactivate_repository( self ):
            self.do_deactivate( repository_dict )
        return test_deactivate_repository
    test_method = make_deactivate_method( repository_dict )
    test_method.__doc__ = "Deactivate the repository %s." % str( repository_dict[ 'name' ] )
    namespace[ 'uninstall_repository_%s_%s' % ( str( repository_dict[ 'name' ] ),
                                                str( repository_dict[ 'changeset_revision' ] ) ) ] = test_method
    # The new.classobj function returns a new class object, with name name, derived
    # from baseclasses (which should be a tuple of classes) and with namespace dict.
    new_class_obj = new.classobj( str( name ), baseclasses, namespace )
    G[ name ] = new_class_obj

def generate_install_method( repository_dict=None ):
    """Generate abstract test cases for the defined list of repositories."""
    if repository_dict is None:
        return
    # Push all the toolbox tests to module level
    G = globals()
    # Eliminate all previous tests from G.
    for key, val in G.items():
        if key.startswith( 'TestInstallRepository_' ) or key.startswith( 'TestUninstallRepository_' ) or key.startswith( 'TestForTool_' ):
            del G[ key ]
    # Create a new subclass with a method named install_repository_XXX that installs the repository specified by the provided dict.
    name = "TestInstallRepository_" + repository_dict[ 'name' ]
    baseclasses = ( InstallTestRepositories, )
    namespace = dict()
    def make_install_method( repository_dict ):
        def test_install_repository( self ):
            self.do_install( repository_dict )
        return test_install_repository
    test_method = make_install_method( repository_dict )
    test_method.__doc__ = "Install the repository %s from %s." % \
        ( str( repository_dict[ 'name' ] ), str( repository_dict[ 'tool_shed_url' ] ) )
    namespace[ 'install_repository_%s' % str( repository_dict[ 'name' ] ) ] = test_method
    # The new.classobj function returns a new class object with name name derived
    # from baseclasses (which should be a tuple of classes) and with namespace dict.
    new_class_obj = new.classobj( str( name ), baseclasses, namespace )
    G[ name ] = new_class_obj

def generate_uninstall_method( repository_dict=None ):
    """Generate abstract test cases for the received repository_dict."""
    if repository_dict is None:
        return
    # Push all the toolbox tests to module level
    G = globals()
    # Eliminate all previous tests from G.
    for key, val in G.items():
        if key.startswith( 'TestInstallRepository_' ) or key.startswith( 'TestForTool_' ):
            del G[ key ]
    # Create a new subclass with a method named install_repository_XXX that installs the repository
    # specified by the received repository_dict.
    name = "TestUninstallRepository_%s_%s" % \
        ( str( repository_dict[ 'name' ] ), str( repository_dict[ 'changeset_revision' ] ) )
    baseclasses = ( InstallTestRepositories, )
    namespace = dict()
    def make_uninstall_method( repository_dict ):
        def test_uninstall_repository( self ):
            self.do_uninstall( repository_dict )
        return test_uninstall_repository
    test_method = make_uninstall_method( repository_dict )
    test_method.__doc__ = "Uninstall the repository %s." % repository_dict[ 'name' ]
    namespace[ 'uninstall_repository_%s_%s' % ( str( repository_dict[ 'name' ] ),
                                                str( repository_dict[ 'changeset_revision' ] ) ) ] = test_method
    # The new.classobj function returns a new class object, with name name, derived
    # from baseclasses (which should be a tuple of classes) and with namespace dict.
    new_class_obj = new.classobj( str( name ), baseclasses, namespace )
    G[ name ] = new_class_obj
