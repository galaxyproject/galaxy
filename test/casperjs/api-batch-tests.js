var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test the API batch system', 0, function suite( test ){
    spaceghost.start();

    // ======================================================================== SET UP
    var email = spaceghost.user.getRandomEmail(),
        password = '123456';
    if( spaceghost.fixtureData.testUser ){
        email = spaceghost.fixtureData.testUser.email;
        password = spaceghost.fixtureData.testUser.password;
    }
    spaceghost.user.registerUser( email, password );

    var responseKeys = [ 'body', 'headers', 'status' ];

    // ======================================================================== TESTS
    spaceghost.then( function(){
        // --------------------------------------------------------------------
        this.test.comment( 'API batching should allow multiple requests and responses, executed in order' );
        var batch = [
                { url : '/api/histories' },
                { url : '/api/histories', type: 'POST', body: JSON.stringify({ name: 'wert' }) },
                { url : '/api/histories' },
            ],
            responses = this.api._ajax( 'api/batch', {
                type        : 'POST',
                contentType : 'application/json',
                data        : { batch : batch }
                // data        : JSON.stringify({ batch : batch })
            });
        this.debug( 'responses:' + this.jsonStr( responses ) );

        this.test.assert( utils.isArray( responses ), "returned an array: length " + responses.length );
        this.test.assert( responses.length === 3, 'Has three responses' );

        var historiesBeforeCreate = responses[0],
            createdHistory = responses[1],
            historiesAfterCreate = responses[2];
        this.test.assert( utils.isArray( historiesBeforeCreate.body ),
            "first histories call returned an array" + historiesBeforeCreate.body.length );
        this.test.assert( utils.isObject( createdHistory.body ), 'history create returned an object' );
        this.test.assert( historiesAfterCreate.body[0].id === createdHistory.body.id,
            "second histories call includes the newly created history:" + historiesAfterCreate.body[0].id );
    /*
    */
    });
    //spaceghost.user.logout();

    // ===================================================================
    spaceghost.run( function(){ test.done(); });
});

