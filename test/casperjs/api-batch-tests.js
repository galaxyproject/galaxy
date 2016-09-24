var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

function apiBatch( batch ){
    return spaceghost.api._ajax( 'api/batch', {
        type        : 'POST',
        contentType : 'application/json',
        data        : { batch : batch }
    });
}

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
        var responses = apiBatch([
                { url : '/api/histories' },
                { url : '/api/histories', type: 'POST', body: JSON.stringify({ name: 'wert' }) },
                { url : '/api/histories' },
            ]);
        // this.debug( 'responses:' + this.jsonStr( responses ) );
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


        this.test.comment( 'API batching should handle bad routes well' );
        responses = apiBatch([
            { url : '/api/bler' },
        ]);
        // this.debug( 'responses:' + this.jsonStr( responses ) );
        this.test.assert( responses.length === 1 );
        var badRouteResponse = responses[0];
        this.test.assert( badRouteResponse.status === 404 );
        this.test.assert( utils.isObject( badRouteResponse.body )
                       && this.countKeys( badRouteResponse.body ) === 0 );

        this.test.comment( 'API batching should handle errors well' );
        responses = apiBatch([
            { url : '/api/histories/abc123' },
            { url : '/api/users/123', method: 'PUT' }
        ]);
        // this.debug( 'responses:' + this.jsonStr( responses ) );
        this.test.assert( responses.length === 2 );
        var badIdResponse = responses[0],
            notImplemented = responses[1];
        this.test.assert( badIdResponse.status === 400 );
        this.test.assert( notImplemented.status === 501 );

    /*
    */
    });
    //spaceghost.user.logout();

    // ===================================================================
    spaceghost.run( function(){ test.done(); });
});

