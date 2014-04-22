/** en/main localization hash - for use with requirejs' i18n plugin */
define({
    root : {

// ---------------------------------------------------------------------------- histories
// ---- history-model
// ---- readonly-history-panel
"This history is empty" :
false,
"No matching datasets found" :
false,
"An error occurred while getting updates from the server" :
false,
"Please contact a Galaxy administrator if the problem persists" :
false,
//TODO:
//"An error was encountered while <% where %>" :
//false,
"Search datasets" :
false,
"You are currently viewing a deleted history!" :
false,
"You are over your disk quota" :
false,
"Tool execution is on hold until your disk usage drops below your allocated quota" :
false,
"All" :
false,
"None" :
false,
"For all selected" :
false,

// ---- history-panel
"Edit history tags" :
false,
"Edit history Annotation" :
false,
"Click to rename history" :
false,
// multi operations
"Operations on multiple datasets" :
false,
"Hide datasets" :
false,
"Unhide datasets" :
false,
"Delete datasets" :
false,
"Undelete datasets" :
false,
"Permanently delete datasets" :
false,
"This will permanently remove the data in your datasets. Are you sure?" :
false,

// ---- annotated-history-panel
"Dataset" :
false,
"Annotation" :
false,

// ---- current-history-panel
"This history is empty. Click 'Get Data' on the left tool menu to start" :
false,
"No matching datasets found" :
false,
"You must be logged in to create histories" :
false,
//TODO:
//"You can <% loadYourOwn %> or <% externalSource %>" :
//false,
//"load your own data" :
//false,
//"get data from an external source" :
//false,

// these aren't in zh/ginga.po and the template doesn't localize
//"Include Deleted Datasets" :
//false,
//"Include Hidden Datasets" :
//false,


// ---------------------------------------------------------------------------- datasets
// ---- hda-model
"Unable to purge dataset" :
false,

// ---- hda-base
// display button
"Cannot display datasets removed from disk" :
false,
"This dataset must finish uploading before it can be viewed" :
false,
"This dataset is not yet viewable" :
false,
"View data" :
false,
// download button
"Download" :
false,
"Download dataset" :
false,
"Additional files" :
false,
// info/show_params
"View details" :
false,

// dataset states
// state: new
"This is a new dataset and not all of its data are available yet" :
false,
// state: noPermission
"You do not have permission to view this dataset" :
false,
// state: discarded
"The job creating this dataset was cancelled before completion" :
false,
// state: queued
"This job is waiting to run" :
false,
// state: upload
"This dataset is currently uploading" :
false,
// state: setting_metadata
"Metadata is being auto-detected" :
false,
// state: running
"This job is currently running" :
false,
// state: paused
"This job is paused. Use the \"Resume Paused Jobs\" in the history menu to resume" :
false,
// state: error
"An error occurred with this dataset" :
false,
// state: empty
"No data" :
false,
// state: failed_metadata
"An error occurred setting the metadata for this dataset" :
false,

// ajax error prefix
"There was an error getting the data for this dataset" :
false,

// purged'd/del'd msg
"This dataset has been deleted and removed from disk" :
false,
"This dataset has been deleted" :
false,
"This dataset has been hidden" :
false,

"format" :
false,
"database" :
false,

// ---- hda-edit
"Edit attributes" :
false,
"Cannot edit attributes of datasets removed from disk" :
false,
"Undelete dataset to edit attributes" :
false,
"This dataset must finish uploading before it can be edited" :
false,
"This dataset is not yet editable" :
false,

"Delete" :
false,
"Dataset is already deleted" :
false,

"View or report this error" :
false,

"Run this job again" :
false,

"Visualize" :
false,
"Visualize in" :
false,

"Undelete it" :
false,
"Permanently remove it from disk" :
false,
"Unhide it" :
false,

"You may be able to" :
false,
"set it manually or retry auto-detection" :
false,

"Edit dataset tags" :
false,
"Edit dataset annotation" :
false,


// ---------------------------------------------------------------------------- misc. MVC
"Tags" :
false,
"Annotation" :
false,
"Edit annotation" :
false,


// ----------------------------------------------------------------------------
},
    'ja'  : true,
    'zh'  : true
});
