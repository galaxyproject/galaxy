/** zh localization */
/* any suggestions, please contact me: ishenweiyan@foxmail.com */
define({
    // ----------------------------------------------------------------------------- masthead
    "Analyze Data": "数据分析",
    Workflow: "工作流程",
    "Shared Data": "数据共享",
    "Data Libraries": "数据库",
    "Published Histories": "历史",
    "Published Workflows": "流程",
    "Published Visualizations": "可视化",
    "Published Pages": "页面",
    Visualization: "可视化",
    "New Track Browser": "创建 Track Browser",
    "Saved Visualizations": "已保存的可视化",
    "Create Visualization": "创建可视化",
    Admin: "管理员",
    Help: "帮助",
    Support: "支持",
    Search: "搜索",
    "Mailing Lists": "邮件列表",
    Videos: "视频",
    Wiki: false,
    "How to Cite Galaxy": "引用",
    "Interactive Tours": "使用引导",
    User: "账号管理",
    Login: "登陆",
    Register: "注册",
    "Login or Register": "注册登陆",
    "Logged in as": "您已登陆为",
    Preferences: "用户偏好性",
    "Custom Builds": "自定义构建集",
    Logout: "退出",
    "Saved Histories": "保存的历史",
    "Saved Datasets": "保存的数据集",
    "Saved Pages": "保存的页面",
    Datasets: "我的数据集",
    Histories: "我的历史",
    "Histories shared with me": "分享给我的历史",
    Pages: "我的页面",
    Visualizations: "我的可视化",

    //Tooltip
    "Account and saved data": "账号及数据保存",
    "Account registration or login": "注册或登录",
    "Support, contact, and community": "社区支持与联系",
    "Administer this Galaxy": "管理您的 Galaxy",
    "Visualize datasets": "数据集可视化",
    "Access published resources": "访问已发布的资源",
    "Chain tools into workflows": "将工具链接到流程中",
    "Analysis home view": "数据分析主页",

    // ---------------------------------------------------------------------------- histories
    // ---- history/options-menu
    History: "历史",
    "History Actions": "历史记录操作",
    "History Lists": "历史记录列表",
    // Saved histories is defined above.
    "Saved Histories": "保存的历史",
    "Histories Shared with Me": "分享给您历史",
    "Current History": "当前历史记录",
    "Create New": "创建新的历史",
    Copy: "复制历史",
    "Share or Publish": "分享或发布历史",
    "Show Structure": "展示结构",
    "Extract Workflow": "提取为工作流",
    "Set Permissions": "设置权限",
    "Make Private": "私有化数据",
    // Delete is defined elsewhere, but is also in this menu.
    Delete: "删除",
    "Delete Permanently": "永久删除",
    "Dataset Actions": "数据集操作",
    "Copy Datasets": "复制数据集",
    "Dataset Security": "数据集安全",
    "Resume Paused Jobs": "恢复已暂停的任务",
    "Collapse Expanded Datasets": "折叠已展开的数据集",
    "Unhide Hidden Datasets": "取消隐藏的数据集",
    "Delete Hidden Datasets": "删除隐藏的数据集",
    "Purge Deleted Datasets": "清除已删除的数据集",
    Downloads: "下载",
    "Export Tool Citations": "导出工具引用的文献",
    "Export History to File": "导出历史到文件",
    "Other Actions": "其他操作",
    "Import from File": "从文件导入",
    Webhooks: false,

    // ---- history-model
    // ---- history-view
    "This history is empty": "您的历史记录为空",
    "No matching datasets found": "未找到匹配的数据集",
    "An error occurred while getting updates from the server": "服务器更新时出现错误",
    "Please contact a Galaxy administrator if the problem persists": "如果问题仍然存在，请联系 Galaxy 管理员",
    //TODO:
    "An error was encountered while <% where %>": "当执行以下操作时: <% where %>, 出现错误",
    "search datasets": "搜索数据集",
    "You are currently viewing a deleted history!": "您正在查看已删除的历史记录！",
    "You are over your disk quota": "您已超出了系统分配的磁盘配额",
    "Tool execution is on hold until your disk usage drops below your allocated quota":
        "工具暂停执行，直到您的磁盘使用量低于您所分配的配额",
    All: "全选",
    None: "反选",
    "For all selected": "为每个选定",

    // ---- history-view-edit
    "Edit history tags": "编辑历史标签",
    "Edit history annotation": "编辑历史备注",
    "Click to rename history": "点击以重命名历史",
    // multi operations
    "Operations on multiple datasets": "编辑多个数据集",
    "Hide datasets": "隐藏数据集",
    "Unhide datasets": "显示数据集",
    "Delete datasets": "删除数据集",
    "Undelete datasets": "取消删除数据集",
    "Permanently delete datasets": "永久删除数据集",
    "This will permanently remove the data in your datasets. Are you sure?":
        "本次操作将从您的数据集中用久移除数据。请再次确定？",

    // ---- history-view-annotated
    Dataset: "数据集",
    Annotation: "备注",

    // ---- history-view-edit-current
    "This history is empty. Click 'Get Data' on the left tool menu to start":
        "您的历史记录为空，请单击左边窗格中‘获取数据’",
    "You must be logged in to create histories": "您必须登录后才能创建历史",
    //TODO:
    "You can <% loadYourOwn %> or <% externalSource %>": "您可以 <% loadYourOwn %> 或者 <% externalSource %>",
    "You can ": "您可以 ",
    " or ": " 或者 ",
    "load your own data": "上传您的个人数据",
    "get data from an external source": "从其他来源上传数据.",

    // these aren't in zh/ginga.po and the template doesn't localize
    "Include Deleted Datasets": "包括删除数据集",
    "Include Hidden Datasets": "包括隐藏数据集",

    // ---------------------------------------------------------------------------- datasets
    // ---- hda-model
    "Unable to purge dataset": "无法清除数据集",

    // ---- hda-base
    // display button
    "Cannot display datasets removed from disk": "无法显示已从磁盘中移除的数据集",
    "This dataset must finish uploading before it can be viewed": "此数据集必须先完成上传, 才能查看",
    "This dataset is not yet viewable": "此数据集暂时不可见",
    "View data": "查看数据",
    // download button
    Download: "下载",
    "Download dataset": "下载数据集",
    "Additional files": "其他文件",
    // info/show_params
    "View details": "查看详情",

    // dataset states
    // state: new
    "This is a new dataset and not all of its data are available yet":
        "这是一个新的数据集，并不是所有与它关联的数据都可用",
    // state: noPermission
    "You do not have permission to view this dataset": "您无权查看此数据集",
    // state: discarded
    "The job creating this dataset was cancelled before completion": "创建此数据集的任务在完成之前已被取消",
    // state: queued
    "This job is waiting to run": "您的任务正在等待运行",
    // state: upload
    "This dataset is currently uploading": "领的数据集正在上传中",
    // state: setting_metadata
    "Metadata is being auto-detected": "元数据正在被自动检测中",
    // state: running
    "This job is currently running": "您的任务正在运行中",
    // state: paused
    'This job is paused. Use the "Resume Paused Jobs" in the history menu to resume':
        '此任务已暂停。您可以使用历史菜单中的 "恢复已暂停的任务" 来恢复',
    // state: error
    "An error occurred with this dataset": "此数据集发生错误",
    // state: empty
    "No data": "没有数据",
    // state: failed_metadata
    "An error occurred setting the metadata for this dataset": "设置此数据集的元数据时发生错误",

    // ajax error prefix
    "There was an error getting the data for this dataset": "获取此数据集的数据时出现错误",

    // purged'd/del'd msg
    "This dataset has been deleted and removed from disk": "此数据集已被删除且已经从系统磁盘中被清空",
    "This dataset has been deleted": "此数据集已被删除",
    "This dataset has been hidden": "此数据集已被隐藏",

    format: "格式",
    database: "数据库",

    // ---- hda-edit
    "Edit attributes": "编辑属性",
    "Cannot edit attributes of datasets removed from disk": "无法编辑已从磁盘中移除的数据集的属性",
    "Undelete dataset to edit attributes": "取消删除数据集以编辑属性",
    "This dataset must finish uploading before it can be edited": "该数据集必须先上传完成, 才能编辑",
    "This dataset is not yet editable": "该数据集不可编辑",

    Delete: "删除",
    "Dataset is already deleted": "数据集已被删除",

    "View or report this error": "查看或报告当前错误",

    "Run this job again": "重新运行当前任务",

    Visualize: "可视化",
    "Visualize in": "的可视化",

    "Undelete it": "取消删除",
    "Permanently remove it from disk": "从磁盘中永久移除",
    "Unhide it": "取消隐藏",

    "You may be able to": "您可以",
    "set it manually or retry auto-detection": "手动设置或重新执行自动检测",

    "Edit dataset tags": "编辑数据集标签",
    "Edit dataset annotation": "编辑数据集备注",

    "Tool Help": "工具帮助",

    // ---------------------------------------------------------------------------- admin
    "Reset passwords": false,
    "Search Tool Shed": false,
    "Monitor installing repositories": false,
    "Manage installed tools": false,
    "Reset metadata": false,
    "Download local tool": false,
    "Tool lineage": false,
    "Reload a tool's configuration": false,
    "View Tool Error Logs": false,
    "Manage Display Whitelist": false,
    "Manage Tool Dependencies": false,
    Users: false,
    Groups: false,
    "API keys": false,
    "Impersonate a user": false,
    Data: false,
    Quotas: false,
    Roles: false,
    "Local data": false,
    "Form Definitions": false,

    // ---------------------------------------------------------------------------- Window Manager
    "Enable/Disable Window Manager": "启用/禁用 Window Manager",
    "Show/Hide Window Manager": "显示/隐藏 Window Manager",

    // ---------------------------------------------------------------------------- misc. MVC
    Tags: "标签",
    "Edit annotation": "编辑备注",

    // ---------------------------------------------------------------------------- galaxy.pages
    Subscript: "下标",
    Superscript: "上标",
    // ---------------------------------------------------------------------------- data
    Trackster: false,
    Visualize: "可视化",
    // ---------------------------------------------------------------------------- dataset-error
    "Any additional comments you can provide regarding what you were doing at the time of the bug.":
        "您可以提供的关于 bug 发生时您正在做什么的任何信息。",
    "Your email address": "您的邮箱地址",
    Report: "报告",
    "Error Report": "错误报告",
    // ---------------------------------------------------------------------------- dataset-li
    "Dataset details": "数据集详情",
    // ---------------------------------------------------------------------------- dataset-edit-attributes
    "Save permissions.": "保存权限",
    "Change the datatype to a new type.": "将数据类型更改为新类型。",
    "Convert the datatype to a new format.": "将数据类型更改为新的格式。",
    "Save attributes of the dataset.": "保存数据集属性。",
    "Change data type": "更改数据类型",
    "Edit Dataset Attributes": "编辑数据集属性",
    "Save permissions": "保存权限",
    "Manage dataset permissions": "管理数据集权限",
    "Change datatype": "更改数据类型",
    "Convert datatype": "转换数据类型",
    "Convert to new format": "转换成新格式",
    Save: "保存",
    Permissions: "权限",
    Datatypes: "数据类型",
    Convert: "转换",
    Attributes: "属性",
    // ---------------------------------------------------------------------------- dataset-li-edit
    Visualization: "可视化",
    // ---------------------------------------------------------------------------- library-dataset-view
    "Import into History": "导入到历史记录中",
    // ---------------------------------------------------------------------------- library-foldertoolbar-view
    "Location Details": "位置的细节",
    "Deleting selected items": "删除选择的条目",
    "Please select folders or files": "请选择目录或者文件",
    "Please enter paths to import": "请填写路径进行导入",
    "Adding datasets from your history": "从您的历史记录中添加数据集",
    "Create New Folder": "创建新的目录",
    // ---------------------------------------------------------------------------- library-librarytoolbar-view
    "Create New Library": "创建新的库",
    // ---------------------------------------------------------------------------- tours
    Tours: "引导",
    // ---------------------------------------------------------------------------- user-preferences
    "Click here to sign out of all sessions.": "点击这里退出所有会话。",
    "Add or remove custom builds using history datasets.": "从历史的数据集中添加或者移除自定义的构建集。",
    "Associate OpenIDs with your account.": "把 OpenIDs 和您的账号进行关联。",
    "Customize your Toolbox by displaying or omitting sets of Tools.": "通过显示或删除工具来自定义您的工具箱。",
    "Access your current API key or create a new one.": "访问您当前的 API密钥或创建一个新的密钥。",
    "Enable or disable the communication feature to chat with other users.": "启用或禁用与其他用户聊天的通信功能。",
    "Allows you to change your login credentials.": "允许您更改您的登录凭证。",
    "User preferences": "用户偏好性",
    "Sign out": "退出",
    "Manage custom builds": "管理您自定义的构建集",
    "Manage OpenIDs": "管理 OpenIDs",
    "Manage Toolbox filters": "管理工具箱过滤器",
    "Manage API Key": "管理您的 API 密钥",
    "Set dataset permissions for new histories": "为新的历史设置数据集权限",
    "Change communication settings": "修改通信设置",
    "Change Password": "更改密码",
    "Manage Information": "管理您的信息",
    // ---------------------------------------------------------------------------- shed-list-view
    "Configured Galaxy Tool Sheds": "配置 Galaxy Tool Sheds",
    // ---------------------------------------------------------------------------- repository-queue-view
    "Repository Installation Queue": "存储库安装队列",
    // ---------------------------------------------------------------------------- repo-status-view
    "Repository Status": "存储卡状态",
    // ---------------------------------------------------------------------------- workflows-view
    "Workflows Missing Tools": false,
    // ---------------------------------------------------------------------------- tool-form-base
    "See in Tool Shed": false,
    Requirements: false,
    Download: "下载",
    Share: "分享",
    Search: "搜索",
    // ---------------------------------------------------------------------------- tool-form-composite
    "Workflow submission failed": false,
    "Run workflow": false,
    // ---------------------------------------------------------------------------- tool-form
    "Job submission failed": "任务提交失败",
    Execute: "执行",
    "Tool request failed": "工具请求失败",
    "Email notification": "邮件提醒",
    "Send an email notification when the job completes.": "任务完成后发送电子邮件通知。",
    // ---------------------------------------------------------------------------- workflow
    Workflows: "流程",
    // ---------------------------------------------------------------------------- workflow-view
    "Copy and insert individual steps": false,
    Warning: "警告",
    // ---------------------------------------------------------------------------- workflow-forms
    "An email notification will be sent when the job has completed.": false,
    "Add a step label.": false,
    "Assign columns": false,
    // ---------------------------------------------------------------------------- form-repeat
    "Delete this repeat block": false,
    placeholder: false,
    Repeat: false,
    // ---------------------------------------------------------------------------- ui-select-genomespace
    "Browse GenomeSpace": false,
    Browse: false,
    // ---------------------------------------------------------------------------- ui-frames
    Error: "错误",
    Close: "关闭",
    // ---------------------------------------------------------------------------- upload-view
    "Download from web or upload from disk": "从网页获取或者从本地磁盘上传数据",
    Collection: "集合数据",
    Composite: "复合数据",
    Regular: "常规数据",
    // ---------------------------------------------------------------------------- default-row
    "Upload configuration": "上传配置",
    // ---------------------------------------------------------------------------- default-view
    "FTP files": "FTP 文件",
    Reset: "重置",
    Pause: "暂停",
    Start: "开始",
    "Choose FTP file": "选择 FTP 文件",
    "Choose local file": "选择本地磁盘文件",
    // ---------------------------------------------------------------------------- collection-view
    Build: "构建集",
    "Choose FTP files": "选择 FTP 文件",
    "Choose local files": "选择本地磁盘文件",
    "Paste/Fetch data": "粘贴数据或链接",
    // ---------------------------------------------------------------------------- composite-row
    Select: "选择",
    // ---------------------------------------------------------------------------- list-of-pairs-collection-creator
    "Create a collection of paired datasets": "创建一个配对数据的集合",
    // ---------------------------------------------------------------------------- history-panel
    "View all histories": "查看所有的历史记录",
    "History options": "历史记录选项",
    "Refresh history": "刷新历史记录",
    // ---------------------------------------------------------------------------- admin-panel
    "View error logs": false,
    "View lineage": false,
    "Manage dependencies": false,
    "Manage whitelist": false,
    "Manage metadata": false,
    "Manage tools": false,
    "Monitor installation": false,
    "Install new tools": false,
    "Tool Management": false,
    Forms: false,
    Roles: false,
    Groups: false,
    Quotas: false,
    Users: false,
    "User Management": false,
    "Manage jobs": false,
    "Display applications": false,
    "Data tables": false,
    "Data types": false,
    Server: false,
    // ---------------------------------------------------------------------------- circster
    "Could Not Save": false,
    "Saving...": false,
    Settings: false,
    "Add tracks": false,
    // ---------------------------------------------------------------------------- trackster
    "New Visualization": false,
    "Add Data to Saved Visualization": false,
    "Close visualization": false,
    Circster: false,
    Bookmarks: false,
    "Add group": false,
    // ---------------------------------------------------------------------------- sweepster
    "Remove parameter from tree": false,
    "Add parameter to tree": false,
    Remove: false,
    // ---------------------------------------------------------------------------- visualization
    "Select datasets for new tracks": false,
    Libraries: "库",
    // ---------------------------------------------------------------------------- phyloviz
    "Zoom out": false,
    "Zoom in": false,
    "Phyloviz Help": false,
    "Save visualization": false,
    "PhyloViz Settings": false,
    Title: false,
    // ---------------------------------------------------------------------------- filters
    "Filtering Dataset": false,
    "Filter Dataset": false,
    // ---------------------------------------------------------------------------- tracks
    "Show individual tracks": false,
    "Trackster Error": false,
    "Tool parameter space visualization": false,
    Tool: false,
    "Set as overview": false,
    "Set display mode": false,
    Filters: false,
    "Show composite track": false,
    "Edit settings": false,
    // ---------------------------------------------------------------------------- modal_tests
    "Test title": false,
    // ---------------------------------------------------------------------------- popover_tests
    "Test Title": false,
    "Test button": false,
    // ---------------------------------------------------------------------------- ui_tests
    title: false,
    // ---------------------------------------------------------------------------- user-custom-builds
    "Create new Build": "创建新的构建集",
    "Delete custom build.": "删除自定义的构建集。",
    "Provide the data source.": "提供数据源。",
    // ---------------------------------------------------------------------------- Window Manager
    "Next in History": "下一个历史记录",
    "Previous in History": "上一个历史记录",
    // ---------------------------------------------------------------------------- generic-nav-view
    "Chat online": false,
    // ---------------------------------------------------------------------------- ui-select-content
    "Multiple collections": false,
    "Dataset collections": false,
    "Dataset collection": false,
    "Multiple datasets": false,
    "Single dataset": false,
    // ---------------------------------------------------------------------------- upload-button
    "Download from URL or upload files from disk": "从 URL 或者本地磁盘上传文件",
    // ---------------------------------------------------------------------------- workflow_editor_tests
    "tool tooltip": false,
    // ----------------------------------------------------------------------------

    ja: true,
    fr: true,
    zh: true,
});
