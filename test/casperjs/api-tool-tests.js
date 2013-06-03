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
spaceghost.user.loginOrRegisterUser( email, password );

function hasKeys( object, keysArray ){
    if( !utils.isObject( object ) ){ return false; }
    for( var i=0; i<keysArray.length; i += 1 ){
        if( !object.hasOwnProperty( keysArray[i] ) ){
            spaceghost.debug( 'key not found: ' + keysArray[i] );
            return false;
        }
    }
    return true;
}

function compareObjs( obj1, where ){
    for( var key in where ){
        if( where.hasOwnProperty( key ) ){
            if( !obj1.hasOwnProperty( key )  ){ return false; }
            if( obj1[ key ] !== where[ key ] ){ return false; }
        }
    }
    return true;
}

function findObject( objectArray, where, start ){
    start = start || 0;
    for( var i=start; i<objectArray.length; i += 1 ){
        if( compareObjs( objectArray[i], where ) ){ return objectArray[i]; }
    }
    return null;
}

// =================================================================== TESTS
var panelSectionKeys = [
        'elems', 'id', 'name', 'type', 'version'
    ],
    panelToolKeys = [
        'id', 'name', 'description', 'version', 'link', 'target', 'min_width', 'type'
    ],
    toolSummaryKeys = [
        'id', 'name', 'description', 'version'
    ],
    toolDetailKeys = [
        'id', 'name', 'description', 'version', 'inputs'
    ],
    toolInputKeys = [
        'html', 'label', 'name', 'type'
        // there are others, but it's not consistent across all inputs
    ];

function attemptShowOnAllTools(){
    //NOTE: execute like: attemptShowOnAllTools.call( spaceghost )
    toolIndex = this.api.tools.index( false );
    var toolErrors = {};
    function ObjectKeySet(){
        var self = this;
        function addOne( key ){
            if( !self.hasOwnProperty( key ) ){
                self[ key ] = true;
            }
        }
        self.__add = function( obj ){
            for( var key in obj ){
                if( obj.hasOwnProperty( key ) ){
                    addOne( key );
                }
            }
        };
        return self;
    }
    var set = new ObjectKeySet();
    for( i=0; i<toolIndex.length; i+=1 ){
        var tool = toolIndex[i];
        try {
            toolShow = this.api.tools.show( tool.id );
            this.info( 'checking: ' + tool.id );
            for( var j=0; j<toolShow.inputs.length; j+=1 ){
                var input = toolShow.inputs[j];
                set.__add( input );
            }
        } catch( err ){
            var message = JSON.parse( err.message ).error;
            this.error( '\t error: ' + message );
            toolErrors[ tool.id ] = message;
        }
    }
    this.debug( this.jsonStr( toolErrors ) );
    this.debug( this.jsonStr( set ) );
}

spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){

    // ------------------------------------------------------------------------------------------- INDEX
    // ........................................................................................... (defaults)
    this.test.comment( 'index should get a list of tools in panel form (by default)' );
    var toolIndex = this.api.tools.index();
    //this.debug( this.jsonStr( toolIndex ) );
    this.test.assert( utils.isArray( toolIndex ), "index returned an array: length " + toolIndex.length );
    this.test.assert( toolIndex.length >= 1, 'Has at least one tool section' );

    this.test.comment( 'index panel form should be separated into sections (by default)' );
    var firstSection = toolIndex[0]; // get data
    //this.debug( this.jsonStr( firstSection ) );
    this.test.assert( hasKeys( firstSection, panelSectionKeys ), 'Has the proper keys' );
    //TODO: test form of indiv. keys

    this.test.comment( 'index sections have a list of tool "elems"' );
    this.test.assert( utils.isArray( firstSection.elems ), firstSection.name + ".elems is an array: "
        + "length " + firstSection.elems.length );
    this.test.assert( firstSection.elems.length >= 1, 'Has at least one tool' );

    var firstTool = firstSection.elems[0]; // get data
    //this.debug( this.jsonStr( firstTool ) );
    this.test.assert( hasKeys( firstTool, panelToolKeys ), 'Has the proper keys' );

    // ........................................................................................... in_panel=False
    this.test.comment( 'index should get a list of all tools when in_panel=false' );
    toolIndex = this.api.tools.index( false );
    //this.debug( this.jsonStr( toolIndex ) );
    this.test.assert( utils.isArray( toolIndex ), "index returned an array: length " + toolIndex.length );
    this.test.assert( toolIndex.length >= 1, 'Has at least one tool' );

    this.test.comment( 'index non-panel form should be a simple list of tool summaries' );
    firstSection = toolIndex[0];
    //this.debug( this.jsonStr( firstSection ) );
    this.test.assert( hasKeys( firstSection, toolSummaryKeys ), 'Has the proper keys' );
    //TODO: test uniqueness of ids
    //TODO: test form of indiv. keys

    // ........................................................................................... trackster=True
    this.test.comment( '(like in_panel=True) index with trackster=True should '
                     + 'get a (smaller) list of tools in panel form (by default)' );
    toolIndex = this.api.tools.index( undefined, true );
    //this.debug( this.jsonStr( toolIndex ) );
    this.test.assert( utils.isArray( toolIndex ), "index returned an array: length " + toolIndex.length );
    this.test.assert( toolIndex.length >= 1, 'Has at least one tool section' );

    this.test.comment( 'index with trackster=True should be separated into sections (by default)' );
    firstSection = toolIndex[0]; // get data
    //this.debug( this.jsonStr( firstSection ) );
    this.test.assert( hasKeys( firstSection, panelSectionKeys ), 'Has the proper keys' );
    //TODO: test form of indiv. keys

    this.test.comment( 'index sections with trackster=True have a list of tool "elems"' );
    this.test.assert( utils.isArray( firstSection.elems ), firstSection.name + ".elems is an array: "
        + "length " + firstSection.elems.length );
    this.test.assert( firstSection.elems.length >= 1, 'Has at least one tool' );

    firstTool = firstSection.elems[0]; // get data
    //this.debug( this.jsonStr( firstTool ) );
    this.test.assert( hasKeys( firstTool, panelToolKeys ), 'Has the proper keys' );

    // ............................................................................ trackster=True, in_panel=False
    // this yields the same as in_panel=False...


    // ------------------------------------------------------------------------------------------- SHOW
    this.test.comment( 'show should get detailed data about the tool with the given id' );
    // get the tool select first from tool index
    toolIndex = this.api.tools.index();
    var selectFirst = findObject( findObject( toolIndex, { id: 'textutil' }).elems, { id: 'Show beginning1' });
    //this.debug( this.jsonStr( selectFirst ) );

    var toolShow = this.api.tools.show( selectFirst.id );
    //this.debug( this.jsonStr( toolShow ) );
    this.test.assert( utils.isObject( toolShow ), "show returned an object" );
    this.test.assert( hasKeys( toolShow, toolDetailKeys ), 'Has the proper keys' );

    this.test.comment( 'show data should include an array of input objects' );
    this.test.assert( utils.isArray( toolShow.inputs ), "inputs is an array: "
        + "length " + toolShow.inputs.length );
    this.test.assert( toolShow.inputs.length >= 1, 'Has at least one element' );
    for( var i=0; i<toolShow.inputs.length; i += 1 ){
        var input = toolShow.inputs[i];
        this.test.comment( 'checking input #' + i + ': ' + ( input.name || '(no name)' ) );
        this.test.assert( utils.isObject( input ), "input is an object" );
        this.test.assert( hasKeys( input, toolInputKeys ), 'Has the proper keys' );
    }
    //TODO: test form of indiv. keys


    // ------------------------------------------------------------------------------------------- CREATE
    // this is a method of running a job. Shouldn't that be in jobs.create?

    // ------------------------------------------------------------------------------------------- MISC
    //attemptShowOnAllTools.call( spaceghost );
});

// ===================================================================
spaceghost.run( function(){
});
