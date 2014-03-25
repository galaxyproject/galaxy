/* Utility to load a specific page and output html, page text, or a screenshot
 *  Optionally wait for some time, text, or dom selector
 */
try {
    //...if there's a better way - please let me know, universe
    var scriptDir = require( 'system' ).args[3]
            // remove the script filename
            .replace( /[\w|\.|\-|_]*$/, '' )
            // if given rel. path, prepend the curr dir
            .replace( /^(?!\/)/, './' ),
        spaceghost = require( scriptDir + 'spaceghost' ).create({
            // script options here (can be overridden by CLI)
            //verbose: true,
            //logLevel: debug,
            scriptDir: scriptDir
        });

} catch( error ){
    console.debug( error );
    phantom.exit( 1 );
}
spaceghost.start();


// =================================================================== SET UP
var utils = require( 'utils' );

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
spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){
    // create three histories: make the 2nd importable (via the API), and the third published

    this.test.comment( 'importable, slug, and published should all be returned by show and initially off' );
    // make the current the inaccessible one
    inaccessibleHistory = this.api.histories.show( 'current' );
    this.test.assert( this.hasKeys( inaccessibleHistory, [ 'id', 'name', 'slug', 'importable', 'published' ] ),
        'Has the proper keys' );
    this.test.assert( inaccessibleHistory.slug === null,
        'initial slug is null: ' + inaccessibleHistory.slug );
    this.test.assert( inaccessibleHistory.importable === false,
        'initial importable is false: ' + inaccessibleHistory.importable );
    this.test.assert( inaccessibleHistory.published === false,
        'initial published is false: ' + inaccessibleHistory.published );
    this.api.histories.update( inaccessibleHistory.id, { name: 'inaccessible' });

    this.test.comment( 'Setting importable to true should create a slug, username_and_slug, and importable === true' );
    accessibleHistory = this.api.histories.create({ name: 'accessible' });
    var returned = this.api.histories.update( accessibleHistory.id, {
        importable  : true
    });
    this.debug( this.jsonStr( returned ) );
    accessibleHistory = this.api.histories.show( accessibleHistory.id );
    this.test.assert( this.hasKeys( accessibleHistory, [ 'username_and_slug' ] ),
        'Has the proper keys' );
    this.test.assert( accessibleHistory.slug === 'accessible',
        'slug is not null: ' + accessibleHistory.slug );
    this.test.assert( accessibleHistory.importable,
        'importable is true: ' + accessibleHistory.importable );
    accessibleLink = 'u/' + email.replace( '@test.test', '' ) + '/h/accessible';
    this.test.assert( accessibleHistory.username_and_slug === accessibleLink,
        'username_and_slug is proper: ' + accessibleHistory.username_and_slug );

    this.test.comment( 'Setting published to true should create make accessible and published === true' );
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

//// ------------------------------------------------------------------------------------------- upload some files
spaceghost.then( function(){
    this.api.tools.thenUpload( inaccessibleHistory.id, { filepath: this.options.scriptDir + '/../../test-data/1.bed' });
    this.api.tools.thenUpload(   accessibleHistory.id, { filepath: this.options.scriptDir + '/../../test-data/1.bed' });
    this.api.tools.thenUpload(    publishedHistory.id, { filepath: this.options.scriptDir + '/../../test-data/1.bed' });
});
spaceghost.then( function(){
    // check that they're there
    inaccessibleHdas = this.api.hdas.index( inaccessibleHistory.id ),
      accessibleHdas = this.api.hdas.index(   accessibleHistory.id ),
       publishedHdas = this.api.hdas.index(    publishedHistory.id );
    this.test.assert( inaccessibleHdas.length === 1,
        'uploaded file to inaccessible: ' + inaccessibleHdas.length );
    this.test.assert( accessibleHdas.length === 1,
        'uploaded file to accessible: ' + accessibleHdas.length );
    this.test.assert( publishedHdas.length === 1,
        'uploaded file to published: ' + publishedHdas.length );
});
spaceghost.user.logout();

//// ------------------------------------------------------------------------------------------- log in user2
function ensureInaccessibility( history, hdas ){

    this.test.comment( 'all four CRUD API calls should fail for user2 with history: ' + history.name );
    this.api.assertRaises( function(){
        this.api.histories.show( history.id );
    }, 400, 'History is not accessible to the current user', 'show failed with error' );
    this.api.assertRaises( function(){
        this.api.histories.create({ history_id : history.id });
    }, 403, 'History is not accessible to the current user', 'copy failed with error' );
    this.api.assertRaises( function(){
        this.api.histories.update( history.id, { deleted: true });
    }, 500, 'History is not owned by the current user', 'update failed with error' );
    this.api.assertRaises( function(){
        this.api.histories.delete_( history.id );
    }, 400, 'History is not owned by the current user', 'delete failed with error' );

    this.test.comment( 'all four HDA CRUD API calls should fail for user2 with history: ' + history.name );
    this.api.assertRaises( function(){
        this.api.hdas.index( history.id );
    }, 500, 'History is not accessible to the current user', 'index failed with error' );
    this.api.assertRaises( function(){
        this.api.hdas.show( history.id, hdas[0].id );
    }, 500, 'History is not accessible to the current user', 'show failed with error' );
    this.api.assertRaises( function(){
        this.api.hdas.update( history.id, hdas[0].id, { deleted: true });
    }, 500, 'HistoryDatasetAssociation is not owned by current user', 'update failed with error' );
    this.api.assertRaises( function(){
        this.api.hdas.delete_( history.id, hdas[0].id );
    }, 500, 'HistoryDatasetAssociation is not owned by current user', 'delete failed with error' );

    this.test.comment( 'Attempting to copy an accessible hda (default is accessible)'
                     + 'from an inaccessible history should fail' );
    this.api.assertRaises( function(){
        var returned = this.api.hdas.create( this.api.histories.show( 'current' ).id, {
            source  : 'hda',
            content : hdas[0].id
        });
        this.debug( this.jsonStr( returned ) );
    }, 403, 'History is not accessible to the current user', 'copy failed with error' );

}
spaceghost.user.loginOrRegisterUser( email2, password2 );
spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){

    // ----------------------------------------------------------------------------------------- user2 + inaccessible
    ensureInaccessibility.call( spaceghost, inaccessibleHistory, inaccessibleHdas );
    
    // ----------------------------------------------------------------------------------------- user2 + accessible
    this.test.comment( 'show should work for the importable history' );
    this.test.assert( this.api.histories.show( accessibleHistory.id ).id === accessibleHistory.id,
        'show worked' );

    this.test.comment( 'create/copy should work for the importable history' );
    var returned = this.api.histories.create({ history_id : accessibleHistory.id });
    this.test.assert( returned.name === "Copy of '" + accessibleHistory.name + "'",
        'copied name matches: ' + returned.name );

    this.test.comment( 'update should fail for the importable history' );
    this.api.assertRaises( function(){
        this.api.histories.update( accessibleHistory.id, { deleted: true });
    }, 500, 'History is not owned by the current user', 'update failed with error' );
    this.test.comment( 'delete should fail for the importable history' );
    this.api.assertRaises( function(){
        this.api.histories.delete_( accessibleHistory.id );
    }, 400, 'History is not owned by the current user', 'delete failed with error' );

    this.test.comment( 'indexing should work for the contents of the importable history' );
    this.test.assert( this.api.hdas.index( accessibleHistory.id ).length === 1,
        'index worked' );
    this.test.comment( 'showing should work for the contents of the importable history' );
    this.test.assert( this.api.hdas.show( accessibleHistory.id, accessibleHdas[0].id ).id === accessibleHdas[0].id,
        'show worked' );
    this.test.comment( 'updating should fail for the contents of the importable history' );
    this.api.assertRaises( function(){
        this.api.hdas.update( accessibleHistory.id, accessibleHdas[0].id, { deleted: true });
    }, 500, 'HistoryDatasetAssociation is not owned by current user', 'update failed with error' );
    this.test.comment( 'deleting should fail for the contents of the importable history' );
    this.api.assertRaises( function(){
        this.api.hdas.delete_( accessibleHistory.id, accessibleHdas[0].id );
    }, 500, 'HistoryDatasetAssociation is not owned by current user', 'delete failed with error' );
    this.test.comment( 'copying a dataset from the importable history should work' );
    returned = this.api.hdas.create( this.api.histories.show( 'current' ).id, {
        source  : 'hda',
        content : accessibleHdas[0].id
    });
    this.test.assert( returned.name === accessibleHdas[0].name, 'successful copy from: ' + returned.name );

    this.test.comment( 'copying a dataset into the importable history should fail' );
    this.api.assertRaises( function(){
        this.api.hdas.create( accessibleHistory.id, {
            source  : 'hda',
            // should error before it checks the id
            content : 'bler'
        });
    }, 400, 'History is not owned by the current user', 'copy to failed' );

    //// ----------------------------------------------------------------------------------------- user2 + published
    this.test.comment( 'show should work for the published history' );
    this.test.assert( this.api.histories.show( publishedHistory.id ).id === publishedHistory.id,
        'show worked' );
    this.test.comment( 'create/copy should work for the published history' );
    returned = this.api.histories.create({ history_id : publishedHistory.id });
    this.test.assert( returned.name === "Copy of '" + publishedHistory.name + "'",
        'copied name matches: ' + returned.name );
    this.test.comment( 'update should fail for the published history' );
    this.api.assertRaises( function(){
        this.api.histories.update( publishedHistory.id, { deleted: true });
    }, 500, 'History is not owned by the current user', 'update failed with error' );
    this.test.comment( 'delete should fail for the published history' );
    this.api.assertRaises( function(){
        this.api.histories.delete_( publishedHistory.id );
    }, 400, 'History is not owned by the current user', 'delete failed with error' );

    this.test.comment( 'indexing should work for the contents of the published history' );
    this.test.assert( this.api.hdas.index( publishedHistory.id ).length === 1,
        'index worked' );
    this.test.comment( 'showing should work for the contents of the published history' );
    this.test.assert( this.api.hdas.show( publishedHistory.id, publishedHdas[0].id ).id === publishedHdas[0].id,
        'show worked' );
    this.test.comment( 'updating should fail for the contents of the published history' );
    this.api.assertRaises( function(){
        this.api.hdas.update( publishedHistory.id, publishedHdas[0].id, { deleted: true });
    }, 500, 'HistoryDatasetAssociation is not owned by current user', 'update failed with error' );
    this.test.comment( 'deleting should fail for the contents of the published history' );
    this.api.assertRaises( function(){
        this.api.hdas.delete_( publishedHistory.id, publishedHdas[0].id );
    }, 500, 'HistoryDatasetAssociation is not owned by current user', 'delete failed with error' );

    this.test.comment( 'copying a dataset from the published history should work' );
    returned = this.api.hdas.create( this.api.histories.show( 'current' ).id, {
        source  : 'hda',
        content : publishedHdas[0].id
    });
    this.test.assert( returned.name === publishedHdas[0].name, 'successful copy from: ' + returned.name );

    this.test.comment( 'copying a dataset into the published history should fail' );
    this.api.assertRaises( function(){
        this.api.hdas.create( publishedHistory.id, {
            source  : 'hda',
            // should error before it checks the id
            content : 'bler'
        });
    }, 400, 'History is not owned by the current user', 'copy to failed' );
});
spaceghost.user.logout();


//// ------------------------------------------------------------------------------------------- user1 revoke perms
spaceghost.user.loginOrRegisterUser( email, password );
spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){
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
    ensureInaccessibility.call( spaceghost, accessibleHistory, accessibleHdas );
    ensureInaccessibility.call( spaceghost, publishedHistory, publishedHdas );
});

// ===================================================================
spaceghost.run( function(){
});
