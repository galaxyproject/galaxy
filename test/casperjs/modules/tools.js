// =================================================================== module object, exports
/** Creates a new tools module object.
 *  @exported
 */
exports.create = function createTools( spaceghost ){
    return new Tools( spaceghost );
};

/** Tools object constructor.
 *  @param {SpaceGhost} spaceghost a spaceghost instance
 */
var Tools = function Tools( spaceghost ){
    //??: circ ref?
    this.options = {
        defaultUploadWait : ( 30 * 1000 )
    };
    this.spaceghost = spaceghost;
};
exports.Tools = Tools;

Tools.prototype.toString = function toString(){
    return this.spaceghost + '.Tools';
};

// -------------------------------------------------------------------
/* TODO:
    move selectors from sg to here

*/
// =================================================================== INTERNAL
/** Tests uploading a file.
 *      NOTE: this version does NOT throw an error on a bad upload.
 *      It is meant for testing the upload functionality and, therefore, is marked as private.
 *      Other tests should use uploadFile
 *  @param {String} filepath    the local filesystem path of the file to upload (absolute (?))
 */
Tools.prototype._uploadFile = function _uploadFile( filepath ){
    var spaceghost = this.spaceghost,
        uploadInfo = {};
    //TODO: check file exists using phantom.fs
    //TODO: pull from test data
    uploadInfo[ spaceghost.data.selectors.tools.upload.fileInput ] = filepath;
    spaceghost.debug( 'uploading file: ' + filepath );

    spaceghost.then( function(){
        spaceghost.withFrame( spaceghost.data.selectors.frames.tools, function(){
            spaceghost.clickLabel( spaceghost.data.labels.tools.upload.panelLabel );
        });
    });

    spaceghost.then( function beginUpload(){
        spaceghost.withFrame( spaceghost.data.selectors.frames.main, function(){
            spaceghost.fill( spaceghost.data.selectors.tools.general.form, uploadInfo, false );

            // the following throws:
            //  [error] [remote] Failed dispatching clickmouse event on xpath selector: //input[@value="Execute"]:
            //  PageError: TypeError: 'undefined' is not a function (evaluating '$(spaceghost).formSerialize()')
            // ...and yet the upload still seems to work
            spaceghost.click( xpath( spaceghost.data.selectors.tools.general.executeButton_xpath ) );
        });
    });

    // debugging
    spaceghost.withFrame( spaceghost.data.selectors.frames.main, function afterUpload(){
        var messageInfo = spaceghost.elementInfoOrNull( spaceghost.data.selectors.messages.all );
        spaceghost.debug( 'post upload message:\n' + spaceghost.jsonStr( messageInfo ) );
    });
};

/** Parses the hid and name of a newly uploaded file from the tool execution donemessagelarge
 *  @param {String} doneMsgText     the text extracted from the donemessagelarge after a tool execution
 */
Tools.prototype._parseDoneMessageForTool = function parseDoneMessageForTool( doneMsgText ){
    //TODO: test on non-upload
    var executionInfo = {};
    var textMatch = doneMsgText.match( /added to the queue:\n\n(\d+)\: (.*)\n/m );
    if( textMatch ){
        if( textMatch.length > 1 ){
            executionInfo.hid = parseInt( textMatch[1], 10 );
        }
        if( textMatch.length > 2 ){
            executionInfo.name = textMatch[2];
        }
        executionInfo.name = textMatch[2];
    }
    return executionInfo;
};

// ------------------------------------------------------------------- get avail. tools
// list available tools
//spaceghost.then( function(){
//    spaceghost.withFrame( 'galaxy_tools', function(){
//        //var availableTools = this.fetchText( 'a.tool-link' );
//
//        var availableTools = this.evaluate( function(){
//            //var toolTitles = __utils__.findAll( 'div.toolTitle' );
//            //return Array.prototype.map.call( toolTitles, function( e ){
//            //    //return e.innerHtml;
//            //    return e.textContent || e.innerText;
//            //}).join( '\n' );
//
//            var toolLinks = __utils__.findAll( 'a.tool-link' );
//            return Array.prototype.map.call( toolLinks, function( e ){
//                //return e.innerHtml;
//                return e.textContent || e.innerText;
//            }).join( '\n' );
//        });
//        this.debug( 'availableTools: ' + availableTools );
//    });
//});

// =================================================================== API (external)
/** get filename from filepath
 *  @param {String} filepath    (POSIX) filepath
 *  @returns {String} filename part of filepath
 */
Tools.prototype.filenameFromFilepath = function filenameFromFilepath( filepath ){
    var lastSepIndex = filepath.lastIndexOf( '/' );
    if( lastSepIndex !== -1 ){
        return filepath.slice( lastSepIndex + 1 );
    }
    return filepath;
};

/** Wait for the hda with given id to move into the given state.
 *      callback function will be passed an uploadInfo object in the form:
 *          filepath:   the filepath of the uploaded file
 *          filename:   the filename of the uploaded file
 *          hid:        the hid of the uploaded file hda in the current history
 *          name:       the name of the uploaded file hda
 *          hdaElement: the hda DOM (casperjs form) element info object (see Casper#getElementInfo)
 *  @param {String} filepath        (POSIX) filepath
 *  @param {Function} callback      callback function called after hda moves into ok state (will be passed uploadInfo)
 *  @param {Integer} timeoutAfterMs milliseconds to wait before timing out (defaults to options.defaultUploadWait)
 */
Tools.prototype.uploadFile = function uploadFile( filepath, callback, timeoutAfterMs ){
    timeoutAfterMs = timeoutAfterMs || this.options.defaultUploadWait;
    var spaceghost = this.spaceghost,
        filename = this.filenameFromFilepath( filepath ),
        uploadInfo = {};

    // precondition: filepath is relative to scriptDir
    filepath = spaceghost.options.scriptDir + filepath;

    // upload the file erroring if a done message is not displayed, aggregate info about upload
    spaceghost.info( 'uploading file: ' + filepath + ' (timeout after ' + timeoutAfterMs + ')' );
    this._uploadFile( filepath );
    spaceghost.withFrame( spaceghost.data.selectors.frames.main, function toolExecuted(){
        spaceghost.debug( 'checking for done message' );
        var doneElementInfo = spaceghost.elementInfoOrNull( spaceghost.data.selectors.messages.donelarge );
        if( !doneElementInfo ){
            throw new spaceghost.GalaxyError( 'Upload Error: no done message uploading "' + filepath + '"' );
        }
        spaceghost.debug( 'doneElementInfo: ' + spaceghost.jsonStr( doneElementInfo ) );
        // grab the hid and uploaded hda name from the done message
        uploadInfo = spaceghost.tools._parseDoneMessageForTool( doneElementInfo.text );
        uploadInfo.filename = filename;
        uploadInfo.filepath = filepath;
        spaceghost.debug( 'uploadInfo: ' + spaceghost.jsonStr( uploadInfo ) );
    });

    // the hpanel should refresh and display the uploading file, wait for that to go into the ok state
    // throw if uploaded HDA doesn't appear, or it doesn't move to 'ok' after allotted time
    spaceghost.then( function getNewHda(){
        spaceghost.debug( 'beginning wait for upload file\'s ok state' );
        // get the hda view DOM element from the upload name and hid
        spaceghost.withFrame( spaceghost.data.selectors.frames.history, function(){
            spaceghost.waitForSelector( '#history-name', function(){
                var hdaInfo = spaceghost.historypanel.hdaElementInfoByTitle( uploadInfo.name, uploadInfo.hid );
                if( hdaInfo === null ){
                    throw new spaceghost.GalaxyError( 'Upload Error: uploaded file HDA not found: '
                        + uploadInfo.hid + ', ' + uploadInfo.name );
                }
                spaceghost.debug( 'hdaInfo: ' + spaceghost.jsonStr( hdaInfo ) );
                uploadInfo.hdaElement = hdaInfo;
                // uploadInfo now has filepath, filename, name, hid, and hdaElement
            });
        });

        spaceghost.then( function waitForOk(){
            spaceghost.debug( 'beginning wait for upload file\'s ok state' );

            // currently best way to get hda state is using the historyItem-<state> class of the historyItemWrapper
            var hdaStateClass = uploadInfo.hdaElement.attributes[ 'class' ].match( /historyItem\-(\w+)/ )[0];
            if( hdaStateClass !== 'historyItem-ok' ){

                spaceghost.historypanel.waitForHdaState( '#' + uploadInfo.hdaElement.attributes.id, 'ok',
                    function whenInStateFn( hdaInfo ){
                        // refresh hdaElement info
                        uploadInfo.hdaElement = hdaInfo;
                        callback.call( spaceghost, uploadInfo );

                    }, function timeoutFn( hdaInfo ){
                        var finalClass = (( hdaInfo )?( hdaInfo.attributes[ 'class' ] ):( undefined ));
                        spaceghost.debug( 'final classes: ' + finalClass );
                        throw new spaceghost.GalaxyError( 'Upload Error: timeout waiting for ok state: '
                            + '"' + uploadInfo.hid + ': ' + uploadInfo.name + '"'
                            + ' (waited ' + timeoutAfterMs + ' ms)' );

                    }, timeoutAfterMs );
            }
        });
    });
    return spaceghost;
};
//TODO: upload via url
//TODO: upload by textarea
