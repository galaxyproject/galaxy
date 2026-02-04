/** zh localization */
/* any suggestions, please contact me: ishenweiyan@foxmail.com */
export default {
    // ----------------------------------------------------------------------------- masthead
    "Analyze Data": "数据分析",
    Workflow: "工作流程",
    "Shared Data": "数据共享",
    "Data Libraries": "数据库",
    Histories: "我的历史",
    Workflows: "流程",
    Visualizations: "我的可视化",
    Pages: "我的页面",
    Visualization: "可视化",
    "New Track Browser": "创建 Track Browser",
    "Saved Visualizations": "已保存的可视化",
    Admin: "管理员",
    Help: "帮助",
    Support: "支持",
    Search: "搜索",
    "Mailing Lists": "邮件列表",
    Videos: "视频",
    Wiki: "Wiki",
    "How to Cite Galaxy": "如何引用Galaxy",
    "Interactive Tours": "使用引导",
    User: "账号管理",
    Login: "登录",
    Register: "注册",
    "Log in or Register": "登录或注册",
    "Signed in as": "您已登录为",
    Preferences: "用户偏好",
    "Custom Builds": "自定义构建集",
    Logout: "退出",
    "Saved Histories": "保存的历史",
    "Saved Datasets": "保存的数据集",
    "Saved Pages": "保存的页面",

        //Tooltip
        "Account and saved data": "账户与已保存数据",
        "Account registration or login": "注册或登录",
        "Support, contact, and community": "支持、联系与社区",
        "Administer this Galaxy": "管理您的 Galaxy",
        "Visualize datasets": "数据集可视化",
        "Access published resources": "访问已发布的资源",
        "Chain tools into workflows": "将工具链接为工作流",
        "Analysis home view": "数据分析主页",

        // ---------------------------------------------------------------------------- histories
        // ---- history/options-menu
        "History Lists": "历史记录列表",
        // Saved histories is defined above.
        // "Saved Histories":
        //     false,
        "Histories Shared with Me": "与我共享的历史",
        "Current History": "当前历史记录",
        "Create New": "新建",
        "Copy History": "复制历史",
        "Share or Publish": "共享或发布",
        "Show Structure": "展示结构",
        "Extract Workflow": "提取为工作流",
        // Delete is defined elsewhere, but is also in this menu.
        // "Delete":
        //     false,
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
        Webhooks: "网络钩子",

        // ---- history-model
        // ---- history-view
        "This history is empty": "您的历史记录为空",
        "No matching datasets found": "未找到匹配的数据集",
        "An error occurred while getting updates from the server": "服务器更新时出现错误",
        "Please contact a Galaxy administrator if the problem persists": "如果问题仍然存在，请联系 Galaxy 管理员",
        //TODO:
        //"An error was encountered while <% where %>" :
        //false,
        "search datasets": "搜索数据集",
        "You are currently viewing a deleted history!": "您正在查看已删除的历史记录！",
        "You are over your disk quota": "您已超出了系统分配的磁盘配额",
        "Tool execution is on hold until your disk usage drops below your allocated quota": "工具执行已暂停，直到您的磁盘使用量低于分配的配额",
        All: "全选",
        None: "反选",
        "For all selected": "对所有选中项",

        // ---- history-view-edit
        "Edit history tags": "编辑历史标签",
        "Edit history annotation": "编辑历史备注",
        "Click to rename history": "点击以重命名历史",
        // multi operations
        "Operations on multiple datasets": "多数据集操作",
        "Hide datasets": "隐藏数据集",
        "Unhide datasets": "取消隐藏数据集",
        "Delete datasets": "删除数据集",
        "Undelete datasets": "取消删除数据集",
        "Permanently delete datasets": "永久删除数据集",
        "This will permanently remove the data in your datasets. Are you sure?": "这将永久删除您数据集中的数据。您确定吗？",

        // ---- history-view-annotated
        Dataset: "数据集",
        Annotation: "备注",

        // ---- history-view-edit-current
        "This history is empty. Click 'Get Data' on the left tool menu to start": "此历史为空。请点击左侧工具菜单中的“获取数据”开始",
        "You must be logged in to create histories": "您必须登录后才能创建历史",
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
        "Unable to purge dataset": "无法清除数据集",

        // ---- hda-base
        // display button
        "Cannot display datasets removed from disk": "无法显示已从磁盘中移除的数据集",
        "This dataset must finish uploading before it can be viewed": "此数据集必须先完成上传, 才能查看",
        "This dataset is not yet viewable": "此数据集尚不可查看",
        "View data": "查看数据",
        // download button
        Download: "下载",
        "Download dataset": "下载数据集",
        "Additional files": "其他文件",
        // info/show_params
        "View details": "查看详情",

        // dataset states
        // state: new
        "This is a new dataset and not all of its data are available yet": "这是一个新数据集，其所有数据尚未完全可用",
        // state: noPermission
        "You do not have permission to view this dataset": "您无权查看此数据集",
        // state: discarded
        "The job creating this dataset was cancelled before completion": "创建此数据集的任务在完成之前已被取消",
        // state: queued
        "This job is waiting to run": "您的任务正在等待运行",
        // state: upload
        "This dataset is currently uploading": "您的数据集正在上传中",
        // state: setting_metadata
        "Metadata is being auto-detected": "正在自动检测元数据",
        // state: running
        "This job is currently running": "您的任务正在运行中",
        // state: paused
        'This job is paused. Use the "Resume Paused Jobs" in the history menu to resume': "此任务已暂停。请使用历史菜单中的“恢复暂停的任务”来恢复",
        // state: error
        "An error occurred with this dataset": "此数据集发生错误",
        // state: empty
        "No data": "没有数据",
        // state: failed_metadata
        "An error occurred setting the metadata for this dataset": "设置此数据集的元数据时发生错误",

        // ajax error prefix
        "There was an error getting the data for this dataset": "获取此数据集的数据时出现错误",

        // purged'd/del'd msg
        "This dataset has been deleted and removed from disk": "此数据集已被删除并从磁盘中移除",
        "This dataset has been deleted": "此数据集已被删除",
        "This dataset has been hidden": "此数据集已被隐藏",

        format: "格式",
        database: "数据库",

        // ---- hda-edit
        "Edit attributes": "编辑属性",
        "Cannot edit attributes of datasets removed from disk": "无法编辑已从磁盘中移除的数据集的属性",
        "Undelete dataset to edit attributes": "取消删除数据集以编辑属性",
        "This dataset must finish uploading before it can be edited": "该数据集必须先上传完成, 才能编辑",
        "This dataset is not yet editable": "此数据集尚不可编辑",

        Delete: "删除",
        "Dataset is already deleted": "数据集已被删除",

        "View or report this error": "查看或报告此错误",

        "Run this job again": "重新运行当前任务",

        Visualize: "可视化",
        "Visualize in": "的可视化",

        "Undelete it": "取消删除",
        "Permanently remove it from disk": "从磁盘中永久移除",
        "Unhide it": "取消隐藏",

        "You may be able to": "您可以",
        "set it manually or retry auto-detection": "手动设置或重试自动检测",

        "Edit dataset tags": "编辑数据集标签",
        "Edit dataset annotation": "编辑数据集备注",

        "Tool Help": "工具帮助",

        // ---------------------------------------------------------------------------- admin
        "Reset passwords": "重置密码",
        "Search Tool Shed": "搜索工具仓库",
        "Monitor installing repositories": "监控仓库安装",
        "Manage installed tools": "管理已安装工具",
        "Reset metadata": "重置元数据",
        "Download local tool": "下载本地工具",
        "Tool lineage": "工具血缘关系",
        "Reload a tool's configuration": "重新加载工具配置",
        "View Tool Error Logs": "查看工具错误日志",
        "Manage Allowlist": "管理允许列表",
        "Manage Tool Dependencies": "管理工具依赖",
        Users: "用户",
        Groups: "组",
        "API keys": "API 密钥",
        "Impersonate a user": "模拟用户",
        Data: "数据",
        Quotas: "配额",
        Roles: "角色",
        "Local data": "本地数据",
        "Form Definitions": "表单定义",

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
        Trackster: "Trackster",
        Visualize: "可视化",
        // ---------------------------------------------------------------------------- dataset-error
        "Any additional comments you can provide regarding what you were doing at the time of the bug.": "您可以提供关于错误发生时您正在做什么的任何额外评论。",
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
        "Edit dataset attributes": "编辑数据集属性",
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
        "Import into History": "导入到历史",
        // ---------------------------------------------------------------------------- library-foldertoolbar-view
        "Location Details": "位置详情",
        "Deleting selected items": "删除选中的项目",
        "Please select folders or files": "请选择文件夹或文件",
        "Please enter paths to import": "请输入要导入的路径",
        "Adding datasets from your history": "从您的历史中添加数据集",
        "Create New Folder": "新建文件夹",
        // ---------------------------------------------------------------------------- library-librarytoolbar-view
        "Create New Library": "新建数据库",
        // ---------------------------------------------------------------------------- tours
        Tours: "引导",
        // ---------------------------------------------------------------------------- user-preferences
        "Click here to sign out of all sessions.": "点击这里退出所有会话。",
        "Add or remove custom builds using history datasets.": "从历史的数据集中添加或者移除自定义的构建集。",
        "Associate OpenIDs with your account.": "把 OpenIDs 和您的账号进行关联。",
        "Customize your Toolbox by displaying or omitting sets of Tools.": "通过显示或删除工具来自定义您的工具箱。",
        "Access your current API key or create a new one.": "访问您当前的 API密钥或创建一个新的密钥。",
        "Allows you to change your login credentials.": "允许您更改您的登录凭证。",
        "User preferences": "用户偏好设置",
        "Sign out": "退出",
        "Manage custom builds": "管理您自定义的构建集",
        "Manage OpenIDs": "管理 OpenIDs",
        "Manage Toolbox filters": "管理工具箱过滤器",
        "Manage API Key": "管理您的 API 密钥",
        "Set dataset permissions for new histories": "为新的历史设置数据集权限",
        "Change Password": "更改密码",
        "Manage Information": "管理您的信息",
        // ---------------------------------------------------------------------------- history-list
        Histories: "我的历史",
        // ---------------------------------------------------------------------------- shed-list-view
        "Configured Tool Sheds": "已配置的工具仓库",
        // ---------------------------------------------------------------------------- repository-queue-view
        "Repository Queue": "仓库队列",
        // ---------------------------------------------------------------------------- repo-status-view
        "Repository Status": "仓库状态",
        // ---------------------------------------------------------------------------- workflows-view
        "Workflows Missing Tools": "缺少工具的工作流",
        // ---------------------------------------------------------------------------- tool-form-base
        "See in Tool Shed": "在工具仓库中查看",
        Requirements: "要求",
        Download: "下载",
        Share: "共享",
        Search: "搜索",
        // ---------------------------------------------------------------------------- tool-form-composite
        "Workflow submission failed": "工作流提交失败",
        "Run workflow": "运行工作流",
        // ---------------------------------------------------------------------------- tool-form
        "Job submission failed": "任务提交失败",
        Execute: "执行",
        "Tool request failed": "工具请求失败",
        // ---------------------------------------------------------------------------- workflow
        Workflows: "流程",
        // ---------------------------------------------------------------------------- workflow-view
        "Copy and insert individual steps": "复制并插入单个步骤",
        Warning: "警告",
        // ---------------------------------------------------------------------------- workflow-forms
        "An email notification will be sent when the job has completed.": "任务完成后将发送电子邮件通知。",
        "Add a step label.": "添加步骤标签。",
        "Assign columns": "分配列",
        // ---------------------------------------------------------------------------- form-repeat
        "Delete this repeat block": "删除此重复块",
        placeholder: "占位符",
        Repeat: "重复",
        // ---------------------------------------------------------------------------- ui-frames
        Error: "错误",
        Close: "关闭",
        // ---------------------------------------------------------------------------- upload-view
        "Download from web or upload from disk": "从网络下载或从本地磁盘上传",
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
        "Choose local file": "选择本地文件",
        // ---------------------------------------------------------------------------- collection-view
        Build: "构建集",
        "Choose FTP files": "选择 FTP 文件",
        "Choose local files": "选择本地文件",
        // ---------------------------------------------------------------------------- composite-row
        Select: "选择",
        // ---------------------------------------------------------------------------- list-of-pairs-collection-creator
        "Create a collection of paired datasets": "创建配对数据集合",
        // ---------------------------------------------------------------------------- history-panel
        "View all histories": "查看所有历史",
        "History options": "历史选项",
        "Refresh history": "刷新历史",
        // ---------------------------------------------------------------------------- admin-panel
        "View error logs": "查看错误日志",
        "View lineage": "查看血缘关系",
        "Manage dependencies": "管理依赖",
        "Manage allowlist": "管理允许列表",
        "Manage metadata": "管理元数据",
        "Manage tools": "管理工具",
        "Monitor installation": "监控安装",
        "Install new tools": "安装新工具",
        "Tool Management": "工具管理",
        Forms: "表单",
        Roles: "角色",
        Groups: "组",
        Quotas: "配额",
        Users: "用户",
        "User Management": "用户管理",
        "Manage jobs": "管理任务",
        "Display applications": "显示应用程序",
        "Data tables": "数据表",
        "Data types": "数据类型",
        Server: "服务器",
        // ---------------------------------------------------------------------------- circster
        "Could Not Save": "无法保存",
        "Saving...": "正在保存...",
        Settings: "设置",
        "Add tracks": "添加轨道",
        // ---------------------------------------------------------------------------- trackster
        "New Visualization": "新建可视化",
        "Add Data to Saved Visualization": "向已保存的可视化添加数据",
        "Close visualization": "关闭可视化",
        Circster: "Circster",
        Bookmarks: "书签",
        "Add group": "添加组",
        // ---------------------------------------------------------------------------- sweepster
        "Remove parameter from tree": "从树中移除参数",
        "Add parameter to tree": "向树中添加参数",
        Remove: "移除",
        // ---------------------------------------------------------------------------- visualization
        "Select datasets for new tracks": "为新轨道选择数据集",
        Libraries: "库",
        // ---------------------------------------------------------------------------- phyloviz
        "Zoom out": "缩小",
        "Zoom in": "放大",
        "Phyloviz Help": "Phyloviz 帮助",
        "Save visualization": "保存可视化",
        "PhyloViz Settings": "PhyloViz 设置",
        Title: "标题",
        // ---------------------------------------------------------------------------- filters
        "Filtering Dataset": "过滤数据集",
        "Filter Dataset": "过滤数据集",
        // ---------------------------------------------------------------------------- tracks
        "Show individual tracks": "显示单个轨道",
        "Trackster Error": "Trackster 错误",
        "Tool parameter space visualization": "工具参数空间可视化",
        Tool: "工具",
        "Set as overview": "设为概览",
        "Set display mode": "设置显示模式",
        Filters: "过滤器",
        "Show composite track": "显示复合轨道",
        "Edit settings": "编辑设置",
        // ---------------------------------------------------------------------------- modal_tests
        "Test title": "测试标题",
        // ---------------------------------------------------------------------------- popover_tests
        "Test Title": "测试标题",
        "Test button": "测试按钮",
        // ---------------------------------------------------------------------------- ui_tests
        title: "标题",
        // ---------------------------------------------------------------------------- user-custom-builds
        "Create new Build": "新建构建集",
        "Delete custom build.": "删除自定义构建集。",
        "Provide the data source.": "提供数据源。",
        // ---------------------------------------------------------------------------- Window Manager
        "Next in History": "历史中的下一个",
        "Previous in History": "历史中的上一个",
        // ---------------------------------------------------------------------------- generic-nav-view
        "Chat online": "在线聊天",
        // ---------------------------------------------------------------------------- ui-select-content
        "Multiple collections": "多个集合",
        "Dataset collections": "数据集集合",
        "Dataset collection": "数据集集合",
        "Multiple datasets": "多个数据集",
        "Single dataset": "单个数据集",
        // ---------------------------------------------------------------------------- upload-button
        "Download from URL or upload files from disk": "从 URL 下载或从本地磁盘上传文件",
        // ---------------------------------------------------------------------------- workflow_editor_tests
        "tool tooltip": "工具提示",
        // ----------------------------------------------------------------------------
        "Subscribe to mailing list": "订阅邮件列表",
        "Already have an account?": "已有账户？",
        "Log in here.": "在此登录。",
        "Create a Galaxy account": "创建 Galaxy 账户",
        "Or, register with email": "或者，使用邮箱注册",
        "Forgot password?": "忘记密码？",
        "Register here.": "在此注册。",
        "Click here to reset your password.": "点击此处重置您的密码。",
    ja: true,
    fr: true,
    zh: true,
    es: true,
};
