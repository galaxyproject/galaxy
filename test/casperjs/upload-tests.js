var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test uploading data to a history', 0, function suite( test ){
    spaceghost.start();
    // ===================================================================

    var email = spaceghost.user.getRandomEmail(),
        password = '123456';
    if( spaceghost.fixtureData.testUser ){
        email = spaceghost.fixtureData.testUser.email;
        password = spaceghost.fixtureData.testUser.password;
    }

    // ------------------------------------------------------------------- start a new user
    spaceghost.user.loginOrRegisterUser( email, password ).openHomePage( function(){
        var loggedInAs = spaceghost.user.loggedInAs();
        this.test.assert( loggedInAs === email, 'loggedInAs() matches email: "' + loggedInAs + '"' );
    });

    spaceghost.api.tools.thenUploadToCurrent({ filepath: '../../test-data/1.sam' }, function( uploadedId, json ){
        var currentHistoryId = this.api.histories.index()[0].id,
            contents = this.api.hdas.index( currentHistoryId );
        this.test.assert( contents.length === 1, 'found one hda in history' );
        this.test.assert( contents[0].id === uploadedId, 'id matches' );
        this.test.assert( contents[0].name === '1.sam', 'name matches' );
    });
    spaceghost.user.logout();

    // ------------------------------------------------------------------- anon user
    spaceghost.openHomePage();
    spaceghost.api.tools.thenUploadToCurrent({ filepath: '../../test-data/1.bed' }, function( uploadedId, json ){
        var currentHistoryId = this.api.histories.index()[0].id,
            contents = this.api.hdas.index( currentHistoryId );
        this.test.assert( contents.length === 1, 'found one hda in history' );
        this.test.assert( contents[0].id === uploadedId, 'id matches' );
        this.test.assert( contents[0].name === '1.bed', 'name matches' );
    });

    // ===================================================================
    spaceghost.run( function(){ test.done(); });
});
