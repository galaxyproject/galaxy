/** ja localization */
define({
    // ----------------------------------------------------------------------------- masthead
    "Analyze Data": "データ解析",
    Workflow: "ワークフロー",
    "Shared Data": "共有データ",
    "Data Libraries": "データライブラリ",
    Histories: "ヒストリー",
    Workflows: "ワークフロー",
    Visualizations: "可視化",
    Pages: "ページ",
    Visualization: "可視化",
    "New Track Browser": "新しい Track Browser",
    "Saved Visualizations": "保存された可視化",
    Admin: "管理者",
    Help: "ヘルプ",
    Support: "サポート",
    Search: "検索",
    Support: "サポート",
    Search: "検索",
    "Mailing Lists": "メーリングリスト",
    Videos: "動画",
    "Community Hub": "コミュニティハブ",
    "How to Cite Galaxy": "Galaxy を引用する方法",
    "Interactive Tours": "インタラクティブツアー",
    User: "ユーザー",
    Login: "ログイン",
    Register: "登録",
    "Log in or Register": "ログイン/登録",
    Preferences: "設定",
    "Custom Builds": "カスタムビルド",
    Logout: "ログアウト",
    "Saved Histories": "保存されたヒストリー",
    "Saved Datasets": "保存されたデータセット",
    "Saved Pages": "保存されたページ",
    //Tooltip
    "Account and saved data": "アカウントと保存されたデータ",
    "Account registration or login": "アカウントの登録またはログイン",
    "Support, contact, and community": "サポート、コンタクト、コミュニティ",
    "Administer this Galaxy": "この Galaxy の管理者",
    "Visualize datasets": "データセットの可視化",
    "Access published resources": "パブリッシュされたリソースへアクセス",
    "Chain tools into workflows": "ツールとワークフローの連携",
    "Analysis home view": "解析ホーム",

    // ---------------------------------------------------------------------------- histories
    "History Lists": "ヒストリーリスト",
    // Saved histories is defined above.
    // "Saved Histories":
    //     false,
    "Histories Shared with Me": "私と共有されているヒストリー",
    "Current History": "現在のヒストリー",
    "Create New": "新しく作成",
    "Copy History": "ヒストリーをコピーする",
    "Share or Publish": "共有またはパブリッシュ",
    "Show Structure": "構造を見る",
    "Extract Workflow": "ワークフローを抽出",
    // Delete is defined elsewhere, but is also in this menu.
    // "Delete":
    //     false,
    "Delete Permanently": "永久に削除",
    "Dataset Actions": "データセットの操作",
    "Copy Datasets": "データセットをコピー",
    "Dataset Security": "データセットのセキュリティ",
    "Resume Paused Jobs": "一時停止したジョブの再開",
    "Collapse Expanded Datasets": "展開されたデータセットを畳む",
    "Unhide Hidden Datasets": "隠されたデータセットを表示する",
    "Delete Hidden Datasets": "隠されたデータセットを削除する",
    "Purge Deleted Datasets": "削除されたデータセットを永久に削除",
    Downloads: "ダウンロード",
    "Export Tool Citations": "ツールの引用をエクスポート",
    "Export History to File": "ヒストリーをファイルへエクスポート",
    "Other Actions": "その他のアクション",
    "Import from File": "ファイルからインポート",
    Webhooks: "Webhooks",
    // ---- history-model
    // ---- history-view
    "This history is empty": "ヒストリーは空です",
    "No matching datasets found": "一致するデータセットが見つかりませんでした",
    "An error occurred while getting updates from the server": "サーバーから更新を取得中にエラーが起こりました",
    //false,
    //"Please contact a Galaxy administrator if the problem persists" :
    //false,
    //TODO:
    //"An error was encountered while <% where %>" :
    //false,
    "Search datasets": "データセットを検索する",
    "You are currently viewing a deleted history!": "消去したヒストリーをみています。",
    "You are over your disk quota": "あなたはディスククォータを超えている",
    "Tool execution is on hold until your disk usage drops below your allocated quota":
        "ディスク使用料があなたに割り当てられたクォータを下回るまでツールの実行は停止します",
    //false,
    All: "一式",
    None: "なし",
    "For all selected": "各項目を",

    // ---- history-view-edit
    "Edit history tags": "ヒストリーのタグを編集",
    "Edit history annotation": "ヒストリーのアノテーションを編集",
    "Click to rename history": "ヒストリーの名前を変更するにはクリック",
    // multi operations
    "Operations on multiple datasets": "複数のデータセットに対する操作",
    "Hide datasets": "データセットを隠す",
    //false,
    "Unhide datasets": "隠れたデータセットの回復",
    //false,
    "Delete datasets": "データセットの削除",
    //false,
    "Undelete datasets": "削除されたデータセットの回復",
    //false,
    "Permanently delete datasets": "永久にデータセットを削除",
    "This will permanently remove the data in your datasets. Are you sure?":
        "これは永久にあなたのデータセット内のデータを削除します。本当に？",

    // ---- history-view-annotated
    Dataset: "データセット",
    Annotation: "アノテーション",
    //false,

    // ---- history-view-edit-current
    "This history is empty. Click 'Get Data' on the left tool menu to start":
        "ヒストリーは空です。解析をはじめるには、左パネルの 'データ取得' をクリック",
    "You must be logged in to create histories": "ヒストリーを作成するためにはログインする必要があります",
    //TODO:
    //"You can <% loadYourOwn %> or <% externalSource %>" :
    //false,
    "load your own data": "自分のデータをロード",
    //false,
    "get data from an external source": "外部のソースからデータを取得",
    //false,

    // these aren't in zh/ginga.po and the template doesn't localize
    "Include Deleted Datasets": "削除されたデータセットを含める",
    //false,
    "Include Hidden Datasets": "隠れたデータセットを含める",
    //false,

    // ---------------------------------------------------------------------------- datasets
    // ---- hda-model
    "Unable to purge dataset": "データセットを完全削除出来ません",
    //false,

    // ---- hda-base
    // display button
    "Cannot display datasets removed from disk": "ディスクから消去されたデータは表示できません",
    //false,
    "This dataset must finish uploading before it can be viewed":
        "このデータセットは見る前にアップロードが完了する必要があります",
    //false,
    "This dataset is not yet viewable": "このデータセットはまだ見ることができません",
    //false,
    "View data": "データを表示",
    // download button
    Download: "ダウンロード",
    "Download dataset": "データセットをダウンロード",
    "Additional files": "追加のファイル",
    //false,
    // info/show_params
    "View details": "細部を表示",

    // dataset states
    // state: new
    "This is a new dataset and not all of its data are available yet":
        "これは新しいデータセットですが、まだすべてのデータが利用可能にはなっていません",
    //false,
    // state: noPermission
    "You do not have permission to view this dataset": "このデータセットを見るための権限がありません",
    //false,
    // state: discarded
    "The job creating this dataset was cancelled before completion":
        "このデータセットを作成するジョブは、完了する前にキャンセルされました",
    //false,
    // state: queued
    "This job is waiting to run": "ジョブは実行待ちです",
    // state: upload
    "This dataset is currently uploading": "このデータセットは現在アップロード中です",
    //false,
    // state: setting_metadata
    //"Metadata is being auto-detected" :
    //false,
    // state: running
    "This job is currently running": "ジョブは実行中です",
    // state: paused
    //"This job is paused. Use the \"Resume Paused Jobs\" in the history menu to resume" :
    //false,
    // state: error
    "An error occurred with this dataset": "このジョブの実行中に発生したエラー",
    // state: empty
    "No data": "データ無し",
    // state: failed_metadata
    "An error occurred setting the metadata for this dataset":
        "このデータセットのメタデータを設定する際にエラーがでました",
    //false,

    // ajax error prefix
    "There was an error getting the data for this dataset": "このデータセットのデータを取得する際にエラーがでました",
    //false,

    // purged'd/del'd msg
    "This dataset has been deleted and removed from disk": "このデータセットは、永続的にディスクから削除されました",
    "This dataset has been deleted": "このデータセットは削除されました",
    "This dataset has been hidden": "このデータセットは、非表示にされた",

    format: "フォーマット",
    database: "データベース",

    // ---- hda-edit
    "Edit attributes": "変数を編集する",
    "Cannot edit attributes of datasets removed from disk": "ディスクから削除されたデータセットの属性は編集できない",
    //false,
    //"Undelete dataset to edit attributes" :
    //false,
    "This dataset must finish uploading before it can be edited":
        "このデータセットは編集する前にアップロードが完了する必要がある",
    //false,
    "This dataset is not yet editable": "このデータセットは、まだ編集可能ではない",
    //false,

    Delete: "削除する",
    "Dataset is already deleted": "データセットは、既に削除されている",
    //false,

    "View or report this error": "このエラーを届け出る",

    "Run this job again": "もう一度このジョブを実行する",

    Visualize: "可視化する",
    //"Visualize in" :
    //false,

    "Undelete it": "復元する",
    "Permanently remove it from disk": "永久にディスクから削除",
    "Unhide it": "非表示解除する",
    "Saved Histories": "保存されたヒストリ",
    "Import from File": "ファイルからの読み込み",

    //"You may be able to" :
    //false,
    //"set it manually or retry auto-detection" :
    //false,

    "Edit dataset tags": "データセットのタグを編集",
    //false,
    "Edit dataset annotation": "データセットのアノテーションを編集",
    //false,

    // ---------------------------------------------------------------------------- admin
    "Search Tool Shed": "Tool Shed で探す",
    "Search Tool Shed (Beta)": "Tool Shed (Beta) で探す",
    "Monitor installing repositories": "インストールレポジトリのモニタ",
    "Manage installed tools": "インストールしたツールの管理",
    "Reset metadata": "メタデータのリセット",
    "Download local tool": "ローカルツールのダウンロード",
    "Tool lineage": "ツール系統",
    "Reload a tool's configuration": "ツールのコンフィグのリロード",
    "View Tool Error Logs": "ツールのエラーログ",
    "Manage Allowlist": "表示ホワイトリストの管理",
    "Manage Tool Dependencies": "ツール依存関係の管理",
    Users: "ユーザー",
    Groups: "グループ",
    "API keys": "API キー",
    "Impersonate a user": "ユーザー偽装",
    Data: "データ",
    Quotas: "クォータ",
    Roles: "ロール",
    "Local data": "ローカルデータ",
    "Form definitions": "フォーム定義",
    Administration: "管理",
    Server: "サーバー",
    "Tools and Tool Shed": "ツールと Tool Shed",
    "User Management": "ユーザ管理",
    Data: "データ",
    "Form Definitions": "フォーム定義",
    // ---------------------------------------------------------------------------- misc. MVC
    Tags: "タグ",
    //false,
    Annotation: "アノテーション",
    //false,
    "Edit annotation": "アノテーションを編集",
    //false,
    "Your workflows": "あなたのワークフロー",
});
