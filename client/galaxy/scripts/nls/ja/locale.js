/** ja localization */
define({

// ---------------------------------------------------------------------------- histories
// ---- history-model
// ---- history-view
"This history is empty" :
    "ヒストリーは空です",
"No matching datasets found" :
    "一致するデータセットが見つかりませんでした",
//"An error occurred while getting updates from the server" :
//false,
//"Please contact a Galaxy administrator if the problem persists" :
//false,
//TODO:
//"An error was encountered while <% where %>" :
//false,
"Search datasets" :
    "データセットを検索する",
"You are currently viewing a deleted history!" :
    "消去したヒストリーをみています。",
"You are over your disk quota" :
    "あなたはディスククォータを超えている",
//"Tool execution is on hold until your disk usage drops below your allocated quota" :
//false,
"All" :
    "一式",
"None" :
    "なし",
"For all selected" :
    "各項目を",

// ---- history-view-edit
//"Edit history tags" :
//false,
//"Edit history Annotation" :
//false,
"Click to rename history" :
    "ヒストリーの名前を変更するにはクリック",
// multi operations
"Operations on multiple datasets" :
    "複数のデータセットに対する操作",
//"Hide datasets" :
//false,
//"Unhide datasets" :
//false,
//"Delete datasets" :
//false,
//"Undelete datasets" :
//false,
"Permanently delete datasets" :
    "永久にデータセットを削除",
"This will permanently remove the data in your datasets. Are you sure?" :
    "これは永久にあなたのデータセット内のデータを削除します。本当に？",

// ---- history-view-annotated
"Dataset" :
    "データセット",
//"Annotation" :
//false,

// ---- history-view-edit-current
"This history is empty. Click 'Get Data' on the left tool menu to start" :
    "ヒストリーは空です。解析をはじめるには、左パネルの 'データ取得' をクリック",
"You must be logged in to create histories" :
    "ヒストリーを作成するためにはログインする必要があります",
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
//"Unable to purge dataset" :
//false,

// ---- hda-base
// display button
//"Cannot display datasets removed from disk" :
//false,
//"This dataset must finish uploading before it can be viewed" :
//false,
//"This dataset is not yet viewable" :
//false,
"View data" :
    "データを表示",
// download button
"Download" :
    "ダウンロード",
"Download dataset" :
    "データセットをダウンロード",
//"Additional files" :
//false,
// info/show_params
"View details" :
    "細部を表示",

// dataset states
// state: new
//"This is a new dataset and not all of its data are available yet" :
//false,
// state: noPermission
//"You do not have permission to view this dataset" :
//false,
// state: discarded
//"The job creating this dataset was cancelled before completion" :
//false,
// state: queued
"This job is waiting to run" :
    "ジョブは実行待ちです",
// state: upload
//"This dataset is currently uploading" :
//false,
// state: setting_metadata
//"Metadata is being auto-detected" :
//false,
// state: running
"This job is currently running" :
    "ジョブは実行中です",
// state: paused
//"This job is paused. Use the \"Resume Paused Jobs\" in the history menu to resume" :
//false,
// state: error
"An error occurred with this dataset" :
    "このジョブの実行中に発生したエラー",
// state: empty
"No data" :
    "データ無し",
// state: failed_metadata
//"An error occurred setting the metadata for this dataset" :
//false,

// ajax error prefix
//"There was an error getting the data for this dataset" :
//false,

// purged'd/del'd msg
"This dataset has been deleted and removed from disk" :
    "このデータセットは、永続的にディスクから削除されました",
"This dataset has been deleted" :
    "このデータセットは削除されました",
"This dataset has been hidden" :
    "このデータセットは、非表示にされた",

"format" :
    "フォーマット",
"database" :
    "データベース",

// ---- hda-edit
"Edit attributes" :
    "変数を編集する",
//"Cannot edit attributes of datasets removed from disk" :
//false,
//"Undelete dataset to edit attributes" :
//false,
//"This dataset must finish uploading before it can be edited" :
//false,
//"This dataset is not yet editable" :
//false,

"Delete" :
    "削除する",
//"Dataset is already deleted" :
//false,

"View or report this error" :
    "このエラーを届け出る",

"Run this job again" :
    "もう一度このジョブを実行する",

"Visualize" :
    "可視化する",
//"Visualize in" :
//false,

"Undelete it" :
    "復元する",
"Permanently remove it from disk" :
    "永久にディスクから削除",
"Unhide it" :
    "非表示解除する",

//"You may be able to" :
//false,
//"set it manually or retry auto-detection" :
//false,

//"Edit dataset tags" :
//false,
//"Edit dataset annotation" :
//false,


// ---------------------------------------------------------------------------- misc. MVC
//"Tags" :
//false,
//"Annotation" :
//false,
//"Edit annotation" :
//false,


});
