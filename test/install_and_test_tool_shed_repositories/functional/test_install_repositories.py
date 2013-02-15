import new
import install_and_test_tool_shed_repositories.base.test_db_util as test_db_util
from install_and_test_tool_shed_repositories.base.twilltestcase import InstallTestRepository

class TestInstallRepositories( InstallTestRepository ):
    """Abstract test case that installs a predefined list of repositories."""
    def do_installation( self, repository_info_dict ):
        self.logout()
        self.login( email='test@bx.psu.edu', username='test' )
        admin_user = test_db_util.get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
        self.install_repository( repository_info_dict )

def build_tests( repository_dict=None ):
    """Generate abstract test cases for the defined list of repositories."""
    if repository_dict is None:
        return
    # Push all the toolbox tests to module level
    G = globals()
    # Eliminate all previous tests from G.
    for key, val in G.items():
        if key.startswith( 'TestInstallRepository_' ):
            del G[ key ]
    # Create a new subclass with a method named install_repository_XXX that installs the repository specified by the provided dict.
    name = "TestInstallRepository_" + repository_dict[ 'name' ]
    baseclasses = ( TestInstallRepositories, )
    namespace = dict()
    def make_install_method( repository_dict ):
        def test_install_repository( self ):
            self.do_installation( repository_dict )
        return test_install_repository
    test_method = make_install_method( repository_dict )
    test_method.__doc__ = "Install the repository %s from %s." % ( repository_dict[ 'name' ], repository_dict[ 'tool_shed_url' ] )
    namespace[ 'install_repository_%s' % repository_dict[ 'name' ] ] = test_method
    # The new.classobj function returns a new class object, with name name, derived
    # from baseclasses (which should be a tuple of classes) and with namespace dict.
    new_class_obj = new.classobj( name, baseclasses, namespace )
    G[ name ] = new_class_obj
