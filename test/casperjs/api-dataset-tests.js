var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test the HDA API', 0, function suite( test ){
    spaceghost.start();

    // =================================================================== SET UP
    var email = spaceghost.user.getRandomEmail(),
        password = '123456';
    if( spaceghost.fixtureData.testUser ){
        email = spaceghost.fixtureData.testUser.email;
        password = spaceghost.fixtureData.testUser.password;
    }

    var detailKeys  = [
            // the following are always present regardless of datatype
            'id', 'name', 'api_type', 'model_class',
            'history_id', 'hid',
            'accessible', 'deleted', 'visible', 'purged',
            'state', 'data_type', 'file_ext', 'file_size',
            'misc_info', 'misc_blurb',
            'download_url', 'visualizations', 'display_apps', 'display_types',
            'genome_build'
        ];

    spaceghost.user.loginOrRegisterUser( email, password );
    spaceghost.openHomePage();
    spaceghost.api.tools.thenUploadToCurrent({ filepath: '../../test-data/1.bed' });

    spaceghost.then( function(){
        // ------------------------------------------------------------------------------------------- INDEX
        this.test.comment( 'index should error with not implemented' );
        this.api.assertRaises( function(){
            this.api.datasets.index();
        }, 501, 'not implemented', 'throws unimplemented' );

        // ------------------------------------------------------------------------------------------- SHOW
        this.test.comment( 'show should get an HDA details object' );
        var history = this.api.histories.show( 'most_recently_used', { keys : 'id,hdas' } ),
            hdaId = history.hdas[0],
            show = this.api.datasets.show( hdaId );
        this.debug( this.jsonStr( history ) );
        this.debug( this.jsonStr( show ) );
        this.test.assert( this.hasKeys( show, detailKeys ), 'Has the proper keys' );

        // ------------------------------------------------------------------------------------------- DISPLAY
        this.test.comment( 'show should get an HDA details object' );
        var fileContents = this.api.datasets.display( history.id, hdaId, { raw: 'True' });
        this.test.assert( fileContents.split( '\n' ).length === 66, '1.bed has 66 lines' );
    });


    // ===================================================================
    spaceghost.run( function(){ test.done(); });
});

