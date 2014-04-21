var require = patchRequire( require ),
    spaceghost = require( 'spaceghost' ).fromCasper( casper ),
    xpath = require( 'casper' ).selectXPath,
    utils = require( 'utils' ),
    format = utils.format;

spaceghost.test.begin( 'Test the visualizations API', 0, function suite( test ){
    spaceghost.start();

// =================================================================== SET UP
var email = spaceghost.user.getRandomEmail(),
    password = '123456';
if( spaceghost.fixtureData.testUser ){
    email = spaceghost.fixtureData.testUser.email;
    password = spaceghost.fixtureData.testUser.password;
}
spaceghost.user.loginOrRegisterUser( email, password );

// =================================================================== TESTS
spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){
    var ALWAYS_CREATE = true,
        indexKeys = [
            'id', 'title', 'type', 'dbkey', 'url'
        ],
        showKeys  = indexKeys.concat([
            'user_id', 'model_class', 'revisions', 'latest_revision', 'annotation'
        ]),
        revisionKeys = [
            'id', 'title', 'visualization_id', 'dbkey', 'model_class', 'config'
        ];

    // ------------------------------------------------------------------------------------------- set up
    var visualizationIndex = this.api.visualizations.index();
    if( ALWAYS_CREATE || !visualizationIndex.length ){
        // post a visualization
        this.info( 'creating new visualization for tests' );
        var testVisualization = this.api.visualizations.create({
            title   : 'Test Visualization',
            // needs to be unique
            slug    : 'test-visualization-' + Date.now(),
            type    : 'test',
            dbkey   : 'hg17',
            annotation : 'this is a test of the emergency visualization system',
            config  : {
                x       : 10,
                y       : 12
            }
        });
        this.debug( this.jsonStr( testVisualization ) );
    }

    // ------------------------------------------------------------------------------------------- INDEX
    this.test.comment( 'index should get a list of visualizations' );
    visualizationIndex = this.api.visualizations.index();
    this.debug( this.jsonStr( visualizationIndex ) );
    this.test.assert( utils.isArray( visualizationIndex ),
        "index returned an array: length " + visualizationIndex.length );
    this.test.assert( visualizationIndex.length >= 1, 'Has at least one visualization' );

    var firstVisualization = visualizationIndex[0];
    this.test.assert( this.hasKeys( firstVisualization, indexKeys ), 'Has the proper keys' );
    this.test.assert( this.api.isEncodedId( firstVisualization.id ), 'Id appears well-formed' );

    //TODO: index searching
    //TODO: anon user
    //TODO: admin user

    // ------------------------------------------------------------------------------------------- SHOW
    this.test.comment( 'show should get a visualization details object' );
    var visualizationShow = this.api.visualizations.show( firstVisualization.id );
    this.debug( this.jsonStr( visualizationShow ) );
    this.test.assert( this.hasKeys( visualizationShow, showKeys ), 'Has the proper keys' );
    this.test.assert( visualizationShow.model_class === 'Visualization',
        'Has the proper model_class: ' + visualizationShow.model_class );

    this.test.comment( 'a visualization details object should contain an array of revision ids' );
    var revisions = visualizationShow.revisions;
    this.test.assert( utils.isArray( revisions ), 'revisions is an array' );
    this.test.assert( revisions.length >= 1, 'revisions has at least one entry' );
    var areIds = true;
    revisions.forEach( function( revision ){
        if( !spaceghost.api.isEncodedId( revision ) ){ areIds = false; }
    });
    this.test.assert( areIds, 'all revisions are ids' );

    this.test.comment( 'a visualization details object should contain a subobject of the latest revision' );
    var latestRevision = visualizationShow.latest_revision;
    this.test.assert( utils.isObject( latestRevision ), 'latestRevision is an object' );
    this.test.assert( this.hasKeys( latestRevision, revisionKeys ), 'latestRevision has the proper keys' );
    this.test.assert( latestRevision.model_class === 'VisualizationRevision',
        'Has the proper model_class: ' + latestRevision.model_class );
    this.test.assert( latestRevision.visualization_id === visualizationShow.id,
        'revision visualization_id matches containing visualization id: ' + latestRevision.visualization_id );
    this.test.assert( visualizationShow.revisions.indexOf( latestRevision.id ) !== -1,
        'found latest_revision id in revisions' );

    this.test.comment( 'a visualization revision should contain a subobject for the config' );
    var config = latestRevision.config;
    this.test.assert( utils.isObject( config ), 'config is an object:\n' + this.jsonStr( config ) );

    //TODO: url in visualizationIndex == show url
    //TODO: non existing id throws error
    //TODO: anon user
    //TODO: user1 has no permissions to show user2

    // ------------------------------------------------------------------------------------------- CREATE
    this.test.comment( 'Calling create should create a new visualization and allow setting the name' );
    var visualizationData = {
        title   : 'Created Visualization',
        // needs to be unique
        slug    : 'created-visualization-' + Date.now(),
        type    : 'test',
        dbkey   : 'hg17',
        annotation : 'invisible visualization',
        config  : {
            x       : 10,
            y       : 12
        }
    };
    var created = this.api.visualizations.create( visualizationData );
    this.debug( 'returned from create:\n' + this.jsonStr( created ) );
    this.test.assert( this.api.isEncodedId( created.id ), "create returned an id: " + created.id );

    // check v. show
    visualizationShow = this.api.visualizations.show( created.id );
    this.debug( 'visualizationShow:\n' + this.jsonStr( visualizationShow ) );
    // config is re-located into a revision and won't be there
    //this.test.assert( compareObjs( visualizationShow, visualizationData, [ 'config' ] ),
    //    "show results seem to match create data" );

    // the following errors are produced within base.controller.UsesVisualizationsMixin._create_visualization
    this.test.comment( 'Calling create with a non-unique slug will cause an API error' );
    this.api.assertRaises( function(){
        created = this.api.visualizations.create( visualizationData );
    }, 400, 'visualization identifier must be unique' );

    this.test.comment( 'Calling create with no title will cause an API error' );
    visualizationData.title = '';
    this.api.assertRaises( function(){
        created = this.api.visualizations.create( visualizationData );
    }, 400, 'visualization name is required' );
    visualizationData.title = 'Created Visualization';

    this.test.comment( 'Calling create with improper characters in the slug will cause an API error' );
    var oldSlug = visualizationData.slug;
    visualizationData.slug = '123_()';
    this.api.assertRaises( function(){
        created = this.api.visualizations.create( visualizationData );
    }, 400, "visualization identifier must consist of only lowercase letters, numbers, and the '-' character" );
    visualizationData.slug = oldSlug;

    this.test.comment( 'Calling create with an unrecognized key will cause an API error' );
    visualizationData.bler = 'blah';
    this.api.assertRaises( function(){
        created = this.api.visualizations.create( visualizationData );
    }, 400, 'unknown key: bler' );
    delete visualizationData.bler;

    this.test.comment( 'Calling create with an unparsable JSON config will cause an API error' );
    visualizationData.config = '3 = nime';
    this.api.assertRaises( function(){
        created = this.api.visualizations.create( visualizationData );
    }, 400, 'config must be a dictionary (JSON)' );

    // ------------------------------------------------------------------------------------------ UPDATE
    // ........................................................................................... idiot proofing
    this.test.comment( 'updating using a nonsense key should fail with an error' );
    this.api.assertRaises( function(){
        returned = this.api.visualizations.update( created.id, { bler : 'blah' });
    }, 400, 'unknown key: bler' );

    this.test.comment( 'updating by attempting to change type should cause an error' );
    this.api.assertRaises( function(){
        returned = this.api.visualizations.update( created.id, { title : 30 });
    }, 400, 'title must be a string or unicode' );
    //TODO: the other types...

    // ........................................................................................... title
    //this.test.comment( 'update should create a new visualization revision' );
    //
    //this.test.comment( 'updating with a new title should NOT change the visualization title...' );
    //latestRevision = this.api.visualizations.show( created.id ).latest_revision;
    //returned = this.api.visualizations.update( created.id, {
    //    title : 'New title'
    //});
    //visualizationShow = this.api.visualizations.show( created.id );
    //this.debug( this.jsonStr( visualizationShow ) );
    //this.test.assert( visualizationShow.title === visualizationData.title,
    //    "Title does not set via update: " + visualizationShow.title );

});

// ===================================================================
    spaceghost.run( function(){ test.done(); });
});
