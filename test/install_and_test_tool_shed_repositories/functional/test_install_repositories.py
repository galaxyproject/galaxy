import logging
import new
import install_and_test_tool_shed_repositories.base.test_db_util as test_db_util
from install_and_test_tool_shed_repositories.base.twilltestcase import InstallTestRepository

log = logging.getLogger(__name__)


class InstallTestRepositories( InstallTestRepository ):
    """Abstract test case that installs a predefined list of repositories."""

    def do_install( self, repository_dict ):
        self.logout()
        admin_email = 'test@bx.psu.edu'
        admin_username = 'test'
        self.login( email=admin_email, username=admin_username )
        admin_user = test_db_util.get_user( admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
        # Install the repository through the web interface using twill.  The install_repository() method may 
        # actually install more than this singe repository because repository dependencies can be installed.
        self.install_repository( repository_dict )

def generate_install_method( repository_dict=None ):
    """Generate abstract test cases for the defined list of repositories."""

    def make_install_method( repository_dict ):
        def test_install_repository( self ):
            self.do_install( repository_dict )
        return test_install_repository

    if repository_dict is None:
        return
    # Push all the toolbox tests to module level
    G = globals()
    # Eliminate all previous tests from G.
    for key, val in G.items():
        if key.startswith( 'TestInstallRepository_' ) or key.startswith( 'TestForTool_' ):
            del G[ key ]
    tool_shed = str( repository_dict[ 'tool_shed_url' ] )
    repository_name = str( repository_dict[ 'name' ] )
    repository_owner = str( repository_dict[ 'owner' ] )
    changeset_revision = str( repository_dict[ 'changeset_revision' ] )
    # Create a new subclass with a method named install_repository_XXX that installs the repository defined
    # by the received repository_dict along with all of its dependency hierarchy.
    test_name = "TestInstallRepository_" + repository_name
    baseclasses = ( InstallTestRepositories, )
    namespace = dict()
    test_method = make_install_method( repository_dict )
    test_method.__doc__ = "Installing revision %s of repository %s owned by %s from tool shed %s." % \
        ( changeset_revision, repository_name, repository_owner, tool_shed )
    namespace[ 'install_repository_%s' % repository_name ] = test_method
    # The new.classobj function returns a new class object with name name derived
    # from baseclasses (which should be a tuple of classes) and with namespace dict.
    new_class_obj = new.classobj( str( test_name ), baseclasses, namespace )
    G[ test_name ] = new_class_obj
