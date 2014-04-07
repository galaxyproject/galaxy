// =================================================================== module object, exports
/** Creates a new historyoptions module object.
 *  @exported
 */
exports.create = function createHistoryOptions( spaceghost ){
    return new HistoryOptions( spaceghost );
};

/** HistoryOptions object constructor.
 *  @param {SpaceGhost} spaceghost a spaceghost instance
 */
var HistoryOptions = function HistoryOptions( spaceghost ){
    //??: circ ref?
    this.spaceghost = spaceghost;
};
exports.HistoryOptions = HistoryOptions;

HistoryOptions.prototype.toString = function toString(){
    return this.spaceghost + '.HistoryOptions';
};

// -------------------------------------------------------------------
/* TODO:
    some of the fns below can be applied to any popup


*/
// =================================================================== internal
var require = patchRequire( require ),
    xpath = require( 'casper' ).selectXPath;

// =================================================================== API (external)
/** Just open the menu
 *  @param {Function} fn function to call when the menu opens
 *  @returns {Any} the return value of fn
 */
HistoryOptions.prototype.openMenu = function openMenu( fn ){

    return this.spaceghost.jumpToTop( function(){
        if( !spaceghost.visible( this.historyoptions.data.selectors.menu ) ){
            this.click( this.historyoptions.data.selectors.button );
        }
        return fn.call( this );
    });
};

/** Click an option by Label
 *  @param {String} optionLabel the label of the option to click (can be partial?)
 *  @returns {SpaceGhost} for chaining
 */
HistoryOptions.prototype.clickOption = function clickOption( optionLabel ){
    this.openMenu( function(){
        this.click( this.historyoptions.data.selectors.optionXpathByLabelFn( optionLabel ) );
        // shouldnt need to clear - clicking an option will do that
    });
    return this.spaceghost;
};

/** Is the history option with the given label showing as toggled?
 *  @param {String} optionLabel the label of the option to check (can be partial?)
 *  @returns {Boolean} true if the option is on, false if off OR not a toggle
 */
HistoryOptions.prototype.isOn = function isOn( optionLabel ){
    return this.openMenu( function(){
        var toggleIconInfo = this.elementInfoOrNull(
            this.historyoptions.data.selectors.optionIsOnXpathByLabelFn( optionLabel ) );
        // have to clear manually
        this.click( 'body' );
        return !!toggleIconInfo;
    });
};

/** Toggle the option - optionally forcing to on or off.
 *  @param {String} optionLabel the label of the option to check (can be partial?)
 *  @param {Boolean} force  if true ensure option is on, if false ensure it's off,
 *      if undefined simply toggle
 *  @returns {Boolean} true if the option is now on, false if now off or not a toggle
 */
HistoryOptions.prototype.toggle = function toggle( optionLabel, force ){
    var isOn = this.isOn( optionLabel );
    if( ( force === false && isOn )
    ||  ( force === true  && !isOn )
    ||  ( force === undefined ) ){
        return this.clickOption( optionLabel );
    }
    return force;
};

// -------------------------------------------------------------------
// these options lead to controller pages - encapsulate those pages here
/** corresponds to history options menu: 'Saved Histories'
 *  @param {String} historyName the name of the history
 */
//HistoryOptions.prototype.savedHistoryByName = function savedHistoryByName( historyName ){
//};
/** corresponds to history options menu: 'Histories Shared with Me'
 *  @param {String} historyName the name of the history
 */
//HistoryOptions.prototype.sharedHistoryByName = function sharedHistoryByName( historyName ){
//};

/** corresponds to history options menu: 'Create New'
 */
//HistoryOptions.prototype.createNew = function createNew(){
//};

/** corresponds to history options menu: 'Copy History'
 */
//HistoryOptions.prototype.copyHistory = function copyHistory(){
//};

/** corresponds to history options menu: 'Copy Datasets'
 */
//HistoryOptions.prototype.copyDatasets = function copyDatasets(){
//};

/** corresponds to history options menu: 'Extract Workflow'
 */
//HistoryOptions.prototype.extractWorkflow = function extractWorkflow(){
//};

/** corresponds to history options menu: 'Share or Publish'
 */
//HistoryOptions.prototype.shareHistoryViaLink = function shareHistoryViaLink(){
//};
/** corresponds to history options menu: 'Share or Publish'
 */
//HistoryOptions.prototype.publishHistory = function publishHistory(){
//};
/** corresponds to history options menu: 'Share or Publish'
 */
//HistoryOptions.prototype.shareHistoryWithUser = function shareHistoryWithUser(){
//};

/** corresponds to history options menu: 'Dataset Security'
 */
//HistoryOptions.prototype.managePermissions = function managePermissions(){
//};
/** corresponds to history options menu: 'Dataset Security'
 */
//HistoryOptions.prototype.accessPermissions = function accessPermissions(){
//};

/** corresponds to history options menu: 'Resume Paused Jobs'
 */
//HistoryOptions.prototype.resumePausedJobs = function resumePausedJobs(){
//};


// ------------------------------------------------------------------- check the togglable options
// these are easy, one click options (they don't open a new page)
/** Is 'Include Deleted Datasets' on (accrd. to the menu)?
 */
HistoryOptions.prototype.deletedAreIncluded = function deletedAreIncluded(){
    return this.isOn( this.data.labels.options.includeDeleted );
};
/** Is 'Include Deleted Datasets' on (accrd. to the menu)?
 */
HistoryOptions.prototype.hiddenAreIncluded = function hiddenAreIncluded(){
    return this.isOn( this.data.labels.options.includeHidden );
};

// ------------------------------------------------------------------- options that control the hpanel
/** corresponds to history options menu: 'Collapse Expanded Datasets'
 */
HistoryOptions.prototype.collapseExpanded = function collapseExpanded( then ){
    return this.spaceghost.then( function(){
        this.historyoptions.clickOption( this.historyoptions.data.labels.options.collapseExpanded );
        this.wait( 500, then );
    });
};

/** set 'Include Deleted Datasets' to on
 *  @param {Function} then  casper step to run when option is set
 */
HistoryOptions.prototype.includeDeleted = function includeDeleted( then ){
    this.toggle( this.data.labels.options.includeDeleted, true );
    this.spaceghost.historypanel.waitForHdas( then );
};

/** set 'Include Deleted Datasets' to off
 *  @param {Function} then  casper step to run when option is set
 */
HistoryOptions.prototype.excludeDeleted = function excludeDeleted( then ){
    this.toggle( this.data.labels.options.includeDeleted, false );
    this.spaceghost.historypanel.waitForHdas( then );
};

/** set 'Include Hidden Datasets' to on
 *  @param {Function} then  casper step to run when option is set
 */
HistoryOptions.prototype.includeHidden = function includeHidden( then ){
    this.toggle( this.data.labels.options.includeHidden, true );
    this.spaceghost.historypanel.waitForHdas( then );
};

/** set 'Include Hidden Datasets' to off
 *  @param {Function} then  casper step to run when option is set
 */
HistoryOptions.prototype.excludeHidden = function excludeHidden( then ){
    this.toggle( this.data.labels.options.includeHidden, false );
    this.spaceghost.historypanel.waitForHdas( then );
};


// =================================================================== SELECTORS
//TODO: data is not a very good name
HistoryOptions.prototype.data = {
    selectors : {
        button      : '#history-options-button',
        buttonIcon  : '#history-options-button span.fa-cog',
        menu        : '#history-options-button-menu',
        optionXpathByLabelFn : function optionXpathByLabelFn( label ){
            return xpath( '//ul[@id="history-options-button-menu"]/li/a[text()[contains(.,"' + label + '")]]' );
        },
        optionIsOnXpathByLabelFn : function optionIsOnXpathByLabelFn( label ){
            return xpath( '//ul[@id="history-options-button-menu"]/li/a[text()[contains(.,"' + label + '")]]'
                        + '/span[@class="fa fa-check"]' );
        }
    },
    labels : {
        options : {
            //History Lists
            savedHistories          : "Saved Histories",
            sharedHistories         : "Histories Shared with Me",
            //Current History
            createNew               : "Create New",
            copyHistory             : "Copy History",
            copyDatasets            : "Copy Datasets",
            shareOrPublish          : "Share or Publish",
            extractWorkflow         : "Extract Workflow",
            datasetSecurity         : "Dataset Security",
            resumePausedJobs        : "Resume Paused Jobs",
            collapseExpanded        : 'Collapse Expanded Datasets',
            includeDeleted          : 'Include Deleted Datasets',
            includeHidden           : 'Include Hidden Datasets',
            unhideHiddenDatasets    : "Unhide Hidden Datasets",
            purgeDeletedDatasets    : "Purge Deleted Datasets",
            showStructure           : "Show Structure",
            exportToFile            : "Export to File",
            deleteHistory           : "Delete",
            deleteHistoryPermanently : "Delete Permanently",
            //Other Actions
            importFromFile          : "Import from File"
        }
    }
};
