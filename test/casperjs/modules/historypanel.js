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
    this.spaceghost = spaceghost;
};
exports.HistoryPanel = HistoryPanel;

HistoryPanel.prototype.toString = function toString(){
    return this.spaceghost + '.HistoryPanel';
};

// -------------------------------------------------------------------
/* TODO:
    conv.fns:
        switch to history frame and wait for any possible rendering - waitForHistoryPanel
        undelete hda
        rename history
    consider removing all timeouts, callbacks - just use thens in test

*/
// =================================================================== INTERNAL
var xpath = require( 'casper' ).selectXPath;
    //utils = require( 'utils' );

// =================================================================== API (external)
// ------------------------------------------------------------------- frame control
/** Is casper currently 'in' the history frame?
 *  @returns {Boolean}
 */
HistoryPanel.prototype.inFrame = function inFrame(){
    return ( ( this.spaceghost.page.frameName === this.spaceghost.data.selectors.frames.history )
          && ( this.spaceghost.page.frameTitle === this.data.text.frameTitle ) );
};

/** Hover over an element in the history panel.
 *  @param {String} selector        a css or xpath selector for an historyItemWrapper
 */
HistoryPanel.prototype.hoverOver = function hoverOver( selector ){
    var spaceghost = this.spaceghost,
        historyFrameInfo = spaceghost.jumpToTop( function(){
            return spaceghost.getElementInfo( 'iframe[name="galaxy_history"]' );
        });
    //spaceghost.debug( 'historyFrameInfo:\n' + spaceghost.jsonStr( historyFrameInfo ) );

    spaceghost.jumpToHistory( function(){
        var elementInfo = spaceghost.getElementInfo( selector ),
            newCoords = { x: ( historyFrameInfo.x + elementInfo.x ),
                          y: ( historyFrameInfo.y + elementInfo.y ) };
        spaceghost.page.sendEvent( 'mousemove', newCoords.x + 1, newCoords.y + 1 );
    });
    return spaceghost;
};

// ------------------------------------------------------------------- hdas
/** Parse the hid and name from an HDA title.
 *      NOTE: if more than one is found, will return the first found.
 *  @param {String} title   the title of the hda
 *  @returns {Object}       of the form { hid: <hid>, name: <name> }
 */
HistoryPanel.prototype.hdaHidAndNameFromTitle = function hdaHidAndNameFromTitle( title ){
    var sep = ': ', split = title.split( sep, 1 );
    return {
        name : (( split.length >= 2 )?( split[1] ):( split[0] )),
        hid  : (( split.length >= 2 )?( parseInt( split[0], 10 ) ):( undefined ))
    };
};

/** Find the casper element info of the hda wrapper given the hda title and hid.
 *      NOTE: if more than one is found, will return the first found.
 *  @param {String} title   the title of the hda
 *  @param {Int} hid        (optional) the hid of the hda to look for
 *  @returns {Object|null} ElementInfo of the historyItemWrapper found, null if not found
 */
HistoryPanel.prototype.hdaElementInfoByTitle = function hdaElementInfoByTitle( title, hid ){
    var spaceghost = this.spaceghost,
        titleContains = ( hid !== undefined )?( hid + ': ' + title ):( title );
    //TODO: this would fail if we named/uploaded a file that has quotations -
    //  we can use underscore.un/escape to solve that

    return spaceghost.jumpToHistory( function getWrapperInfo(){
        var wrapperXpath = xpath( '//span[@class="historyItemTitle" ' +
                                  'and contains(text(),"' + titleContains + '")]/../..' );
        return spaceghost.elementInfoOrNull( wrapperXpath );
    });
};

/** Get the state string of the given hda.
 *      NOTE: if more than one is found, will return the first found.
 *  @param {Selector} title a selector for the desired hdaWrapper
 *  @returns {String|undefined}  class string of the historyItemWrapper found, undefined if not found or set
 */
HistoryPanel.prototype.getHdaState = function getHdaState( hdaSelector ){
    return this.spaceghost.jumpToHistory( function(){
        var found = null,
            hdaInfo = this.elementInfoOrNull( hdaSelector );
        if( !hdaInfo ){ return undefined; }
        return (( found = hdaInfo.attributes[ 'class' ].match( /historyItem\-(\w+)/ ) )?( found[1] ):( undefined ));
    });
};

/** Get the encoded database/API id of the given hda.
 *      NOTE: if more than one is found, will return the first found.
 *  @param {Selector} title a selector for the desired hdaWrapper
 *  @returns {String|undefined}  db id string of the hda found, undefined if not found or set
 */
HistoryPanel.prototype.getHdaEncodedId = function getHdaEncodedId( hdaSelector ){
    var hdaInfo = spaceghost.elementInfoOrNull( hdaSelector );
    if( !hdaInfo ){ return undefined; }
    return (( found = hdaInfo.attributes.id.match( /historyItem\-(\w+)/ ) )?( found[1] ):( undefined ));
};

// ------------------------------------------------------------------- step functions
/** Version of Casper#withFrame for the history iframe.
 *      Hopefully will allow easier test transition if/when frames are removed
 *      (i.e. -> just call the function).
 *      NOTE: is more than one Casper step.
 *  @param {Function} then  function called when in the history frame
 */
HistoryPanel.prototype.then = function then( thenFn ){
    if( this.inFrame() ){
        thenFn.call( this.spaceghost );
    } else {
        this.spaceghost.withHistoryPanel( thenFn );
    }
};

/** Moves into history iframe and waits until hdas are visible or empty message is.
 *      NOTE: is more than one Casper step.
 *  @see Casper@waitFor
 */
HistoryPanel.prototype.waitForHdas = function waitForHdas( then, timeout, maxWait ){
    //TODO:?? should this wait until the seletors are in AND they are opaque?
    var spaceghost = this.spaceghost;
    this.then( function waitingForHdas(){
        this.waitFor(
            function checkHpanel(){
                // trying a subtitle opacity test for page.isloaded
                var subtitleOpacity = this.evaluate( function( selector ){
                    return $( selector ).css( 'opacity' );
                }, this.historypanel.data.selectors.history.subtitle );
                return ( subtitleOpacity !== 1
                       && ( ( this.visible( this.historypanel.data.selectors.hda.wrapper.itemClass ) )
                          ||( this.visible( this.historypanel.data.selectors.history.emptyMsg ) ) ) );
            }, then, timeout, maxWait );
    });
    return spaceghost;
};

/** Expands or collapses an HDA by clicking the title (does nothing if already in desired state).
 *      NOTE: is more than one Casper step.
 *  @param {String} hdaSelector     a css or xpath selector for an historyItemWrapper
 *  @param {Function} then          function called when the change is made
 *  @param {Boolean} desiredClosed  true if you want to collapse, false if you want open
 *  @private
 */
HistoryPanel.prototype._thenExpandOrCollapseHda = function _thenExpandOrCollapseHda( hdaSelector, then, desiredClosed ){
    // using a step here (instead of a jump) bc we need the wait for function
    this.then( function checkingHda(){
        this.info( (( desiredClosed )?( 'collapsing' ):( 'expanding' )) + ' hda: ' + hdaSelector );

        // click to open if the body isn't visible and call wait to account for opening animation
        if( this.visible( hdaSelector + ' ' + this.historypanel.data.selectors.hda.body ) === desiredClosed ){
            this.click( hdaSelector + ' ' + this.historypanel.data.selectors.hda.title );
            //NOTE: then is executed in the top frame
            //TODO: magic number
            this.wait( 500, then );

        // otherwise, just call then
        } else if( then ){
            then.call( this );
        }
    });
    return this.spaceghost;
};

/** Collapses an HDA by clicking the title (does nothing if already collapsed).
 *      NOTE: is more than one Casper step.
 *  @param {String} hdaSelector     a css or xpath selector for an historyItemWrapper
 *  @param {Function} then          function called when the change is made
 */
HistoryPanel.prototype.thenCollapseHda = function thenCollapseHda( hdaSelector, then ){
    return this._thenExpandOrCollapseHda( hdaSelector, then, true );
};

/** Expands an HDA by clicking the title (does nothing if already expanded).
 *      NOTE: is more than one Casper step.
 *  @param {String} hdaSelector     a css or xpath selector for an historyItemWrapper
 *  @param {Function} then          function called when the change is made
 */
HistoryPanel.prototype.thenExpandHda = function thenExpandHda( hdaSelector, then ){
    return this._thenExpandOrCollapseHda( hdaSelector, then, false );
};

/** Wait for the hda with given id to move into the given state.
 *      whenInStateFn and timeoutFn will be passed the hda element info (see Casper#getElementInfo)
 *      NOTE: is more than one Casper step.
 *  @param {String} hdaSelector     selector for hda (should be historyItemWrapper)
 *  @param {String} finalState      hda state to wait for (e.g. 'ok', 'error', 'running', 'queued', etc.)
 *  @param {Function} whenInStateFn called when hda goes into finalState
 *  @param {Function} timeoutFn     called when maxWaitMs have passed without the desired state
 *      (defaults to throwing and error)
 *  @param {Int} maxWaitMs          number of milliseconds to wait before timing out
 *      (defaults to options.waitTimeout)
 */
HistoryPanel.prototype.waitForHdaState = function waitForHdaState( hdaSelector, finalState,
                                                                   whenInStateFn, timeoutFn, maxWaitMs ){
    // maxWaitMs default - we need a larger timeout option, some things can take a bit
    maxWaitMs = maxWaitMs || this.spaceghost.options.waitTimeout;
    var hpanel = this,
        spaceghost = this.spaceghost;

    this.then( function(){
        // get initial state, cache old timeout, set new timeout
        var prevState = hpanel.getHdaState( hdaSelector ),
            oldWaitTimeout = spaceghost.options.waitTimeout;
        spaceghost.info( hdaSelector + ': ' + prevState );
        spaceghost.options.waitTimeout = maxWaitMs;

        // begin waiting for desired state
        spaceghost.waitFor(
            function _checkForState(){
                var newState = hpanel.getHdaState( hdaSelector );
                // report state changes
                if( newState !== prevState ){
                    spaceghost.info( hdaSelector + ': ' + newState );
                    prevState = newState;
                }
                return newState === finalState;
            },
            // if the hda state happened, call the whenInStateFn
            //  and close down the progress interval and reset the wait timeout to what it was
            function _whenInState(){
                spaceghost.options.waitTimeout = oldWaitTimeout;
                whenInStateFn.call( spaceghost, spaceghost.elementInfoOrNull( hdaSelector ) );
            },
            // if we've timed out, call the timeoutFn and close up
            function _timeout(){
                spaceghost.options.waitTimeout = oldWaitTimeout;
                var hdaInfo = spaceghost.elementInfoOrNull( hdaSelector );
                if( utils.isFunction( timeoutFn ) ){
                    timeoutFn.call( spaceghost, hdaInfo );

                // timeoutFn default - raise an error on timeout
                } else {
                    spaceghost.error( 'Timeout: final hda: ' + spaceghost.jsonStr( hdaInfo ) );
                    throw new spaceghost.GalaxyError(
                        'Timeout: waiting for ' + hdaSelector + ' to enter state: ' + finalState );
                }
            }
        );
    });
    return spaceghost;
};

/** Deletes an hda by finding an hda with the given title and clicking on the delete icon.
 *      NOTE: if more than one is found, the first found will be deleted.
 *      NOTE: is more than one Casper step.
 *  @param {String} hdaSelector     a css or xpath selector for an historyItemWrapper
 *  @param {Function} whenDeletedFn function to be called when the hda is deleted (optional)
 *  @param {Function} timeoutFn     function to be called if/when the deleted attempted times out (optional)
 */
HistoryPanel.prototype.deleteHda = function deleteHda( hdaSelector, whenDeletedFn, timeoutFn ){
    this.then( function deletingHda(){
        var hdaId = this.getElementInfo( hdaSelector ).attributes.id,
            deleteIconSelector = '#' + hdaId + ' ' + this.historypanel.data.hdaTitleButtons['delete'].selector;
        this.click( deleteIconSelector );

        this.waitWhileSelector( '#' + hdaId,
            function hdaNoLongerInDom(){
                this.info( 'hda deleted: ' + hdaSelector );
                if( utils.isFunction( whenDeletedFn ) ){ whenDeletedFn.call( spaceghost ); }

            //TODO: test timeouts by cutting delete fn
            }, function timeout(){
                if( utils.isFunction( timeoutFn ) ){
                    timeoutFn.call( spaceghost );
                } else {
                    throw new this.GalaxyError( 'Timeout: attempting to delete hda : ' + hdaSelector );
                }
            });
    });
    return spaceghost;
};

/** Undeletes an hda by including deleted in the panel, clicking undelete, and turning off include deleted
 *      NOTE: if more than one is found, the first found will be undeleted.
 *      NOTE: is more than one Casper step.
 *  @param {String} hdaSelector     a css or xpath selector for an historyItemWrapper
 *  @param {Function} whenDeletedFn function to be called when the hda is deleted (optional)
 */
HistoryPanel.prototype.undeleteHda = function undeleteHda( hdaSelector, whenUndeletedFn ){
    this.spaceghost.historyoptions.includeDeleted( function(){
        this.click( hdaSelector + ' ' + this.historypanel.data.selectors.history.undeleteLink );
        this.historyoptions.excludeDeleted( function(){
            this.info( 'hda undeleted: ' + hdaSelector );
            if( utils.isFunction( whenUndeletedFn ) ){ whenUndeletedFn.call( this ); }
        });
        //TODO:?? no timeout fn?
    });
};

// =================================================================== SELECTORS
//TODO: data is not a very good name
HistoryPanel.prototype.data = {
    hdaTitleButtons : {
        // mixing text and selectors here
        display : {
            selector : '.icon-button.display',
            tooltip  : 'Display data in browser',
            hrefTpl  : '/datasets/%s/display',
            nodeName : 'a'
        },
        edit : {
            selector : '.icon-button.edit',
            tooltip  : 'Edit Attributes',
            hrefTpl  : '/datasets/%s/edit',
            nodeName : 'a'
        },
        'delete' : {
            selector : '.icon-button.delete',
            tooltip  : 'Delete',
            hrefTpl  : '/datasets/%s/delete_async',
            nodeName : 'a'
        }
    },
    selectors : {
        history : {
            name        : 'div#history-name',
            subtitle    : 'div#history-subtitle-area',
            tagIcon     : '#history-tag.icon-button',
            tagArea     : '#history-tag-area',
            annoIcon    : '#history-annotate.icon-button',
            annoArea    : '#history-annotation-area',
            // weak
            emptyMsg    : '.infomessagesmall',
            undeleteLink : '.historyItemUndelete',
            hdaContainer : '.history-datasets-list'
        },
        hda : {
            wrapper : {
                itemClass   : '.historyItem',
                stateClasses : {
                    prefix  : 'historyItem-',
                    ok      : 'historyItem-ok',
                    'new'   : 'historyItem-new'
                }
            },
            title           : '.historyItemTitle',
            titleButtonArea : '.historyItemButtons',
            body            : '.historyItemBody',
            summary         : '.hda-summary',
            dbkey           : '.metadata-dbkey',
            info            : '.hda-info',
            primaryActionButtons    : 'div[id^="primary-actions"]',
            secondaryActionButtons  : 'div[id^="secondary-actions"]',
            peek            : 'pre.peek'
        }
    },
    labels : {
        history : {
        },
        hda : {
        }
    },
    text : {
        windowTitle : 'History',
        frameTitle : 'Galaxy History',
        anonymous : {
            tooltips : {
                name    : 'You must be logged in to edit your history name'
            }
        },
        history : {
            tooltips : {
                name     : 'Click to rename history',
                tagIcon  : 'Edit history tags',
                annoIcon : 'Edit history annotation'
            },
            newName  : 'Unnamed history',
            newSize  : '0 bytes',
            emptyMsg : "Your history is empty. Click 'Get Data' on the left pane to start"
        }
    }
};
