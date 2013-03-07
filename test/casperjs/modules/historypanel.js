// =================================================================== module object, exports
/** Creates a new historypanel module object.
 *  @exported
 */
exports.create = function createHistoryPanel( spaceghost ){
    return new HistoryPanel( spaceghost );
};

/** HistoryPanel object constructor.
 *  @param {SpaceGhost} spaceghost a spaceghost instance
 */
var HistoryPanel = function HistoryPanel( spaceghost ){
    this.options = {
        progressIntervalDelay : 500
    };
    //??: circ ref?
    this.spaceghost = spaceghost;
};
exports.HistoryPanel = HistoryPanel;

HistoryPanel.prototype.toString = function toString(){
    return this.spaceghost + '.HistoryPanel';
};

// -------------------------------------------------------------------
/* TODO:
    conv.fns:
        expand hda (click title)
        undelete hda
        rename history

*/
// =================================================================== INTERNAL

// =================================================================== API (external)
/** Find the casper element info of the hda wrapper given the hda title and hid.
 *      NOTE: if more than one is found, will return the first found.
 *      precondition: you should wrap this with withFrame( 'galaxy_history' ) :(
 *  @param {String} title   the title of the hda
 *  @param {Int} hid        (optional) the hid of the hda to look for
 *  @returns {Object|null} ElementInfo of the historyItemWrapper found, null if not found
 */
HistoryPanel.prototype.hdaElementInfoByTitle = function hdaElementInfoByTitle( title, hid ){
    var spaceghost = this.spaceghost,
        titleContains = ( hid !== undefined )?( hid + ': ' + title ):( title ),
        wrapperInfo = null;

    //NOTE: depends on jquery
    wrapperInfo = spaceghost.evaluate( function( titleContains ){
        // find the title, then the wrapper (2 containers up)
        var $title = $( '.historyItemTitle:contains(' + titleContains + ')' );
        var $wrapper = $title.parent().parent();
        return (( $wrapper.attr( 'id' ) )?( __utils__.getElementInfo(  '#' + $wrapper.attr( 'id' ) )):( null ));
    }, titleContains );

    return wrapperInfo;
};

/** Wait for the hda with given id to move into the given state.
 *      whenInStateFn and timeoutFn will be passed the hda element info (see Casper#getElementInfo)
 *  @param {String} hdaSelector     selector for hda (should be historyItemWrapper)
 *  @param {String} finalState      hda state to wait for (e.g. 'ok', 'error', 'running', 'queued', etc.)
 *  @param {Function} whenInStateFn called when hda goes into finalState
 *  @param {Function} timeoutFn     called when maxWaitMs have passed without the desired state
 *  @param {Int} maxWaitMs          number of milliseconds to wait before timing out (defaults to options.waitTimeout)
 */
HistoryPanel.prototype.waitForHdaState = function waitForHdaState( hdaSelector, finalState,
                                                                   whenInStateFn, timeoutFn, maxWaitMs ){
    //TODO:?? explicitly a historyWrapper id?
    // we need a larger timeout for these - it can take a bit
    maxWaitMs = maxWaitMs || this.spaceghost.options.waitTimeout;
    var spaceghost = this.spaceghost,
        finalStateClass = '.historyItem-' + finalState;

    spaceghost.then( function(){
        spaceghost.withFrame( spaceghost.selectors.frames.history, function(){

            // save the old time out
            var oldWaitTimeout = spaceghost.options.waitTimeout,

            // output some progress indicator within the test (debug)
                progressIntervalId = setInterval( function progress(){
                    // get the state from the hda wrapper's class
                    var state = spaceghost.evaluate( function( hdaSelector ){
                        if( !$( hdaSelector )[0] ){ return '(no hda found)'; }
                        var $wrapperClasses = $( hdaSelector ).attr( 'class' );
                        //TODO: remove magic string/regex
                        return $wrapperClasses.match( /historyItem\-(\w+)/ )[1];
                    }, hdaSelector );
                    spaceghost.debug( hdaSelector + ': ' + state );
                }, spaceghost.historypanel.options.progressIntervalDelay ),

            // when done, close down the progress reporter and reset the wait timeout to what it was
                finallyFn = function(){
                    spaceghost.options.waitTimeout = oldWaitTimeout;
                    clearInterval( progressIntervalId );
                };

            spaceghost.options.waitTimeout = maxWaitMs;
            spaceghost.waitForSelector( hdaSelector + finalStateClass,

                // if the hda state became 'ok', call the whenInStateFn and close up
                function _whenInState(){
                    var hdaInfo = spaceghost.elementInfoOrNull( hdaSelector );
                    spaceghost.debug( 'HDA now in state ' + finalState );
                    //spaceghost.debug( 'HDA:\n' + hdaInfo );
                    whenInStateFn.call( spaceghost, hdaInfo );
                    finallyFn();

                // if we've timed out, call the timeoutFn and close up
                }, function timeout(){
                    var hdaInfo = spaceghost.elementInfoOrNull( hdaSelector );
                    spaceghost.debug( 'HDA timed out. HDA = ' + spaceghost.jsonStr( hdaInfo ) );
                    timeoutFn.call( spaceghost, hdaInfo );
                    finallyFn();
                }
            );
        });
    });
};

/** Find the casper element info of the hda wrapper given the hda title and hid.
 *      NOTE: if more than one is found, will return the first found.
 *      precondition: you should wrap this with withFrame( 'galaxy_history' ) :(
 *  @param {String} title   the title of the hda
 *  @param {Int} hid        (optional) the hid of the hda to look for
 *  @returns {Object|null} ElementInfo of the historyItemWrapper found, null if not found
 */
HistoryPanel.prototype.hdaElementInfoByTitle = function hdaElementInfoByTitle( title, hid ){
    var titleContains = ( hid !== undefined )?( hid + ': ' + title ):( title ),
        wrapperInfo = this.spaceghost.elementInfoOrNull(
            //TODO??: how to put this in editable json file
            xpath( '//span[contains(text(),"' + titleContains + '")]/parent::*/parent::*' ) );
    //this.spaceghost.debug( 'wrapperInfo: ' + this.spaceghost.jsonStr( wrapperInfo ) );
    return wrapperInfo;
};
//TODO!: this will break if the hda name has single or double quotes (which are permitted in names)

/** Find the id of the hda wrapper given the hda title and hid.
 *  @param {String} title   the title of the hda
 *  @param {Int} hid        (optional) the hid of the hda to look for
 *  @returns {String|null} DOM id of the historyItemWrapper found, null if not found
 */
HistoryPanel.prototype.hdaIdByTitle = function hdaIdByTitle( title, hid ){
    var elementInfo = this.hdaElementInfoByTitle( title, hid );
    return (( elementInfo && elementInfo.attributes && elementInfo.attributes.id )?
        ( elementInfo.attributes.id ):( null ));
};

/** Deletes an hda by finding an hda with the given title and clicking on the delete icon.
 *      NOTE: if more than one is found, the first found will be deleted.
 *  @param {String} hdaSelector     a css or xpath selector for an historyItemWrapper
 *  @param {Function} whenDeletedFn function to be called when the hda is deleted (optional)
 *  @param {Function} timeoutFn     function to be called if/when the deleted attempted times out (optional)
 */
HistoryPanel.prototype.deleteHda = function deleteHda( hdaSelector, whenDeletedFn, timeoutFn ){
    whenDeletedFn = whenDeletedFn || function(){};
    var spaceghost = this.spaceghost;

    spaceghost.withFrame( spaceghost.selectors.frames.history, function deletingHda(){
        //precondition: historyItemWrapper's (hda dom elements) should have an id
        // we could use the selector directly, but better if it errors before an attempted delete
        var hdaId = spaceghost.getElementInfo( hdaSelector ).attributes.id;
        spaceghost.debug( 'hda id: ' + hdaId );

        // get the delete icon and click it
        //TODO: handle disabled delete icon?
        var deleteIconSelector = 'a[id^="historyItemDeleter-"]',
            thisDeleteIconSelector = '#' + hdaId + ' ' + deleteIconSelector;
        spaceghost.click( thisDeleteIconSelector );

        spaceghost.waitWhileSelector( '#' + hdaId,
            function hdaNoLongerInDom(){
                spaceghost.info( 'hda deleted: ' + hdaSelector );
                whenDeletedFn.call( spaceghost );

            }, function timeout(){
                if( timeoutFn ){
                    timeoutFn.call( spaceghost );
                } else {
                    throw new spaceghost.GalaxyError( 'HistoryPanelError: '
                        + 'timeout attempting to delete hda : ' + hdaSelector );
                }
            });
    });
};

/** Expands an HDA.
 *  @param {String} hdaSelector     a css or xpath selector for an historyItemWrapper
 */
HistoryPanel.prototype.expandHda = function expandHda( hdaSelector ){
    var spaceghost = this.spaceghost,
        historyFrameInfo = spaceghost.getElementInfo( 'iframe[name="galaxy_history"]' );

    spaceghost.withFrame( spaceghost.selectors.frames.history, function expandingHda(){
        var titleInfo = spaceghost.getElementInfo( hdaSelector + ' .historyItemTitle' );
        spaceghost.page.sendEvent( 'mousedown',
            historyFrameInfo.x + titleInfo.x + 1, historyFrameInfo.y + titleInfo.y - 5 );
    });
    return spaceghost;
};
