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

function countKeys( object ){
    if( !utils.isObject( object ) ){ return 0; }
    var count = 0;
    for( var key in object ){
        if( object.hasOwnProperty( key ) ){ count += 1; }
    }
    return count;
}

// =================================================================== TESTS
var workflowJSONFilepath = 'test-data/Bed_interval_lengths.ga',
    workflowModelClass = 'StoredWorkflow',
    workflowSummaryKeys = [
        'id', 'model_class', 'name', 'published', 'tags', 'url'
    ],
    workflowDetailKeys = workflowSummaryKeys.concat([
        'inputs', 'steps'
    ]),
    stepKeys = [
        'id', 'input_steps', 'tool_id', 'type'
    ],
    simpleBedFilepath = 'test-data/simple.bed',
    uploadedFile = null,
    workflowCreateKeys = [ 'history', 'outputs' ];


spaceghost.thenOpen( spaceghost.baseUrl ).then( function(){

    // ------------------------------------------------------------------------------------------- UPLOAD
    // upload first or we have no data to test
    this.test.comment( 'upload should allow importing a new workflow given in JSON form' );
    var workflowToUpload = this.loadJSONFile( workflowJSONFilepath );
    //this.debug( this.jsonStr( workflowToUpload ) );
    var returned = this.api.workflows.upload( workflowToUpload );

    this.test.comment( 'upload should return a summary object of what we uploaded' );
    //this.debug( this.jsonStr( returned ) );
    this.test.assert( utils.isObject( returned ), "upload returned an object" );
    this.test.assert( hasKeys( returned, workflowSummaryKeys ), "upload's return has the proper keys" );
    this.test.assert( this.api.isEncodedId( returned.id ),
        "id is of the proper form: " + returned.id );
    this.test.assert( returned.model_class === workflowModelClass,
        "has the proper model_class: " + returned.model_class );
    this.test.assert( returned.name === workflowToUpload.name + ' ' + '(imported from API)',
        "has the proper, modified name: " + returned.name );
    this.test.assert( !returned.published,
        "uploaded workflow defaults to un-published: " + returned.published );
    this.test.assert( utils.isArray( returned.tags ) && returned.tags.length === 0,
        "upload returned an empty tag array: " + this.jsonStr( returned.tags ) );
    this.test.assert( returned.url === '/' + utils.format( this.api.workflows.urlTpls.show, returned.id ),
        "url matches the show url: " + returned.url );


    // ------------------------------------------------------------------------------------------- INDEX
    this.test.comment( 'index should get a list of workflows' );
    var workflowIndex = this.api.workflows.index();
    this.debug( this.jsonStr( workflowIndex ) );
    this.test.assert( utils.isArray( workflowIndex ), "index returned an array: length " + workflowIndex.length );
    this.test.assert( workflowIndex.length >= 1, "index returned at least one job" );

    this.test.comment( 'index should have returned an object matching the workflow uploaded' );
    var firstWorkflow = workflowIndex[0];
    this.test.assert( hasKeys( firstWorkflow, workflowSummaryKeys ), "index has the proper keys" );
    this.test.assert( this.api.isEncodedId( firstWorkflow.id ),
        "id is of the proper form: " + firstWorkflow.id );
    this.test.assert( firstWorkflow.model_class === workflowModelClass,
        "has the proper model_class: " + firstWorkflow.model_class );
    this.test.assert( firstWorkflow.name === workflowToUpload.name + ' ' + '(imported from API)',
        "has the proper, modified name: " + firstWorkflow.name );
    this.test.assert( !firstWorkflow.published,
        "workflow is un-published: " + firstWorkflow.published );
    this.test.assert( utils.isArray( firstWorkflow.tags ) && firstWorkflow.tags.length === 0,
        "tag array is empty: " + this.jsonStr( firstWorkflow.tags ) );
    this.test.assert( firstWorkflow.url === '/' + utils.format( this.api.workflows.urlTpls.show, firstWorkflow.id ),
        "url matches the show url: " + firstWorkflow.url );


    // ------------------------------------------------------------------------------------------- SHOW
    this.test.comment( 'show should get detailed data about the workflow with the given id' );
    var workflowShow = this.api.workflows.show( firstWorkflow.id );
    this.debug( this.jsonStr( workflowShow ) );
    this.test.assert( utils.isObject( workflowShow ), "show returned an object" );
    this.test.assert( hasKeys( workflowShow, workflowDetailKeys ), "show has the proper keys" );
    this.test.assert( this.api.isEncodedId( workflowShow.id ),
        "id is of the proper form: " + workflowShow.id );
    this.test.assert( workflowShow.model_class === workflowModelClass,
        "has the proper model_class: " + workflowShow.model_class );
    this.test.assert( workflowShow.name === workflowToUpload.name + ' ' + '(imported from API)',
        "has the proper, modified name: " + workflowShow.name );
    this.test.assert( !workflowShow.published,
        "workflow is un-published: " + workflowShow.published );
    this.test.assert( utils.isArray( workflowShow.tags ) && workflowShow.tags.length === 0,
        "tag array is empty: " + this.jsonStr( workflowShow.tags ) );
    this.test.assert( workflowShow.url === '/' + utils.format( this.api.workflows.urlTpls.show, workflowShow.id ),
        "url matches the show url: " + workflowShow.url );

    this.test.comment( 'inputs from show should be an object (and, in this case, empty)' );
    var inputs = workflowShow.inputs;
    //this.debug( 'inputs:\n' + this.jsonStr( inputs ) );
    this.test.assert( utils.isObject( workflowShow.inputs ), "inputs is an object" );
    //for( var inputKey in inputs ){
    //    if( inputs.hasOwnProperty( inputKey ) ){
    //    }
    //}
    this.test.assert( countKeys( workflowShow.inputs ) === 0, "inputs is empty" );

    this.test.comment( 'steps from show should be an object containing each tool defined as a step' );
    var steps = workflowShow.steps;
    //this.debug( 'steps:\n' + this.jsonStr( steps ) );
    this.test.assert( utils.isObject( workflowShow.steps ), "steps is an object" );
    //! ids for steps (and the keys used) are un-encoded (and in strings)
    for( var stepKey in steps ){
        if( steps.hasOwnProperty( stepKey ) ){
            // any way to match this up with the workflowToUpload?

            this.test.assert( utils.isString( stepKey ), "step key is a string: " + stepKey );
            var step = steps[ stepKey ];
            this.debug( 'step:\n' + this.jsonStr( step ) );
            this.test.assert( hasKeys( step, stepKeys ), "step has the proper keys" );

            this.test.assert( utils.isNumber( step.id ),
                "step id is a number: " + step.id );
            try {
                this.test.assert( parseInt( stepKey, 10 ) === step.id,
                    "step id matches step key: " + step.id );
            } catch( err ){
                this.test.fail( 'couldnt parse stepKey: ' + stepKey + ',' + err );
            }

            this.test.assert( utils.isObject( step.input_steps ), "input_steps is an object" );
            if( countKeys( step.input_steps ) !== 0 ){
                this.test.assert( hasKeys( step.input_steps, [ 'input' ] ), "input_steps has the proper keys" );
            }

            this.test.assert( step.type === 'tool',
                "step type is a tool: " + step.type );

            // check for tools in this wf with the api
            this.test.assert( utils.isString( step.tool_id ),
                "step tool_id is a string: " + step.tool_id );
            var tool_used = this.api.tools.show( step.tool_id );
            //this.debug( this.jsonStr( tool_used ) )
            this.test.assert( countKeys( step.input_steps ) !== 0, "found tool in api.tools for: " + step.tool_id );

            // trace the path through input_steps, source_steps
        }
    }



    // ------------------------------------------------------------------------------------------- MISC
});

// now run the uploaded workflow
spaceghost.tools.uploadFile( simpleBedFilepath, function( uploadInfo ){
    uploadedFile = uploadInfo;
});
spaceghost.then( function(){
    var currentHistory = this.api.histories.index()[0],
        firstWorkflow = this.api.workflows.show( this.api.workflows.index()[0].id );

    //this.debug( this.jsonStr( uploadedFile ) );
    var uploadedFileId = uploadedFile.hdaElement.attributes.id.split( '-' )[1];
    this.debug( this.jsonStr( uploadedFileId ) );
    this.debug( this.jsonStr( this.api.hdas.show( currentHistory.id, uploadedFileId ) ) );

    //this.debug( this.jsonStr( firstWorkflow ) );
    // find the input step by looking for a step where input_steps == {}
    var input_step = null;
    for( var stepKey in firstWorkflow.steps ){
        if( firstWorkflow.steps.hasOwnProperty( stepKey ) ){
            var step = firstWorkflow.steps[ stepKey ];
            if( countKeys( step.input_steps ) === 0 ){
                input_step = stepKey;
                this.debug( 'input step: ' + this.jsonStr( step ) )
                break;
            }
        }
    }

    // ------------------------------------------------------------------------------------------- CREATE
    this.test.comment( 'create should allow running an existing workflow' );
    // needs workflow_id, history, ds_map
    var executionData = {
        workflow_id : firstWorkflow.id,
        history     : 'hist_id=' + currentHistory.id,
        ds_map      : {}
    };
    executionData.ds_map[ input_step ] = {
        src: 'hda',
        id: uploadedFileId
    };
    var returned = this.api.workflows.create( executionData );
    this.debug( this.jsonStr( returned ) );
    this.test.assert( utils.isObject( returned ), "create returned an object" );
    this.test.assert( hasKeys( returned, workflowCreateKeys ), "create returned the proper keys" );
    this.test.assert( this.api.isEncodedId( returned.history ),
        "history id is proper: " + returned.history );
    this.test.assert( utils.isArray( returned.outputs ),
        "create.outputs is an array: length " + returned.outputs.length );
    this.test.assert( returned.outputs.length >= 1, "there is at least one output" );
    for( var i=0; i<returned.outputs.length; i+=1 ){
        this.test.assert( this.api.isEncodedId( returned.outputs[i] ),
            "output id is proper: " + returned.outputs[i] );
    }

    var counter = 0;
    this.waitFor(
        function checkHdas(){
            if( counter % 4 !== 0 ){
                counter += 1;
                return false;
            }
            counter += 1;

            var outputs = this.api.hdas.index( currentHistory.id, returned.outputs );
            //this.debug( 'outputs:\n' + this.jsonStr( outputs ) );
            for( var i=0; i<outputs.length; i+=1 ){
                var output = outputs[i];
                this.debug( utils.format( 'name: %s, state: %s', output.name, output.state ) );
                if( output.state === 'queued' || output.state === 'running' ){
                    return false;
                }
            }
            return true;
        },
        function allDone(){
            this.debug( 'DONE' );
            var outputs = this.api.hdas.index( currentHistory.id, returned.outputs );
            this.debug( 'outputs:\n' + this.jsonStr( outputs ) );
        },
        function timeout(){
            this.debug( 'timeout' );

        },
        45 * 1000
    );
/*
*/
});

// ===================================================================
spaceghost.run( function(){
});
