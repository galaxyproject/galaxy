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


*/
// =================================================================== API (external)
/** Just open the menu
 */
HistoryOptions.prototype.openMenu = function openMenu(){
    this.spaceghost.click( this.data.selectors.button );
};

/** Click an option by Label
 */
HistoryOptions.prototype.clickOption = function clickOption( optionLabel ){
    this.openMenu();
    // casperjs clickLabel
    var optionXpath = this.data.selectors.optionXpathByLabelFn( optionLabel );
    this.spaceghost.click( optionXpath );
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


// -------------------------------------------------------------------
// these are easy, one click options (they don't open a new page)
/** corresponds to history options menu: 'Collapse Expanded Datasets'
 */
HistoryOptions.prototype.collapseExpanded = function collapseExpanded(){
    this.clickOption( this.data.labels.options.collapseExpanded );
};
/** corresponds to history options menu: 'Include Deleted Datasets'
 */
HistoryOptions.prototype.includeDeleted = function includeDeleted(){
    this.clickOption( this.data.labels.options.includeDeleted );
};
/** corresponds to history options menu: 'Include Hidden Datasets'
 */
HistoryOptions.prototype.includeHidden = function includeHidden(){
    this.clickOption( this.data.labels.options.includeHidden );
};


// =================================================================== SELECTORS
//TODO: data is not a very good name
HistoryOptions.prototype.data = {
    selectors : {
        button      : '#history-options-button',
        buttonIcon  : '#history-options-button span.fa-icon-cog',
        menu        : '#history-options-button-menu',
        optionXpathByLabelFn : function optionXpathByLabelFn( label ){
            return xpath( '//ul[@id="history-options-button-menu"]/li/a[text()[contains(.,"' + label + '")]]' );
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
