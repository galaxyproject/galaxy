var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test permissions for accessible, published, and inaccessible histories '
                        + 'over the API', 0, function suite( test ){
    spaceghost.start();

    // =================================================================== SET UP
    var email = spaceghost.user.getRandomEmail(),
        password = '123456';
    if( spaceghost.fixtureData.testUser ){
        email = spaceghost.fixtureData.testUser.email;
        password = spaceghost.fixtureData.testUser.password;
    }
    var email2 = spaceghost.user.getRandomEmail(),
        password2 = '123456';
    if( spaceghost.fixtureData.testUser2 ){
        email2 = spaceghost.fixtureData.testUser2.email;
        password2 = spaceghost.fixtureData.testUser2.password;
    }

    var inaccessibleHistory, accessibleHistory, publishedHistory,
        inaccessibleHdas, accessibleHdas, publishedHdas,
        accessibleLink;

    // =================================================================== TESTS
    //// ------------------------------------------------------------------------------------------- create 3 histories
    spaceghost.user.loginOrRegisterUser( email, password );
    spaceghost.openHomePage().then( function(){
        this.test.comment( '(logged in as ' + this.user.loggedInAs() + ')' );
        // create three histories: make the 2nd importable (via the API), and the third published

        this.test.comment( 'importable, slug, and published should all be returned by show and initially off' );
        // make the current the inaccessible one
        inaccessibleHistory = this.api.histories.show( this.api.histories.index()[0].id );
        this.test.assert( this.hasKeys( inaccessibleHistory, [ 'id', 'name', 'slug', 'importable', 'published' ] ),
            'Has the proper keys' );
        this.test.assert( inaccessibleHistory.slug === null,
            'initial slug is null: ' + inaccessibleHistory.slug );
        this.test.assert( inaccessibleHistory.importable === false,
            'initial importable is false: ' + inaccessibleHistory.importable );
        this.test.assert( inaccessibleHistory.published === false,
            'initial published is false: ' + inaccessibleHistory.published );
        this.api.histories.update( inaccessibleHistory.id, { name: 'inaccessible' });
        inaccessibleHistory = this.api.histories.show( inaccessibleHistory.id );

        this.test.comment( 'Setting importable to true should create a slug, ' +
                           'username_and_slug, and importable === true' );
        accessibleHistory = this.api.histories.create({ name: 'accessible' });
        var returned = this.api.histories.update( accessibleHistory.id, {
            importable  : true
        });
        this.debug( this.jsonStr( returned ) );
        accessibleHistory = this.api.histories.show( accessibleHistory.id );
        this.test.assert( this.hasKeys( accessibleHistory, [ 'username_and_slug' ] ),
            'Has username_and_slug' );
        this.test.assert( accessibleHistory.slug === 'accessible',
            'slug is not null: ' + accessibleHistory.slug );
        this.test.assert( accessibleHistory.importable,
            'importable is true: ' + accessibleHistory.importable );
        accessibleLink = 'u/' + email.replace( '@test.test', '' ) + '/h/accessible';
        this.test.assert( accessibleHistory.username_and_slug === accessibleLink,
            'username_and_slug is proper: ' + accessibleHistory.username_and_slug );

        this.test.comment( 'Setting published to true should make accessible and published === true' );
        publishedHistory =  this.api.histories.create({ name: 'published' });
        returned = this.api.histories.update( publishedHistory.id, {
            published  : true
        });
        this.debug( this.jsonStr( returned ) );
        publishedHistory = this.api.histories.show( publishedHistory.id );
        this.test.assert( this.hasKeys( publishedHistory, [ 'username_and_slug' ] ),
            'Has the proper keys' );
        this.test.assert( publishedHistory.published,
            'published is true: ' + publishedHistory.published );
        this.test.assert( publishedHistory.importable,
            'importable is true: ' + publishedHistory.importable );
        this.test.assert( publishedHistory.slug === 'published',
            'slug is not null: ' + publishedHistory.slug );
        accessibleLink = 'u/' + email.replace( '@test.test', '' ) + '/h/published';
        this.test.assert( publishedHistory.username_and_slug === accessibleLink,
            'username_and_slug is proper: ' + publishedHistory.username_and_slug );

    });

    // ------------------------------------------------------------------------------------------- upload some files
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
        this.test.comment( '---- adding datasets' );
        this.test.assert( inaccessibleHdas.length === 1,
            'uploaded file to inaccessible: ' + inaccessibleHdas.length );
        this.test.assert( accessibleHdas.length === 1,
            'uploaded file to accessible: ' + accessibleHdas.length );
        this.test.assert( publishedHdas.length === 1,
            'uploaded file to published: ' + publishedHdas.length );
    });
    spaceghost.user.logout();

    //// ------------------------------------------------------------------------------------------- log in user2
    function testReadFunctionsOnAccessible( history, hdas ){
        this.test.comment( '---- testing read/accessibility functions for ACCESSIBLE history: ' + history.name );

        // read functions for history
        this.test.comment( 'show should work for history: ' + history.name );
        this.test.assert( this.api.histories.show( history.id ).id === history.id,
            'show worked' );
        this.test.comment( 'copying should work for history: ' + history.name );
        var returned = this.api.histories.create({ history_id : history.id });
        this.test.assert( returned.name === "Copy of '" + history.name + "'",
            'copied name matches: ' + returned.name );

        // read functions for history contents
        this.test.comment( 'index of history contents should work for history: ' + history.name );
        this.test.assert( this.api.hdas.index( history.id ).length === 1,
            'hda index worked' );
        this.test.comment( 'showing of history contents should work for history: ' + history.name );
        this.test.assert( this.api.hdas.show( history.id, hdas[0].id ).id === hdas[0].id,
            'hda show worked' );

        this.test.comment( 'Attempting to copy an accessible hda (default is accessible)'
                         + ' should work from accessible history: ' + history.name );
        returned = this.api.hdas.create( this.api.histories.index()[0].id, {
            source  : 'hda',
            content : hdas[0].id
        });
        this.test.assert( returned.name === hdas[0].name, 'successful hda copy from: ' + returned.name );
    }

    function testReadFunctionsOnInaccessible( history, hdas ){
        this.test.comment( '---- testing read/accessibility functions for INACCESSIBLE history: ' + history.name );

        // read functions for history
        this.test.comment( 'show should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.histories.show( history.id );
        }, 403, 'History is not accessible by user', 'show failed with error' );
        this.test.comment( 'copying should fail for history: ' + history.name );
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

    function testWriteFunctions( history, hdas ){
        this.test.comment( '---- testing write/ownership functions for history: ' + history.name );

        this.test.comment( 'update should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.histories.update( history.id, { deleted: true });
        }, 403, 'History is not owned by user', 'update failed with error' );
        this.test.comment( 'delete should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.histories.delete_( history.id );
        }, 403, 'History is not owned by user', 'delete failed with error' );

        this.test.comment( 'hda updating should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.hdas.update( history.id, hdas[0].id, { deleted: true });
        }, 403, 'HistoryDatasetAssociation is not owned by user', 'hda update failed with error' );
        this.test.comment( 'hda deletion should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.hdas.delete_( history.id, hdas[0].id );
        }, 403, 'HistoryDatasetAssociation is not owned by user', 'hda delete failed with error' );

        this.test.comment( 'copying hda into history should fail for history: ' + history.name );
        this.api.assertRaises( function(){
            this.api.hdas.create( history.id, {
                source  : 'hda',
                // should error before it checks the id
                content : 'bler'
            });
        }, 403, 'History is not owned by user', 'hda copy to failed' );
    }

    function testInaccessible( history, hdas ){
        testReadFunctionsOnInaccessible.call( this, history, hdas );
        testWriteFunctions.call( this, history, hdas );
    }

    function testAccessible( history, hdas ){
        testReadFunctionsOnAccessible.call( this, history, hdas );
        testWriteFunctions.call( this, history, hdas );
    }

    spaceghost.user.loginOrRegisterUser( email2, password2 );
    spaceghost.openHomePage().then( function(){
        this.test.comment( '(logged in as ' + this.user.loggedInAs() + ')' );
        testInaccessible.call( spaceghost, inaccessibleHistory, inaccessibleHdas );
        testAccessible.call( spaceghost, accessibleHistory, accessibleHdas );
        testAccessible.call( spaceghost, publishedHistory, publishedHdas );
    });
    spaceghost.user.logout();


    //// ------------------------------------------------------------------------------------------- user1 revoke perms
    spaceghost.user.loginOrRegisterUser( email, password );
    spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){
        this.test.comment( '(logged in as ' + this.user.loggedInAs() + ')' );
        this.test.comment( 'revoking perms should prevent access' );
        this.api.histories.update( accessibleHistory.id, {
            importable : false
        });
        var returned = this.api.histories.show( accessibleHistory.id );
        this.test.assert( !returned.importable, 'now not importable' );
        this.test.assert( !returned.published, '(still not published)' );
        this.test.assert( !!returned.slug, '(slug still set) ' + returned.slug );

        this.api.histories.update( publishedHistory.id, {
            importable : false,
            published  : false
        });
        returned = this.api.histories.show( publishedHistory.id );
        this.test.assert( !returned.importable, 'now not importable' );
        this.test.assert( !returned.published, 'now not published' );
        this.test.assert( !!returned.slug, '(slug still set) ' + returned.slug );
    });
    spaceghost.user.logout();


    //// ------------------------------------------------------------------------------------------- user2 retry perms
    spaceghost.user.loginOrRegisterUser( email2, password2 );
    spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){
        this.test.comment( '(logged in as ' + this.user.loggedInAs() + ')' );
        testInaccessible.call( spaceghost, accessibleHistory, accessibleHdas );
        testInaccessible.call( spaceghost, publishedHistory, publishedHdas );
    });
    // spaceghost.user.logout();


    // ===================================================================
    spaceghost.run( function(){ test.done(); });
});
