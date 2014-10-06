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
var require = patchRequire( require ),
    xpath = require( 'casper' ).selectXPath;

// =================================================================== API (external)
// ------------------------------------------------------------------- frame control
///** Hover over an element in the history panel.
// *  @param {String} selector        a css or xpath selector for an historyItemWrapper
// */
//HistoryPanel.prototype.hoverOver = function hoverOver( selector ){
//    var spaceghost = this.spaceghost,
//        elementInfo = spaceghost.getElementInfo( selector );
//    spaceghost.page.sendEvent( 'mousemove', elementInfo.x + 1, elementInfo.y + 1 );
//    return spaceghost;
//};

// ------------------------------------------------------------------- hdas
///** Parse the hid and name from an HDA title.
// *      NOTE: if more than one is found, will return the first found.
// *  @param {String} title   the title of the hda
// *  @returns {Object}       of the form { hid: <hid>, name: <name> }
// */
//HistoryPanel.prototype.hdaHidAndNameFromTitle = function hdaHidAndNameFromTitle( title ){
//    var sep = ': ', split = title.split( sep, 1 );
//    return {
//        name : (( split.length >= 2 )?( split[1] ):( split[0] )),
//        hid  : (( split.length >= 2 )?( parseInt( split[0], 10 ) ):( undefined ))
//    };
//};

/** Find the casper element info of the hda wrapper given the hda title.
 *      NOTE: if more than one is found, will return the first found.
 *  @param {String} title   the title of the hda
 *  @returns {Object|null} ElementInfo of the historyItemWrapper found, null if not found
 */
HistoryPanel.prototype.hdaElementInfoByTitle = function hdaElementInfoByTitle( title ){
    var wrapperXpath = xpath( '//span[@class="name" and contains(text(),"' + title + '")]/../../..' );
    return this.spaceghost.elementInfoOrNull( wrapperXpath );
};

/** Get the state string of the given hda.
 *      NOTE: if more than one is found, will return the first found.
 *  @param {Selector} title a selector for the desired hdaWrapper
 *  @returns {String|undefined}  class string of the historyItemWrapper found, undefined if not found or set
 */
HistoryPanel.prototype.getHdaState = function getHdaState( hdaSelector ){
    var found = null,
        hdaInfo = this.spaceghost.elementInfoOrNull( hdaSelector );
    if( !hdaInfo ){ return undefined; }
    return (( found = hdaInfo.attributes[ 'class' ].match( /state\-(\w+)/ ) )?( found[1] ):( undefined ));
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
/** Moves into history iframe and waits until hdas are visible or empty message is.
 *      NOTE: is more than one Casper step.
 *  @see Casper@waitFor
 */
HistoryPanel.prototype.waitForHdas = function waitForHdas( then, timeout, maxWait ){
    //TODO:?? should this wait until the seletors are in AND they are opaque?
    var spaceghost = this.spaceghost;
    spaceghost.then( function waitingForHdas(){
        this.waitFor(
            function checkHpanel(){
                var subtitleOpacity = this.evaluate( function( selector ){
                    return $( selector ).css( 'opacity' );
                }, this.historypanel.data.selectors.history.subtitle );
                // wait until the subtitle is faded in and either the hdas or the empty history msg is displayed
                return ( subtitleOpacity !== 1
                       && ( ( this.visible( this.historypanel.data.selectors.hda.wrapper.itemClass ) )
                          ||( this.visible( this.historypanel.data.selectors.history.emptyMsg ) ) ) );
            }, then, timeout, maxWait );
    });
    return spaceghost;
};

/** Moves into history iframe and waits until hdas are visible or empty message is.
 *      NOTE: is more than one Casper step.
 *  @see Casper@waitFor
 */
HistoryPanel.prototype.waitForHda = function waitForHda( hdaName, then, timeout, maxWait ){
    //TODO:?? should this wait until the seletors are in AND they are opaque?
    var spaceghost = this.spaceghost,
        hdaElement = null,
        previousState = null;
    spaceghost.then( function waitingForHda(){
        this.waitFor(
            function checkHpanel(){
                var wrapperXpath = xpath( '//span[contains(text(),"' + hdaName + '")]/../../..' );
                hdaElement = this.elementInfoOrNull( wrapperXpath );
                //NOTE: this will probably fail if the name was used on a previous HDA
                if( !hdaElement ){ return false; }
                
                var state = hdaElement.attributes[ "class" ].match( /state\-([\w\-_]*)/ )[1];
                if( state !== previousState ){
                    spaceghost.info( 'state: ' + state );
                    previousState = state;
                }
                if( state !== 'ok' ){ return false; }

                var hdaOpacity = this.evaluate( function( name ){
                    // locate the hda by name and return its opacity
                    console.debug( name );
                    console.debug( $( '.name:contains("' + name + '")' ) );
                    console.debug( $( '.name:contains("' + name + '")' ).parents( '.hda' ) );
                    return $( '.name:contains("' + name + '")' ).parents( '.dataset' ).css( 'opacity' );
                }, hdaName );
                //this.debug( 'fading in: ' + hdaOpacity );
                return hdaOpacity >= 1;
            },
            function _then(){ then.call( this, hdaElement ); },
            function _timeout(){ timeout.call( this, hdaElement ); },
            maxWait );
    });
    return spaceghost;
};

//TODO: combine with above
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

    this.spaceghost.then( function(){
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

/** Expands or collapses an HDA by clicking the title (does nothing if already in desired state).
 *      NOTE: is more than one Casper step.
 *  @param {String} hdaSelector     a css or xpath selector for an historyItemWrapper
 *  @param {Function} then          function called when the change is made
 *  @param {Boolean} desiredClosed  true if you want to collapse, false if you want open
 *  @private
 */
HistoryPanel.prototype._thenExpandOrCollapseHda = function _thenExpandOrCollapseHda( hdaSelector, then, desiredClosed ){
    // using a step here (instead of a jump) bc we need the wait for function
    this.spaceghost.then( function checkingHda(){
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

/** Deletes an hda by finding an hda with the given title and clicking on the delete icon.
 *      NOTE: if more than one is found, the first found will be deleted.
 *      NOTE: is more than one Casper step.
 *  @param {String} hdaSelector     a css or xpath selector for an historyItemWrapper
 *  @param {Function} whenDeletedFn function to be called when the hda is deleted (optional)
 *  @param {Function} timeoutFn     function to be called if/when the deleted attempted times out (optional)
 */
HistoryPanel.prototype.deleteHda = function deleteHda( hdaSelector, whenDeletedFn, timeoutFn ){
    this.spaceghost.then( function deletingHda(){
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
        this.click( hdaSelector + ' ' + this.historypanel.data.selectors.hda.undeleteLink );
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
            selector : '.icon-btn.display-btn',
            tooltip  : 'View data',
            hrefTpl  : '/datasets/%s/display',
            nodeName : 'a'
        },
        edit : {
            selector : '.icon-btn.edit-btn',
            tooltip  : 'Edit attributes',
            hrefTpl  : '/datasets/%s/edit',
            nodeName : 'a'
        },
        'delete' : {
            selector : '.icon-btn.delete-btn',
            tooltip  : 'Delete',
            hrefTpl  : 'javascript:void(0);',
            nodeName : 'a'
        }
    },
    hdaPrimaryActionButtons : {
        download : {
            selector : '.icon-btn.download-btn',
            tooltip  : 'Download',
            hrefTpl  : '/datasets/%s/display?to_ext=',
            nodeName : 'a'
        },
        info : {
            selector : '.icon-btn.params-btn',
            tooltip  : 'View details',
            hrefTpl  : '/datasets/%s/show_params',
            nodeName : 'a'
        },
        rerun : {
            selector : '.icon-btn.rerun-btn',
            tooltip  : 'Run this job again',
            hrefTpl  : '/tool_runner/rerun?id=%s',
            nodeName : 'a'
        },
        downloadDropdownButtonIdTpl : 'dataset-%s-popup',
        downloadDropdownMenuIdTpl : 'dataset-%s-popup-menu'
    },
    selectors : {
        history : {
            title       : '.controls .title',
            name        : '.title .name',
            nameEditableTextInput : '.name input',
            subtitle    : '.subtitle',
            size        : '.history-size',
            tagIcon     : '.actions .history-tag-btn',
            tagArea     : '.controls .tags-display',
            annoIcon    : '.actions .history-annotate-btn',
            annoArea    : '.controls .annotation-display',
            emptyMsg    : '.empty-message',
            hdaContainer: '.datasets-list'
        },
        hda : {
            wrapper : {
                itemClass   : '.history-content.dataset',
                stateClasses : {
                    prefix  : 'state-',
                    ok      : 'state-ok',
                    'new'   : 'state-new'
                }
            },
            errorMessage    : '.errormessagesmall',

            title           : '.title',
            titleButtonArea : '.primary-actions',
            summary         : '.summary',
            dbkey           : '.dbkey .value',
            info            : '.info',
            body            : '.details',
            
            primaryActionButtons    : '.actions .left',
            secondaryActionButtons  : '.actions .right',

            undeleteLink    : '.undelete-link',
            purgeLink       : '.purge-link',

            peek            : '.dataset-peek'
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
        //frameTitle : 'Galaxy History',
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
            emptyMsg : "This history is empty. You can load your own data or get data from an external source"
        },
        hda : {
            datasetFetchErrorMsg : 'There was an error getting the data for this dataset'
        }
    }
};
