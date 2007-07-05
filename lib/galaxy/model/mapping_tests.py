import unittest
import galaxy.model.mapping as mapping

class MappingTests( unittest.TestCase ):
    def test_basic( self ):
        # Start the database and connect the mapping
        model = mapping.init( "/tmp", "sqlite:///:memory:", create_tables=True )
        assert model.engine is not None
        # Make some changes and commit them
        u = model.User( email="james@foo.bar.baz", password="password" )
        # gs = model.GalaxySession()
        h1 = model.History( name="History 1", user=u)
        #h1.queries.append( model.Query( "h1->q1" ) )
        #h1.queries.append( model.Query( "h1->q2" ) )
        h2 = model.History( name=( "H" * 1024 ) )
        #q1 = model.Query( "h2->q1" )
        d1 = model.Dataset( metadata=dict(chromCol=1,startCol=2,endCol=3 ), history=h2 )
        #h2.queries.append( q1 )
        #h2.queries.append( model.Query( "h2->q2" ) )
        model.context.current.flush()
        model.context.current.clear()
        # Check
        users = model.User.select()
        assert len( users ) == 1
        assert users[0].email == "james@foo.bar.baz"
        assert users[0].password == "password"
        assert len( users[0].histories ) == 1
        assert users[0].histories[0].name == "History 1"    
        hists = model.History.select()
        assert hists[0].name == "History 1"
        assert hists[1].name == ( "H" * 255 )
        assert hists[0].user == users[0]
        assert hists[1].user is None
        assert hists[1].datasets[0].metadata.chromCol == 1
        assert hists[1].datasets[0].file_name == "/tmp/dataset_%d.dat" % hists[1].datasets[0].id
        # Do an update and check
        hists[1].name = "History 2b"
        model.context.current.flush()
        model.context.current.clear()
        hists = model.History.select()
        assert hists[0].name == "History 1"
        assert hists[1].name == "History 2b"
        # gvk TODO need to ad test for GalaxySessions, but not yet sure what they should look like.
        
def get_suite():
    suite = unittest.TestSuite()
    suite.addTest( MappingTests( "test_basic" ) )
    return suite
