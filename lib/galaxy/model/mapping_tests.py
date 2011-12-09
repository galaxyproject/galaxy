import unittest
import galaxy.model.mapping as mapping
from galaxy.model import directory_hash_id
import os.path

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
        model.session.add_all( ( u, h1, h2 ) )
        #q1 = model.Query( "h2->q1" )
        d1 = model.HistoryDatasetAssociation( extension="interval", metadata=dict(chromCol=1,startCol=2,endCol=3 ), history=h2, create_dataset=True, sa_session=model.session )
        #h2.queries.append( q1 )
        #h2.queries.append( model.Query( "h2->q2" ) )
        model.session.add( ( d1 ) )
        model.session.flush()
        model.session.expunge_all()
        # Check
        users = model.session.query( model.User ).all()
        assert len( users ) == 1
        assert users[0].email == "james@foo.bar.baz"
        assert users[0].password == "password"
        assert len( users[0].histories ) == 1
        assert users[0].histories[0].name == "History 1"    
        hists = model.session.query( model.History ).all()
        assert hists[0].name == "History 1"
        assert hists[1].name == ( "H" * 255 )
        assert hists[0].user == users[0]
        assert hists[1].user is None
        assert hists[1].datasets[0].metadata.chromCol == 1
        # The filename test has moved to objecstore
        #id = hists[1].datasets[0].id
        #assert hists[1].datasets[0].file_name == os.path.join( "/tmp", *directory_hash_id( id ) ) + ( "/dataset_%d.dat" % id )
        # Do an update and check
        hists[1].name = "History 2b"
        model.session.flush()
        model.session.expunge_all()
        hists = model.session.query( model.History ).all()
        assert hists[0].name == "History 1"
        assert hists[1].name == "History 2b"
        # gvk TODO need to ad test for GalaxySessions, but not yet sure what they should look like.
        
def get_suite():
    suite = unittest.TestSuite()
    suite.addTest( MappingTests( "test_basic" ) )
    return suite
