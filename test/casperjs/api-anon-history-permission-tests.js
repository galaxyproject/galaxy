var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test permissions for accessible, published, and inaccessible histories '
                        + 'with anonymous users over the API', 0, function suite( test ){
    spaceghost.start();

    // =================================================================== SET UP
    var email = spaceghost.user.getRandomEmail(),
        password = '123456';
    if( spaceghost.fixtureData.testUser ){
        email = spaceghost.fixtureData.testUser.email;
        password = spaceghost.fixtureData.testUser.password;
    }
    var inaccessibleHistory, accessibleHistory, publishedHistory,
        inaccessibleHdas, accessibleHdas, publishedHdas;

    //// ------------------------------------------------------------------------------------------- create 3 histories
    spaceghost.user.loginOrRegisterUser( email, password );
    spaceghost.openHomePage().then( function(){
        // create three histories: make the 2nd importable (via the API), and the third published

        // make the current the inaccessible one
        inaccessibleHistory = this.api.histories.index()[0];
        this.api.histories.update( inaccessibleHistory.id, { name: 'inaccessible' });
        inaccessibleHistory = this.api.histories.index()[0];

        accessibleHistory = this.api.histories.create({ name: 'accessible' });
        var returned = this.api.histories.update( accessibleHistory.id, {
            importable  : true
        });
        //this.debug( this.jsonStr( returned ) );
        accessibleHistory = this.api.histories.show( accessibleHistory.id );

        publishedHistory =  this.api.histories.create({ name: 'published' });
        returned = this.api.histories.update( publishedHistory.id, {
            published  : true
        });
        //this.debug( this.jsonStr( returned ) );
        publishedHistory = this.api.histories.show( publishedHistory.id );

    });

    //// ------------------------------------------------------------------------------------------- upload some files
    spaceghost.then( function(){
        this.api.tools.thenUpload( inaccessibleHistory.id, { filepath: '../../test-data/1.bed' });
        this.api.tools.thenUpload(   accessibleHistory.id, { filepath: '../../test-data/1.bed' });
        this.api.tools.thenUpload(    publishedHistory.id, { filepath: '../../test-data/1.bed' });
    });
    spaceghost.then( function(){
        // check that they're there
        inaccessibleHdas = this.api.hdas.index( inaccessibleHistory.id ),
          accessibleHdas = this.api.hdas.index(   accessibleHistory.id ),
           publishedHdas = this.api.hdas.index(    publishedHistory.id );
    });
    spaceghost.user.logout();

    // =================================================================== TESTS
    //// ------------------------------------------------------------------------------------------- anon user
    function testAnonReadFunctionsOnAccessible( history, hdas ){
        this.test.comment( '---- testing read/accessibility functions for ACCESSIBLE history: ' + history.name );

        // read functions for history
        this.test.comment( 'show should work for history: ' + history.name );
        this.test.assert( this.api.histories.show( history.id ).id === history.id,
            'show worked' );

        this.test.comment( 'copying should work for history (replacing the original history): ' + history.name );
        var copiedHistory = this.api.histories.create({ history_id : history.id });
        var historiesIndex = this.api.histories.index();
        this.test.assert( historiesIndex.length === 1, 'only one history after copy' );
        this.test.assert( historiesIndex[0].id === copiedHistory.id, 'original history with copy' );

        // read functions for history contents
        this.test.comment( 'index of history contents should work for history: ' + history.name );
        this.test.assert( this.api.hdas.index( history.id ).length === 1,
            'hda index worked' );
        this.test.comment( 'showing of history contents should work for history: ' + history.name );
        this.test.assert( this.api.hdas.show( history.id, hdas[0].id ).id === hdas[0].id,
            'hda show worked' );

        this.test.comment( 'Attempting to copy an accessible hda (default is accessible)'
                         + ' should work from accessible history: ' + history.name );
        this.api.hdas.create( this.api.histories.index()[0].id, {
            source  : 'hda',
            content : hdas[0].id
        });
    }

    function testAnonReadFunctionsOnInaccessible( history, hdas ){
        this.test.comment( '---- testing read/accessibility functions for INACCESSIBLE history: ' + history.name );

        // read functions for history
        this.test.comment( 'show should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.histories.show( history.id );
        }, 403, 'History is not accessible by user', 'show failed with error' );
        this.test.comment( 'copying should fail for history (implicit multiple histories): ' + history.name );
        this.api.assertRaises( function(){
            this.api.histories.create({ history_id : history.id });
        }, 403, 'History is not accessible by user', 'copy failed with error' );

        // read functions for history contents
        this.test.comment( 'index and show of history contents should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.hdas.index( history.id );
        }, 403, 'History is not accessible by user', 'hda index failed with error' );
        // 150721: accessible hdas in an inaccessible history are considered accessible (since api/datasets does)
        // this.api.assertRaises( function(){
        //     this.api.hdas.show( history.id, hdas[0].id );
        // }, 403, 'History is not accessible by user', 'hda show failed with error' );
        this.test.assertTrue( utils.isObject( this.api.hdas.show( history.id, hdas[0].id ) ) );

        this.test.comment( 'Attempting to copy an accessible hda (default is accessible)'
                         + ' from an inaccessible history should fail for: ' + history.name );
        this.api.assertRaises( function(){
            var returned = this.api.hdas.create( this.api.histories.index()[0].id, {
                source  : 'hda',
                content : hdas[0].id
            });
            this.debug( this.jsonStr( returned ) );
        }, 403, 'History is not accessible by user', 'hda copy from failed with error' );

    }

    function testAnonWriteFunctions( history, hdas ){
        this.test.comment( '---- testing write/ownership functions for history: ' + history.name );

        this.test.comment( 'update should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.histories.update( history.id, { deleted: true });
        }, 403, 'API authentication required for this request', 'update authentication required' );
        this.test.comment( 'delete should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.histories.delete_( history.id );
        }, 403, 'API authentication required for this request', 'delete authentication required' );

        this.test.comment( 'hda updating should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.hdas.update( history.id, hdas[0].id, { deleted: true });
        // anon hda update fails w/ this msg if trying to update non-current history hda
        }, 403, 'API authentication required for this request', 'hda update failed with error' );
        this.test.comment( 'hda deletion should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.hdas.delete_( history.id, hdas[0].id );
        }, 403, 'API authentication required for this request', 'hda delete failed with error' );

        this.test.comment( 'copying hda into history should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.hdas.create( history.id, {
                source  : 'hda',
                // should error before it checks the id
                content : 'bler'
            });
        }, 403, 'History is not owned by user', 'hda copy to failed' );
    }

    function testAnonInaccessible( history, hdas ){
        testAnonReadFunctionsOnInaccessible.call( this, history, hdas );
        testAnonWriteFunctions.call( this, history, hdas );
    }

    function testAnonAccessible( history, hdas ){
        testAnonReadFunctionsOnAccessible.call( this, history, hdas );
        testAnonWriteFunctions.call( this, history, hdas );
    }

    spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){
        testAnonInaccessible.call( spaceghost, inaccessibleHistory, inaccessibleHdas );
        testAnonAccessible.call( spaceghost, accessibleHistory, accessibleHdas );
        testAnonAccessible.call( spaceghost, publishedHistory, publishedHdas );
    });


    // ------------------------------------------------------------------------------------------- user1 revoke perms
    spaceghost.user.loginOrRegisterUser( email, password );
    spaceghost.openHomePage().then( function(){
        this.test.comment( 'revoking perms should prevent access' );
        this.api.histories.update( accessibleHistory.id, {
            importable : false
        });
        var returned = this.api.histories.show( accessibleHistory.id );

        this.api.histories.update( publishedHistory.id, {
            importable : false,
            published  : false
        });
        returned = this.api.histories.show( publishedHistory.id );
    });
    spaceghost.user.logout();


    // ------------------------------------------------------------------------------------------- anon retry perms
    spaceghost.openHomePage().then( function(){
        testAnonInaccessible.call( spaceghost, accessibleHistory, accessibleHdas );
        testAnonInaccessible.call( spaceghost, publishedHistory, publishedHdas );
    });


    // ===================================================================
    spaceghost.run( function(){ test.done(); });
});
