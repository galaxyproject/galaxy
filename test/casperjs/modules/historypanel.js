// =================================================================== module object, exports
/** Creates a new tools module object.
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
    run a tool

*/
// =================================================================== INTERNAL

// =================================================================== API (external)
//TODO: to history module
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
