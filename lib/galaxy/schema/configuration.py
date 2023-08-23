"""Contains models for Galaxy configuration options.

These models are used to generate the OpenAPI and Configuration YAML schema for the Galaxy configuration.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import Field
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.schema.schema import Model

WatchToolOptions = Union[bool, Literal["false", "true", "auto", "polling"]]


class ComputedGalaxyConfig(Model):
    """Contains Galaxy configuration options computed at runtime.

    These values are used to generate the OpenAPI schema and are excluded from the YAML schema
    of the configuration file.
    """

    lims_doc_url: Annotated[
        Optional[str],
        Field(
            deprecated=True,  # TODO: This option seems to be unused in the codebase (?)
            title="Lims Doc Url",
            description="""The URL linked by the "LIMS Documentation" link in the "Help" menu.
**Deprecated**: This is deprecated and will be removed in a future release.
Please use the `helpsite_url` option instead.""",
        ),
    ] = "https://usegalaxy.org/u/rkchak/p/sts"

    markdown_to_pdf_available: Annotated[
        Optional[bool],
        Field(
            deprecated=True,  # TODO: This option seems to be used only in tests (?)
            title="Markdown To Pdf Available",
            description="""Determines if the markdown to pdf conversion is available.
**Deprecated**: This is deprecated and will be removed in a future release.""",
        ),
    ] = False

    has_user_tool_filters: Annotated[
        bool,
        Field(
            title="Has User Tool Filters",
            description="""Determines if the user has tool filters.""",
        ),
    ] = False

    version_major: Annotated[
        str,
        Field(
            title="Version Major",
            description="""The major version of Galaxy.""",
        ),
    ]

    version_minor: Annotated[
        str,
        Field(
            title="Version Minor",
            description="""The minor version of Galaxy.""",
        ),
    ]

    version_extra: Annotated[
        Optional[Any],
        Field(
            title="Version Extra",
            description="""The extra version of Galaxy.""",
        ),
    ]

    carbon_intensity: Annotated[
        Optional[float],
        Field(
            title="Carbon Intensity",
            description="""The carbon intensity of the electricity used by the Galaxy server.""",
        ),
    ]

    geographical_server_location_name: Annotated[
        Optional[str],
        Field(
            title="Geographical Server Location Name",
            description="""The name of the geographical location of the Galaxy server.""",
        ),
    ]

    server_startttime: Annotated[
        int,
        Field(
            title="Server Start Time",
            description="""The time when the Galaxy server was started (seconds since Epoch).""",
        ),
    ]

    server_mail_configured: Annotated[
        bool,
        Field(
            title="Server Mail Configured",
            description="""Determines if the Galaxy instance has a SMTP server configured.""",
        ),
    ] = False

    python: Annotated[
        List[int],
        Field(
            title="Python Version",
            description="""The Python version used by Galaxy as a tuple of integers [mayor, minor].""",
        ),
    ]

    file_sources_configured: Annotated[
        bool,
        Field(
            title="File Sources Configured",
            description="""Determines if the Galaxy instance has custom file sources configured.""",
        ),
    ]

    quota_source_labels: Annotated[
        List[str],
        Field(
            title="Quota Source Labels",
            description="""The labels of the disk quota sources available on this Galaxy instance.""",
        ),
    ]

    object_store_allows_id_selection: Annotated[
        bool,
        Field(
            title="Object Store Allows Id Selection",
            description="""Determines if the object store allows id selection.""",
        ),
    ]

    object_store_ids_allowing_selection: Annotated[
        List[str],
        Field(
            title="Object Store Ids Allowing Selection",
            description="""The ids of the object stores that can be selected.""",
        ),
    ]

    user_library_import_dir_available: Annotated[
        bool,
        Field(
            title="User Library Import Dir Available",
            description="""Determines if the user library import directory is available.""",
        ),
    ]

    themes: Annotated[
        Dict[str, Dict[str, str]],
        Field(
            title="Themes",
            description="""The visual style themes available on this Galaxy instance.""",
        ),
    ]


# This field is redundant (as it can be obtained from the user data), but...
# we could use it for now as a simple discriminator for Admin/NonAdmin models
IsAdminUserField = Field(
    title="Is Admin User",
    description="""Determines if the current user is an admin user.""",
)


class AdminOnlyComputedGalaxyConfig(ComputedGalaxyConfig):
    """Contains Galaxy configuration options computed at runtime exposed to admins only."""

    is_admin_user: Annotated[Literal[True], IsAdminUserField] = True

    tool_shed_urls: Annotated[
        List[str],
        Field(
            title="Tool Shed Urls",
            description="""List of Tool Shed URLs to search for tools. This is a list of
fully qualified URLs (e.g., https://toolshed.g2.bx.psu.edu/).""",
        ),
    ] = []


class UserOnlyComputedGalaxyConfig(ComputedGalaxyConfig):
    """Contains Galaxy configuration options computed at runtime that can be exposed to users."""

    is_admin_user: Annotated[Literal[False], IsAdminUserField] = False


# TODO: import StaticToolBoxView or move it to a common module
PanelViewList = List[Dict[str, Any]]
PanelViewDict = Dict[str, Any]
PanelViewField = Field(
    title="Panel Views",
    description="""Definitions of static toolbox panel views embedded directly in the config instead of reading
YAML from directory with panel_views_dir.""",
)


class ApiCompatibleConfigValues(Model):
    """Contains Galaxy configuration options that can be exposed to the API.

    These values are used to generate the OpenAPI schema and may differ from the YAML schema.
    """

    panel_views: Annotated[Optional[PanelViewDict], PanelViewField] = None


class SchemaCompatibleConfigValues(Model):
    """Contains Galaxy configuration options that are used to generate the YAML schema.

    These values are used to generate the Configuration YAML schema and may differ from the OpenAPI schema.
    """

    panel_views: Annotated[Optional[PanelViewList], PanelViewField] = None


class ExposableGalaxyConfig(Model):
    """Contains Galaxy configuration values that can be exposed to regular users.

    These values are used to generate the OpenAPI and Configuration YAML schema for the Galaxy configuration.
    When a new configuration option is added to Galaxy, it should be added to this model as well as
    to the ConfigSerializer.
    """

    brand: Annotated[
        Optional[str],
        Field(
            title="Brand",
            description="""Append "{brand}" text to the masthead.""",
        ),
    ] = None

    logo_url: Annotated[
        Optional[str],
        Field(
            title="Logo Url",
            description="""The URL linked by the "Galaxy/brand" text.""",
        ),
    ] = "/"

    logo_src: Annotated[
        Optional[str],
        Field(
            title="Logo Src",
            description="""The brand image source.""",
        ),
    ] = "/static/favicon.svg"

    logo_src_secondary: Annotated[
        Optional[str],
        Field(
            title="Logo Src Secondary",
            description="""The custom brand image source.""",
        ),
    ] = None

    terms_url: Annotated[
        Optional[str],
        Field(
            title="Terms Url",
            description="""The URL linked by the "Terms and Conditions" link in the "Help" menu, as well
as on the user registration and login forms and in the activation emails.""",
        ),
    ] = None

    wiki_url: Annotated[
        str,
        Field(
            title="Wiki Url",
            description="""The URL linked by the "Community Hub" link in the "Help" menu.""",
        ),
    ] = "https://galaxyproject.org/"

    screencasts_url: Annotated[
        str,
        Field(
            title="Screencasts Url",
            description="""The URL linked by the "Videos" link in the "Help" menu.""",
        ),
    ] = "https://www.youtube.com/c/galaxyproject"

    citation_url: Annotated[
        str,
        Field(
            title="Citation Url",
            description="""The URL linked by the "How to Cite Galaxy" link in the "Help" menu.""",
        ),
    ] = "https://galaxyproject.org/citing-galaxy"

    citations_export_message_html: Annotated[
        str,
        Field(
            title="Citations Export Message Html",
            description="""Message to display on the export citations tool page""",
        ),
    ] = 'When writing up your analysis, remember to include all references that should be cited in order to completely describe your work. Also, please remember to <a href="https://galaxyproject.org/citing-galaxy">cite Galaxy</a>.'

    support_url: Annotated[
        str,
        Field(
            title="Support Url",
            description="""The URL linked by the "Support" link in the "Help" menu.""",
        ),
    ] = "https://galaxyproject.org/support/"

    quota_url: Annotated[
        str,
        Field(
            title="Quota Url",
            description="""The URL linked for quota information in the UI.""",
        ),
    ] = "https://galaxyproject.org/support/account-quotas/"

    helpsite_url: Annotated[
        str,
        Field(
            title="Helpsite Url",
            description="""The URL linked by the "Galaxy Help" link in the "Help" menu.""",
        ),
    ] = "https://help.galaxyproject.org/"

    default_locale: Annotated[
        str,
        Field(
            title="Default Locale",
            description="""Default localization for Galaxy UI.
Allowed values are listed at the end of client/src/nls/locale.js.
With the default value (auto), the locale will be automatically adjusted to
the user's navigator language.
Users can override this settings in their user preferences if the localization
settings are enabled in user_preferences_extra_conf.yml""",
        ),
    ] = "auto"

    enable_account_interface: Annotated[
        bool,
        Field(
            title="Enable Account Interface",
            description="""Allow users to manage their account data, change passwords or delete their accounts.""",
        ),
    ] = True

    enable_tool_recommendations: Annotated[
        bool,
        Field(
            title="Enable Tool Recommendations",
            description="""Allow the display of tool recommendations in workflow editor and after tool execution.
If it is enabled and set to true, please enable 'tool_recommendation_model_path' as well""",
        ),
    ] = False

    tool_recommendation_model_path: Annotated[
        str,
        Field(
            title="Tool Recommendation Model Path",
            description="""Set remote path of the trained model (HDF5 file) for tool recommendation.""",
        ),
    ] = "https://github.com/galaxyproject/galaxy-test-data/raw/master/tool_recommendation_model_v_0.2.hdf5"

    admin_tool_recommendations_path: Annotated[
        str,
        Field(
            title="Admin Tool Recommendations Path",
            description="""Set path to the additional tool preferences from Galaxy admins.
It has two blocks. One for listing deprecated tools which will be removed from the recommendations and
another is for adding additional tools to be recommended along side those from the deep learning model.""",
        ),
    ] = "tool_recommendations_overwrite.yml"

    overwrite_model_recommendations: Annotated[
        bool,
        Field(
            title="Overwrite Model Recommendations",
            description="""Overwrite or append to the tool recommendations by the deep learning model. When set to true, all the recommendations by the deep learning model
are overwritten by the recommendations set by an admin in a config file 'tool_recommendations_overwrite.yml'. When set to false, the recommended tools
by admins and predicted by the deep learning model are shown.""",
        ),
    ] = False

    topk_recommendations: Annotated[
        int,
        Field(
            title="Topk Recommendations",
            description="""Set the number of predictions/recommendations to be made by the model""",
        ),
    ] = 20

    allow_user_impersonation: Annotated[
        bool,
        Field(
            title="Allow User Impersonation",
            description="""Allow administrators to log in as other users (useful for debugging).""",
        ),
    ] = False

    allow_user_creation: Annotated[
        bool,
        Field(
            title="Allow User Creation",
            description="""Allow unregistered users to create new accounts (otherwise, they will have to be created by an admin).""",
        ),
    ] = True

    allow_user_dataset_purge: Annotated[
        bool,
        Field(
            title="Allow User Dataset Purge",
            description="""Allow users to remove their datasets from disk immediately (otherwise,
datasets will be removed after a time period specified by an administrator in
the cleanup scripts run via cron)""",
        ),
    ] = True

    use_remote_user: Annotated[
        Optional[bool],
        Field(
            title="Use Remote User",
            description="""User authentication can be delegated to an upstream proxy server (usually
Apache). The upstream proxy should set a REMOTE_USER header in the request.
Enabling remote user disables regular logins. For more information, see:
https://docs.galaxyproject.org/en/master/admin/special_topics/apache.html""",
        ),
    ] = False

    remote_user_logout_href: Annotated[
        Optional[str],
        Field(
            title="Remote User Logout Href",
            description="""If use_remote_user is enabled, you can set this to a URL that will log your users out.""",
        ),
    ] = None

    single_user: Annotated[
        # Warning: This property behaves as a str in the YAML config file but as a bool in the API response
        Optional[Union[bool, str]],
        Field(
            title="Single User",
            description="""If an e-mail address is specified here, it will hijack remote user mechanics
(``use_remote_user``) and have the webapp inject a single fixed user. This
has the effect of turning Galaxy into a single user application with no
login or external proxy required. Such applications should not be exposed to
the world.""",
        ),
    ] = None

    enable_oidc: Annotated[
        bool,
        Field(
            title="Enable Oidc",
            description="""Enables and disables OpenID Connect (OIDC) support.""",
        ),
    ] = False

    # TODO: This is a placeholder for the OIDC configuration. It should be
    # replaced with a proper model. Is not part of the YAML config file.
    oidc: Annotated[
        Dict[str, Any],
        Field(
            title="Oidc",
            description="""OpenID Connect (OIDC) configuration.""",
        ),
    ] = {}

    prefer_custos_login: Annotated[
        bool,
        Field(
            title="Prefer Custos Login",
            description="""Controls the order of the login page to prefer Custos-based login and registration.""",
        ),
    ] = False

    enable_quotas: Annotated[
        bool,
        Field(
            title="Enable Quotas",
            description="""Enable enforcement of quotas. Quotas can be set from the Admin interface.""",
        ),
    ] = False

    post_user_logout_href: Annotated[
        str,
        Field(
            title="Post User Logout Href",
            description="""This is the default url to which users are redirected after they log out.""",
        ),
    ] = "/root/login?is_logout_redirect=true"

    datatypes_disable_auto: Annotated[
        bool,
        Field(
            title="Datatypes Disable Auto",
            description="""Disable the 'Auto-detect' option for file uploads""",
        ),
    ] = False

    ga_code: Annotated[
        Optional[str],
        Field(
            title="Google Analytics Code",
            description="""You can enter tracking code here to track visitor's behavior
through your Google Analytics account. Example: UA-XXXXXXXX-Y""",
        ),
    ] = None

    plausible_server: Annotated[
        Optional[str],
        Field(
            title="Plausible Server",
            description="""Please enter the URL for the Plausible server (including https) so this can be used for tracking
with Plausible (https://plausible.io/).""",
        ),
    ] = None

    plausible_domain: Annotated[
        Optional[str],
        Field(
            title="Plausible Domain",
            description="""Please enter the URL for the Galaxy server so this can be used for tracking
with Plausible (https://plausible.io/).""",
        ),
    ] = None

    matomo_server: Annotated[
        Optional[str],
        Field(
            title="Matomo Server",
            description="""Please enter the URL for the Matomo server (including https) so this can be used for tracking
with Matomo (https://matomo.org/).""",
        ),
    ] = None

    matomo_site_id: Annotated[
        Optional[str],
        Field(
            title="Matomo Site Id",
            description="""Please enter the site ID for the Matomo server so this can be used for tracking
with Matomo (https://matomo.org/).""",
        ),
    ] = None

    enable_unique_workflow_defaults: Annotated[
        bool,
        Field(
            title="Enable Unique Workflow Defaults",
            description="""Enable a feature when running workflows. When enabled, default datasets
are selected for "Set at Runtime" inputs from the history such that the
same input will not be selected twice, unless there are more inputs than
compatible datasets in the history.
When false, the most recently added compatible item in the history will
be used for each "Set at Runtime" input, independent of others in the workflow.""",
        ),
    ] = False

    enable_beta_markdown_export: Annotated[
        bool,
        Field(
            title="Enable Beta Markdown Export",
            description="""Enable export of Galaxy Markdown documents (pages and workflow reports)
to PDF. Requires manual installation and setup of weasyprint (latest version
available for Python 2.7 is 0.42).""",
        ),
    ] = False

    enable_beacon_integration: Annotated[
        bool,
        Field(
            title="Enable Beacon Integration",
            description="""Enables user preferences and api endpoint for the beacon integration.""",
        ),
    ] = False

    simplified_workflow_run_ui: Annotated[
        Literal["off", "prefer"],
        Field(
            title="Simplified Workflow Run Ui",
            description="""If set to 'off' by default, always use the traditional workflow form that renders
all steps in the GUI and serializes the tool state of all steps during
invocation. Set to 'prefer' to default to a simplified workflow UI that
only renders the inputs if possible (the workflow must have no disconnected
runtime inputs and not replacement parameters within tool steps). In the
future 'force' may be added an option for Galaskio-style servers that should
only render simplified workflows.""",
        ),
    ] = "prefer"

    simplified_workflow_run_ui_target_history: Annotated[
        Literal["current", "new", "prefer_current", "prefer_new"],
        Field(
            title="Simplified Workflow Run Ui Target History",
            description="""When the simplified workflow run form is rendered, should the invocation outputs
be sent to the 'current' history or a 'new' history. If the user should be presented
and option between these - set this to 'prefer_current' or 'prefer_new' to display
a runtime setting with the corresponding default. The default is to provide the
user this option and default it to the current history (the traditional behavior
of Galaxy for years) - this corresponds to the setting 'prefer_current'.
""",
        ),
    ] = "prefer_current"

    simplified_workflow_run_ui_job_cache: Annotated[
        Literal["on", "off"],
        Field(
            title="Simplified Workflow Run Ui Job Cache",
            description="""When the simplified workflow run form is rendered, should the invocation use job
caching. This isn't a boolean so an option for 'show-selection' can be added later.""",
        ),
    ] = "off"

    nginx_upload_path: Annotated[
        Optional[str],
        Field(
            title="Nginx Upload Path",
            description="""This value overrides the action set on the file upload form, e.g. the web
path where the nginx_upload_module has been configured to intercept upload requests.""",
        ),
    ]

    chunk_upload_size: Annotated[
        int,
        Field(
            title="Chunk Upload Size",
            description="""Galaxy can upload user files in chunks without using nginx. Enable the chunk
uploader by specifying a chunk size larger than 0. The chunk size is specified
in bytes (default: 10MB).
""",
        ),
    ] = 10485760

    ftp_upload_site: Annotated[
        Optional[str],
        Field(
            title="Ftp Upload Site",
            description="""Enable Galaxy's "Upload via FTP" interface.
You'll need to install and configure an FTP server (we've used ProFTPd since it can use Galaxy's
database for authentication) and set the following two options.
This will be provided to users in the help text as 'log in to the FTP server at '.
Thus, it should be the hostname of your FTP server.""",
        ),
    ] = None

    require_login: Annotated[
        bool,
        Field(
            title="Require Login",
            description="""Force everyone to log in (disable anonymous access).""",
        ),
    ] = False

    inactivity_box_content: Annotated[
        str,
        Field(
            title="Inactivity Box Content",
            description="""Shown in warning box to users that were not activated yet.
In use only if activation_grace_period is set.""",
        ),
    ] = "Your account has not been activated yet. Feel free to browse around and see what's available, but you won't be able to upload data or run jobs until you have verified your email address."

    visualizations_visible: Annotated[
        bool,
        Field(
            title="Visualizations Visible",
            description="""Show visualization tab and list in masthead.""",
        ),
    ] = True

    interactivetools_enable: Annotated[
        bool,
        Field(
            title="Interactivetools Enable",
            description="""Enable InteractiveTools.""",
        ),
    ] = False

    aws_estimate: Annotated[
        bool,
        Field(
            title="Aws Estimate",
            description="""This flag enables an AWS cost estimate for every job based on their runtime matrices.
CPU, RAM and runtime usage is mapped against AWS pricing table.
Please note, that those numbers are only estimates.""",
        ),
    ] = False

    carbon_emission_estimates: Annotated[
        bool,
        Field(
            title="Carbon Emission Estimates",
            description="""This flag enables carbon emissions estimates for every job based on its runtime metrics.
CPU and RAM usage and the total job runtime are used to determine an estimate value.
These estimates and are based off of the work of the Green Algorithms Project and
the United States Environmental Protection Agency (EPA).
Visit https://www.green-algorithms.org/ and https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator.
for more details.""",
        ),
    ] = True

    geographical_server_location_code: Annotated[
        str,
        Field(
            title="Geographical Server Location Code",
            description="""The estimated geographical location of the server hosting your galaxy instance given as an ISO 3166 code.
This is used to make carbon emissions estimates more accurate as the location effects the
carbon intensity values used in the estimate calculation. This defaults to "GLOBAL" if not set or the
`geographical_server_location_code` value is invalid or unsupported. To see a full list of supported locations,
visit https://galaxyproject.org/admin/carbon_emissions""",
        ),
    ] = "GLOBAL"

    power_usage_effectiveness: Annotated[
        float,
        Field(
            title="Power Usage Effectiveness",
            description="""The estimated power usage effectiveness of the data centre housing the server your galaxy
instance is running on. This can make carbon emissions estimates more accurate.
For more information on how to calculate a PUE value, visit
https://en.wikipedia.org/wiki/Power_usage_effectiveness
""",
        ),
    ] = 1.67

    message_box_visible: Annotated[
        bool,
        Field(
            title="Message Box Visible",
            description="""Show a message box under the masthead.""",
        ),
    ] = False

    message_box_content: Annotated[
        Optional[str],
        Field(
            title="Message Box Content",
            description="""Show a message box under the masthead.""",
        ),
    ]

    message_box_class: Annotated[
        Literal["info", "warning", "error", "done"],
        Field(
            title="Message Box Class",
            description="""Class of the message box under the masthead.
Possible values are: 'info' (the default), 'warning', 'error', 'done'.""",
        ),
    ] = "info"

    mailing_join_addr: Annotated[
        Optional[str],
        Field(
            title="Mailing Join Address",
            description="""On the user registration form, users may choose to join a mailing list. This
is the address used to subscribe to the list. Uncomment and leave empty if you
want to remove this option from the user registration form.

Example value 'galaxy-announce-join@lists.galaxyproject.org'""",
        ),
    ] = "galaxy-announce-join@bx.psu.edu"

    registration_warning_message: Annotated[
        Optional[str],
        Field(
            title="Registration Warning Message",
            description="""Registration warning message is used to discourage people from registering
multiple accounts. Applies mostly for the main Galaxy instance.
If no message specified the warning box will not be shown.""",
        ),
    ] = "Please register only one account - we provide this service free of charge and have limited computational resources. Multi-accounts are tracked and will be subjected to account termination and data deletion."

    welcome_url: Annotated[
        str,
        Field(
            title="Welcome Url",
            description="""The URL of the page to display in Galaxy's middle pane when loaded. This can
be an absolute or relative URL.""",
        ),
    ] = "/static/welcome.html"

    show_welcome_with_login: Annotated[
        bool,
        Field(
            title="Show Welcome With Login",
            description="""Show the site's welcome page (see welcome_url) alongside the login page
(even if require_login is true).""",
        ),
    ] = False

    cookie_domain: Annotated[
        Optional[str],
        Field(
            title="Cookie Domain",
            description="""Tell Galaxy that multiple domains sharing the same root are associated
to this instance and wants to share the same session cookie.
This allow a user to stay logged in when passing from one subdomain to the other.
This root domain will be written in the unique session cookie shared by all subdomains.""",
        ),
    ]

    select_type_workflow_threshold: Annotated[
        int,
        Field(
            title="Select Type Workflow Threshold",
            description="""Due to performance considerations (select2 fields are pretty 'expensive' in terms of memory usage)
Galaxy uses the regular select fields for non-dataset selectors in the workflow run form.
use 0 in order to always use select2 fields, use -1 (default) in order to always use the regular select fields,
use any other positive number as threshold (above threshold: regular select fields will be used)""",
        ),
    ] = -1

    toolbox_auto_sort: Annotated[
        bool,
        Field(
            title="Toolbox Auto Sort",
            description="""If true, the toolbox will be sorted by tool id when the toolbox is loaded.
This is useful for ensuring that tools are always displayed in the same
order in the UI. If false, the order of tools in the toolbox will be
preserved as they are loaded from the tool config files.""",
        ),
    ] = True

    default_panel_view: Annotated[
        str,
        Field(
            title="Default Panel View",
            description="""Default tool panel view for the current Galaxy configuration. This should refer to an id of
a panel view defined using the panel_views or panel_views_dir configuration options or an
EDAM panel view. The default panel view is simply called `default` and refers to the tool
panel state defined by the integrated tool panel.""",
        ),
    ] = "default"

    upload_from_form_button: Annotated[
        Literal["always-on", "always-off"],
        Field(
            title="Upload From Form Button",
            description="""If 'always-on', add another button to tool form data inputs that allow uploading
data from the tool form in fewer clicks (at the expense of making the form more complicated). This applies to workflows as well.

Avoiding making this a boolean because we may add options such as 'in-single-form-view'
or 'in-simplified-workflow-views'. https://github.com/galaxyproject/galaxy/pull/9809/files#r461889109""",
        ),
    ] = "always-off"

    release_doc_base_url: Annotated[
        str,
        Field(
            title="Release Doc Base Url",
            description="""The URL linked by the "Galaxy Version" link in the "Help" menu.""",
        ),
    ] = "https://docs.galaxyproject.org/en/release_"

    expose_user_email: Annotated[
        bool,
        Field(
            title="Expose User Email",
            description="""Expose user list. Setting this to true will expose the user list to
authenticated users. This makes sharing datasets in smaller galaxy instances
much easier as they can type a name/email and have the correct user show up.
This makes less sense on large public Galaxy instances where that data
shouldn't be exposed. For semi-public Galaxies, it may make sense to expose
just the username and not email, or vice versa.

If enable_beta_gdpr is set to true, then this option will be overridden and set to false.""",
        ),
    ] = False

    enable_tool_source_display: Annotated[
        bool,
        Field(
            title="Enable Tool Source Display",
            description="""This option allows users to view the tool wrapper source code. This is
safe to enable if you have not hardcoded any secrets in any of the tool
wrappers installed on this Galaxy server. If you have only installed tool
wrappers from public tool sheds and tools shipped with Galaxy there you
can enable this option.""",
        ),
    ] = False

    enable_celery_tasks: Annotated[
        bool,
        Field(
            title="Enable Celery Tasks",
            description="""Offload long-running tasks to a Celery task queue.
Activate this only if you have setup a Celery worker for Galaxy.
For details, see https://docs.galaxyproject.org/en/master/admin/production.html""",
        ),
    ] = False

    welcome_directory: Annotated[
        str,
        Field(
            title="Welcome Directory",
            description="""Location of New User Welcome data, a single directory containing the
images and JSON of Topics/Subtopics/Slides as export. This location
is relative to galaxy/static""",
        ),
    ] = "plugins/welcome_page/new_user/static/topics/"

    tool_training_recommendations: Annotated[
        bool,
        Field(
            title="Tool Training Recommendations",
            description="""Displays a link to training material, if any includes the current tool.
When activated the following options also need to be set:
 tool_training_recommendations_link,
 tool_training_recommendations_api_url
""",
        ),
    ] = True

    tool_training_recommendations_link: Annotated[
        str,
        Field(
            title="Tool Training Recommendations Link",
            description="""Template URL to display all tutorials containing current tool.
Valid template inputs are:
 {repository_owner}
 {name}
 {tool_id}
 {training_tool_identifier}
 {version}
""",
        ),
    ] = "https://training.galaxyproject.org/training-material/by-tool/{training_tool_identifier}.html"

    tool_training_recommendations_api_url: Annotated[
        str,
        Field(
            title="Tool Training Recommendations Api Url",
            description="""URL to API describing tutorials containing specific tools.
When CORS is used, make sure to add this host.""",
        ),
    ] = "https://training.galaxyproject.org/training-material/api/top-tools.json"

    enable_notification_system: Annotated[
        bool,
        Field(
            title="Enable Notification System",
            description="""Enables the Notification System integrated in Galaxy.

Users can receive automatic notifications when a certain resource is shared with them or when some long running operations have finished, etc.

The system allows notification scheduling and expiration, and users can opt-out of specific notification categories or channels.

Admins can schedule and broadcast notifications that will be visible to all users, including special server-wide announcements such as scheduled maintenance, high load warnings, and event announcements, to name a few examples.
""",
        ),
    ] = False


class AdminExposableGalaxyConfig(ExposableGalaxyConfig):
    """Configuration options available only to Galaxy admins.

    These values are used to generate the OpenAPI and Configuration YAML schema for the Galaxy configuration.
    """

    library_import_dir: Annotated[
        Optional[str],
        Field(
            title="Library Import Dir",
            description="""Add an option to the library upload form which allows administrators to
upload a directory of files.""",
        ),
    ] = None

    user_library_import_dir: Annotated[
        Optional[str],
        Field(
            title="User Library Import Dir",
            description="""Add an option to the library upload form which allows authorized
non-administrators to upload a directory of files. The configured directory
must contain sub-directories named the same as the non-admin user's Galaxy
login ( email ). The non-admin user is restricted to uploading files or
sub-directories of files contained in their directory.""",
        ),
    ] = None

    allow_library_path_paste: Annotated[
        bool,
        Field(
            title="Allow Library Path Paste",
            description="""Adds an option to the admin library upload tool allowing admins to paste
filesystem paths to files and directories in a box, and these paths will be added to a library.""",
        ),
    ] = False

    allow_user_deletion: Annotated[
        bool,
        Field(
            title="Allow User Deletion",
            description="""Allow administrators to delete accounts.""",
        ),
    ] = False


class FullGalaxyConfig(AdminExposableGalaxyConfig, SchemaCompatibleConfigValues):
    """Contains all options from the Galaxy Configuration File.

    This model should be used only to generate the Configuration YAML schema.
    """

    config_dir: Annotated[
        Optional[str],
        Field(
            title="Config Dir",
            description="""The directory that will be prepended to relative paths in options specifying
other Galaxy config files (e.g. datatypes_config_file). Defaults to the
directory in which galaxy.yml is located.
""",
        ),
    ] = None

    managed_config_dir: Annotated[
        Optional[str],
        Field(
            title="Managed Config Dir",
            description="""The directory that will be prepended to relative paths in options specifying
config files controlled by Galaxy (such as shed_tool_config_file, etc.). Must be
writable by the user running Galaxy. Defaults to `<config_dir>/` if running
Galaxy from source or `<data_dir>/config` otherwise.
""",
        ),
    ] = None

    data_dir: Annotated[
        Optional[str],
        Field(
            title="Data Dir",
            description="""The directory that will be prepended to relative paths in options specifying
Galaxy data/cache directories and files (such as the default SQLite database,
file_path, etc.). Defaults to `database/` if running Galaxy from source or
`<config_dir>/data` otherwise.
""",
        ),
    ] = None

    templates_dir: Annotated[
        Optional[str],
        Field(
            title="Templates Dir",
            description="""The directory containing custom templates for Galaxy, such as HTML/text email templates. Defaults to 'templates'. Default templates can be found in the Galaxy root under config/templates. These can be copied to <templates_dir> if you wish to customize them.""",
        ),
    ] = "templates"

    cache_dir: Annotated[
        Optional[str],
        Field(
            title="Cache Dir",
            description="""Top level cache directory. Any other cache directories (tool_cache_data_dir,
template_cache_path, etc.) should be subdirectories.""",
        ),
    ] = "cache"

    database_connection: Annotated[
        Optional[str],
        Field(
            title="Database Connection",
            description="""By default, Galaxy uses a SQLite database at '<data_dir>/universe.sqlite'. You
may use a SQLAlchemy connection string to specify an external database instead.

Sample default 'sqlite:///<data_dir>/universe.sqlite?isolation_level=IMMEDIATE'

You may specify additional options that will be passed to the SQLAlchemy
database engine by using the prefix "database_engine_option_". For some of these
options, default values are provided (e.g. see database_engine_option_pool_size,
etc.).

The same applies to `install_database_connection`, for which you should use the
"install_database_engine_option_" prefix.

For more options, please check SQLAlchemy's documentation at
https://docs.sqlalchemy.org/en/14/core/engines.html?highlight=create_engine#sqlalchemy.create_engine
""",
        ),
    ] = None

    database_engine_option_pool_size: Annotated[
        int,
        Field(
            title="Database Engine Option Pool Size",
            description="""If the server logs errors about not having enough database pool connections,
you will want to increase these values, or consider running more Galaxy processes.""",
        ),
    ] = 5

    database_engine_option_max_overflow: Annotated[
        int,
        Field(
            title="Database Engine Option Max Overflow",
            description="""If the server logs errors about not having enough database pool connections,
you will want to increase these values, or consider running more Galaxy processes.""",
        ),
    ] = 10

    database_engine_option_pool_recycle: Annotated[
        int,
        Field(
            title="Database Engine Option Pool Recycle",
            description="""If using MySQL and the server logs the error "MySQL server has gone away",
you will want to set this to some positive value (7200 should work).""",
        ),
    ] = -1

    database_engine_option_server_side_cursors: Annotated[
        bool,
        Field(
            title="Database Engine Option Server Side Cursors",
            description="""If large database query results are causing memory or response time issues in
the Galaxy process, leave the result on the server instead. This option is
only available for PostgreSQL and is highly recommended.
""",
        ),
    ] = False

    database_query_profiling_proxy: Annotated[
        bool,
        Field(
            title="Database Query Profiling Proxy",
            description="""Log all database transactions, can be useful for debugging and performance
profiling. Logging is done via Python's 'logging' module under the qualname
'galaxy.model.orm.logging_connection_proxy'
""",
        ),
    ] = False

    database_template: Annotated[
        Optional[str],
        Field(
            title="Database Template",
            description="""If auto-creating a postgres database on startup - it can be based on an existing
template database. This will set that. This is probably only useful for testing but
documentation is included here for completeness.
""",
        ),
    ] = None

    database_log_query_counts: Annotated[
        bool,
        Field(
            title="Database Log Query Counts",
            description="""Log number of SQL queries executed and total time spent dispatching SQL statements for
each web request. If statsd is also enabled this information will be logged there as well.
This should be considered somewhat experimental, we are unsure of the performance costs of
running this in production. This is useful information for optimizing database interaction
performance. Similar information can be obtained on a per-request basis by enabling the
sql_debug middleware and adding sql_debug=1 to a request string.
""",
        ),
    ] = False

    slow_query_log_threshold: Annotated[
        float,
        Field(
            title="Slow Query Log Threshold",
            description="""Slow query logging. Queries slower than the threshold indicated below will
be logged to debug. A value of '0' is disabled. For example, you would set
this to .005 to log all queries taking longer than 5 milliseconds.
""",
        ),
    ] = 0.0

    enable_per_request_sql_debugging: Annotated[
        bool,
        Field(
            title="Enable Per Request Sql Debugging",
            description="""Enables a per request sql debugging option. If this is set to true,
append ?sql_debug=1 to web request URLs to enable detailed logging on
the backend of SQL queries generated during that request. This is
useful for debugging slow endpoints during development.
""",
        ),
    ] = False

    install_database_connection: Annotated[
        Optional[str],
        Field(
            title="Install Database Connection",
            description="""By default, Galaxy will use the same database to track user data and
tool shed install data. There are many situations in which it is
valuable to separate these - for instance bootstrapping fresh Galaxy
instances with pretested installs. The following option can be used to
separate the tool shed install database (all other options listed above
but prefixed with ``install_`` are also available).

Defaults to the value of the 'database_connection' option.
""",
        ),
    ] = None

    database_auto_migrate: Annotated[
        bool,
        Field(
            title="Database Auto Migrate",
            description="""Setting the following option to true will cause Galaxy to automatically
migrate the database forward after updates. This is not recommended for production use.
""",
        ),
    ] = False

    database_wait: Annotated[
        bool,
        Field(
            title="Database Wait",
            description="""Wait for database to become available instead of failing immediately.""",
        ),
    ] = False

    database_wait_attempts: Annotated[
        int,
        Field(
            title="Database Wait Attempts",
            description="""Number of attempts before failing if database_wait is enabled.""",
        ),
    ] = 60

    database_wait_sleep: Annotated[
        float,
        Field(
            title="Database Wait Sleep",
            description="""Time to sleep between attempts if database_wait is enabled (in seconds).""",
        ),
    ] = 1.0

    history_audit_table_prune_interval: Annotated[
        int,
        Field(
            title="History Audit Table Prune Interval",
            description="""Time (in seconds) between attempts to remove old rows from the history_audit database table.
Set to 0 to disable pruning.
""",
        ),
    ] = 3600

    file_path: Annotated[
        Optional[str],
        Field(
            title="File Path",
            description="""Where dataset files are stored. It must be accessible at the same path on any cluster
nodes that will run Galaxy jobs, unless using Pulsar. The default value has been changed
from 'files' to 'objects' as of 20.05; however, Galaxy will first check if the 'files'
directory exists before using 'objects' as the default.
""",
        ),
    ] = "objects"

    new_file_path: Annotated[
        Optional[str],
        Field(
            title="New File Path",
            description="""Where temporary files are stored. It must be accessible at the same path on any cluster
nodes that will run Galaxy jobs, unless using Pulsar.
""",
        ),
    ] = "tmp"

    maximum_upload_file_size: Annotated[
        int,
        Field(
            title="Maximum Upload File Size",
            description="""Maximum size of uploadable files, specified in bytes (default: 100GB).
This value is ignored if an external upload server is configured.
""",
        ),
    ] = 107374182400

    tool_config_file: Annotated[
        Optional[Any],
        Field(
            title="Tool Config File",
            description="""Tool config files, defines what tools are available in Galaxy.
Tools can be locally developed or installed from Galaxy tool sheds.
(config/tool_conf.xml.sample will be used if left unset and
config/tool_conf.xml does not exist). Can be a single file, a list of
files, or (for backwards compatibility) a comma-separated list of files.
""",
        ),
    ] = "tool_conf.xml"

    shed_tool_config_file: Annotated[
        Optional[str],
        Field(
            title="Shed Tool Config File",
            description="""Tool config file for tools installed from the Galaxy Tool Shed. Must
be writable by Galaxy and generally should not be edited by hand. In
older Galaxy releases, this file was part of the tool_config_file
option. It is still possible to specify this file (and other
shed-enabled tool config files) in tool_config_file, but in the
standard case of a single shed-enabled tool config, this option is
preferable. This file will be created automatically upon tool
installation, whereas Galaxy will fail to start if any files in
tool_config_file cannot be read.
""",
        ),
    ] = "shed_tool_conf.xml"

    migrated_tools_config: Annotated[
        Optional[str],
        Field(
            title="Migrated Tools Config",
            description="""This option is deprecated.
In previous releases this file was maintained by tool migration scripts that are no
longer part of the code base. The option remains as a placeholder for deployments where
these scripts were previously run and such a file exists.
""",
        ),
    ] = "migrated_tools_conf.xml"

    integrated_tool_panel_config: Annotated[
        Optional[str],
        Field(
            title="Integrated Tool Panel Config",
            description="""File that contains the XML section and tool tags from all tool panel config
files integrated into a single file that defines the tool panel layout. This
file can be changed by the Galaxy administrator to alter the layout of the
tool panel. If not present, Galaxy will create it.

The value of this option will be resolved with respect to <managed_config_dir>.
""",
        ),
    ] = "integrated_tool_panel.xml"

    tool_path: Annotated[
        Optional[str],
        Field(
            title="Tool Path",
            description="""Default path to the directory containing the tools defined in tool_conf.xml.
Other tool config files must include the tool_path as an attribute in the
<toolbox> tag.
""",
        ),
    ] = "tools"

    tool_dependency_dir: Annotated[
        Optional[str],
        Field(
            title="Tool Dependency Dir",
            description="""Various dependency resolver configuration parameters will have defaults set relative
to this path, such as the default conda prefix, default Galaxy packages path, legacy
tool shed dependencies path, and the dependency cache directory.

Set the string to null to explicitly disable tool dependency handling.
If this option is set to none or an invalid path, installing tools with dependencies
from the Tool Shed or in Conda will fail.
""",
        ),
    ] = "dependencies"

    dependency_resolvers_config_file: Annotated[
        Optional[str],
        Field(
            title="Dependency Resolvers Config File",
            description="""Specifies the path to the standalone dependency resolvers configuration file. This
configuration can now be specified directly in the Galaxy configuration, see the
description of the 'dependency_resolvers' option for details.
""",
        ),
    ] = "dependency_resolvers_conf.xml"

    conda_prefix: Annotated[
        Optional[str],
        Field(
            title="Conda Prefix",
            description="""conda_prefix is the location on the filesystem where Conda packages and environments are
installed.

Sample default '<tool_dependency_dir>/_conda'
""",
        ),
    ] = None

    conda_exec: Annotated[
        Optional[str],
        Field(
            title="Conda Exec",
            description="""Override the Conda executable to use, it will default to the one on the
PATH (if available) and then to <conda_prefix>/bin/conda
""",
        ),
    ] = None

    conda_debug: Annotated[
        bool,
        Field(
            title="Conda Debug",
            description="""Pass debug flag to conda commands.""",
        ),
    ] = False

    conda_ensure_channels: Annotated[
        Optional[str],
        Field(
            title="Conda Ensure Channels",
            description="""conda channels to enable by default
(https://conda.io/docs/user-guide/tasks/manage-channels.html)
""",
        ),
    ] = "conda-forge,bioconda,defaults"

    conda_use_local: Annotated[
        bool,
        Field(
            title="Conda Use Local",
            description="""Use locally-built conda packages.""",
        ),
    ] = False

    conda_auto_install: Annotated[
        bool,
        Field(
            title="Conda Auto Install",
            description="""Set to true to instruct Galaxy to look for and install missing tool
dependencies before each job runs.
""",
        ),
    ] = False

    conda_auto_init: Annotated[
        bool,
        Field(
            title="Conda Auto Init",
            description="""Set to true to instruct Galaxy to install Conda from the web automatically
if it cannot find a local copy and conda_exec is not configured.
""",
        ),
    ] = True

    conda_copy_dependencies: Annotated[
        bool,
        Field(
            title="Conda Copy Dependencies",
            description="""You must set this to true if conda_prefix and job_working_directory are not on the same
volume, or some conda dependencies will fail to execute at job runtime.
Conda will copy packages content instead of creating hardlinks or symlinks.
This will prevent problems with some specific packages (perl, R), at the cost
of extra disk space usage and extra time spent copying packages.
""",
        ),
    ] = False

    local_conda_mapping_file: Annotated[
        Optional[str],
        Field(
            title="Local Conda Mapping File",
            description="""Path to a file that provides a mapping from abstract packages to concrete conda packages.
See `config/local_conda_mapping.yml.sample` for examples.
""",
        ),
    ] = "local_conda_mapping.yml"

    modules_mapping_files: Annotated[
        Optional[str],
        Field(
            title="Modules Mapping Files",
            description="""Path to a file that provides a mapping from abstract packages to locally installed modules.
See `config/environment_modules_mapping.yml.sample` for examples.
""",
        ),
    ] = "environment_modules_mapping.yml"

    use_cached_dependency_manager: Annotated[
        bool,
        Field(
            title="Use Cached Dependency Manager",
            description="""Certain dependency resolvers (namely Conda) take a considerable amount of
time to build an isolated job environment in the job_working_directory if the
job working directory is on a network share. Set this option to true
to cache the dependencies in a folder. This option is beta and should only be
used if you experience long waiting times before a job is actually submitted
to your cluster.

This only affects tools where some requirements can be resolved but not others,
most modern best practice tools can use prebuilt environments in the Conda
directory.
""",
        ),
    ] = False

    tool_dependency_cache_dir: Annotated[
        Optional[str],
        Field(
            title="Tool Dependency Cache Dir",
            description="""By default the tool_dependency_cache_dir is the _cache directory
of the tool dependency directory.

Sample default '<tool_dependency_dir>/_cache'
""",
        ),
    ] = None

    precache_dependencies: Annotated[
        bool,
        Field(
            title="Precache Dependencies",
            description="""By default, when using a cached dependency manager, the dependencies are cached
when installing new tools and when using tools for the first time.
Set this to false if you prefer dependencies to be cached only when installing new tools.
""",
        ),
    ] = True

    tool_sheds_config_file: Annotated[
        Optional[str],
        Field(
            title="Tool Sheds Config File",
            description="""File containing the Galaxy Tool Sheds that should be made available to
install from in the admin interface (.sample used if default does not exist).
""",
        ),
    ] = "tool_sheds_conf.xml"

    watch_tools: Annotated[
        WatchToolOptions,
        Field(
            title="Watch Tools",
            description="""Monitor the tools and tool directories listed in any tool config file specified in
tool_config_file option. If changes are found, tools are automatically reloaded.
Watchdog ( https://pypi.org/project/watchdog/ ) must be installed and available to Galaxy
to use this option. Other options include 'auto' which will attempt to watch tools if the
watchdog library is available but won't fail to load Galaxy if it is not and 'polling'
which will use a less efficient monitoring scheme that may work in wider range of
scenarios than the watchdog default.
""",
        ),
    ] = "false"

    watch_job_rules: Annotated[
        WatchToolOptions,
        Field(
            title="Watch Job Rules",
            description="""Monitor dynamic job rules. If changes are found, rules are automatically reloaded. Takes
the same values as the 'watch_tools' option.
""",
        ),
    ] = "false"

    watch_core_config: Annotated[
        WatchToolOptions,
        Field(
            title="Watch Core Config",
            description="""Monitor a subset of options in the core configuration file (See RELOADABLE_CONFIG_OPTIONS
in lib/galaxy/config/__init__.py). If changes are found, modified options are
automatically reloaded. Takes the same values as the 'watch_tools' option.
""",
        ),
    ] = "false"

    watch_tours: Annotated[
        WatchToolOptions,
        Field(
            title="Watch Tours",
            description="""Monitor the interactive tours directory specified in the 'tour_config_dir' option. If
changes are found, modified tours are automatically reloaded. Takes the same values as the
'watch_tools' option.
""",
        ),
    ] = "false"

    short_term_storage_dir: Annotated[
        Optional[str],
        Field(
            title="Short Term Storage Dir",
            description="""Location of files available for a short time as downloads (short term storage).
This directory is exclusively used for serving dynamically generated downloadable
content. Galaxy may uses the new_file_path parameter as a general temporary directory
and that directory should be monitored by a tool such as tmpwatch in production
environments. short_term_storage_dir on the other hand is monitored by Galaxy's task
framework and should not require such external tooling.
""",
        ),
    ] = "short_term_web_storage"

    short_term_storage_default_duration: Annotated[
        int,
        Field(
            title="Short Term Storage Default Duration",
            description="""Default duration before short term web storage files will be cleaned up by Galaxy
tasks (in seconds). The default duration is 1 day.
""",
        ),
    ] = 86400

    short_term_storage_maximum_duration: Annotated[
        int,
        Field(
            title="Short Term Storage Maximum Duration",
            description="""The maximum duration short term storage files can hosted before they will be marked for
clean up. The default setting of 0 indicates no limit here.
""",
        ),
    ] = 0

    short_term_storage_cleanup_interval: Annotated[
        int,
        Field(
            title="Short Term Storage Cleanup Interval",
            description="""How many seconds between instances of short term storage being cleaned up in default
Celery task configuration.
""",
        ),
    ] = 3600

    file_sources_config_file: Annotated[
        Optional[str],
        Field(
            title="File Sources Config File",
            description="""Configured FileSource plugins.""",
        ),
    ] = "file_sources_conf.yml"

    file_sources: Annotated[
        Optional[List[Any]],
        Field(
            title="File Sources",
            description="""FileSource plugins described embedded into Galaxy's config.""",
        ),
    ] = None

    enable_mulled_containers: Annotated[
        bool,
        Field(
            title="Enable Mulled Containers",
            description="""Enable Galaxy to fetch containers registered with quay.io generated
from tool requirements resolved through Conda. These containers (when
available) have been generated using mulled - https://github.com/mulled.
Container availability will vary by tool, this option will only be used
for job destinations with Docker or Singularity enabled.
""",
        ),
    ] = True

    container_resolvers_config_file: Annotated[
        Optional[str],
        Field(
            title="Container Resolvers Config File",
            description="""Container resolvers configuration. Set up a file describing
container resolvers to use when discovering containers for Galaxy. If
this is set to None, the default container resolvers loaded is
determined by enable_mulled_containers.
For available options see https://docs.galaxyproject.org/en/master/admin/container_resolvers.html
""",
        ),
    ] = None

    container_resolvers: Annotated[
        Optional[List[Any]],
        Field(
            title="Container Resolvers",
            description="""Rather than specifying a container_resolvers_config_file, the definition of the
resolvers to enable can be embedded into Galaxy's config with this option.
This has no effect if a container_resolvers_config_file is used.
Takes the same options that can be set in container_resolvers_config_file.
""",
        ),
    ] = None

    involucro_path: Annotated[
        Optional[str],
        Field(
            title="Involucro Path",
            description="""involucro is a tool used to build Docker or Singularity containers for tools from Conda
dependencies referenced in tools as `requirement` s. The following path is
the location of involucro on the Galaxy host. This is ignored if the relevant
container resolver isn't enabled, and will install on demand unless
involucro_auto_init is set to false.
""",
        ),
    ] = "involucro"

    involucro_auto_init: Annotated[
        bool,
        Field(
            title="Involucro Auto Init",
            description="""Install involucro as needed to build Docker or Singularity containers for tools. Ignored if
relevant container resolver is not used.
""",
        ),
    ] = True

    mulled_channels: Annotated[
        Optional[str],
        Field(
            title="Mulled Channels",
            description="""Conda channels to use when building Docker or Singularity containers using involucro.""",
        ),
    ] = "conda-forge,bioconda"

    enable_tool_shed_check: Annotated[
        bool,
        Field(
            title="Enable Tool Shed Check",
            description="""Enable automatic polling of relative tool sheds to see if any updates
are available for installed repositories. Ideally only one Galaxy
server process should be able to check for repository updates. The
setting for hours_between_check should be an integer between 1 and 24.
""",
        ),
    ] = False

    hours_between_check: Annotated[
        int,
        Field(
            title="Hours Between Check",
            description="""Enable automatic polling of relative tool sheds to see if any updates
are available for installed repositories. Ideally only one Galaxy
server process should be able to check for repository updates. The
setting for hours_between_check should be an integer between 1 and 24.
""",
        ),
    ] = 12

    tool_data_table_config_path: Annotated[
        Optional[str],
        Field(
            title="Tool Data Table Config Path",
            description="""XML config file that contains data table entries for the
ToolDataTableManager. This file is manually # maintained by the Galaxy
administrator (.sample used if default does not exist).
""",
        ),
    ] = "tool_data_table_conf.xml"

    shed_tool_data_table_config: Annotated[
        Optional[str],
        Field(
            title="Shed Tool Data Table Config",
            description="""XML config file that contains additional data table entries for the
ToolDataTableManager. This file is automatically generated based on the
current installed tool shed repositories that contain valid
tool_data_table_conf.xml.sample files. At the time of installation, these
entries are automatically added to the following file, which is parsed and
applied to the ToolDataTableManager at server start up.
""",
        ),
    ] = "shed_tool_data_table_conf.xml"

    tool_data_path: Annotated[
        Optional[str],
        Field(
            title="Tool Data Path",
            description="""Directory where data used by tools is located. See the samples in that
directory and the Galaxy Community Hub for help:
https://galaxyproject.org/admin/data-integration
""",
        ),
    ] = "tool-data"

    shed_tool_data_path: Annotated[
        Optional[str],
        Field(
            title="Shed Tool Data Path",
            description="""Directory where Tool Data Table related files will be placed when installed from a
ToolShed. Defaults to the value of the 'tool_data_path' option.
""",
        ),
    ] = None

    watch_tool_data_dir: Annotated[
        WatchToolOptions,
        Field(
            title="Watch Tool Data Dir",
            description="""Monitor the tool_data and shed_tool_data_path directories. If changes in tool data table
files are found, the tool data tables for that data manager are automatically reloaded.
Watchdog ( https://pypi.org/project/watchdog/ ) must be installed and available to Galaxy
to use this option. Other options include 'auto' which will attempt to use the watchdog
library if it is available but won't fail to load Galaxy if it is not and 'polling' which
will use a less efficient monitoring scheme that may work in wider range of scenarios than
the watchdog default.
""",
        ),
    ] = "false"

    refgenie_config_file: Annotated[
        Optional[str],
        Field(
            title="Refgenie Config File",
            description="""File containing refgenie configuration, e.g. /path/to/genome_config.yaml. Can be used by refgenie backed tool data tables.""",
        ),
    ] = None

    build_sites_config_file: Annotated[
        Optional[str],
        Field(
            title="Build Sites Config File",
            description="""File that defines the builds (dbkeys) available at sites used by display applications
and the URL to those sites.
""",
        ),
    ] = "build_sites.yml"

    builds_file_path: Annotated[
        Optional[str],
        Field(
            title="Builds File Path",
            description="""File containing old-style genome builds.

The value of this option will be resolved with respect to <tool_data_path>.
""",
        ),
    ] = "shared/ucsc/builds.txt"

    len_file_path: Annotated[
        Optional[str],
        Field(
            title="Len File Path",
            description="""Directory where chrom len files are kept, currently mainly used by trackster.

The value of this option will be resolved with respect to <tool_data_path>.
""",
        ),
    ] = "shared/ucsc/chrom"

    datatypes_config_file: Annotated[
        Optional[str],
        Field(
            title="Datatypes Config File",
            description="""Datatypes config file(s), defines what data (file) types are available in
Galaxy (.sample is used if default does not exist). If a datatype appears in
multiple files, the last definition is used (though the first sniffer is used
so limit sniffer definitions to one file).
""",
        ),
    ] = "datatypes_conf.xml"

    sniff_compressed_dynamic_datatypes_default: Annotated[
        bool,
        Field(
            title="Sniff Compressed Dynamic Datatypes Default",
            description="""Enable sniffing of compressed datatypes. This can be configured/overridden
on a per-datatype basis in the datatypes_conf.xml file.
With this option set to false the compressed datatypes will be unpacked
before sniffing.
""",
        ),
    ] = True

    visualization_plugins_directory: Annotated[
        Optional[str],
        Field(
            title="Visualization Plugins Directory",
            description="""Visualizations config directory: where to look for individual visualization
plugins. The path is relative to the Galaxy root dir. To use an absolute
path begin the path with '/'. This is a comma-separated list.
""",
        ),
    ] = "config/plugins/visualizations"

    tour_config_dir: Annotated[
        Optional[str],
        Field(
            title="Tour Config Dir",
            description="""Interactive tour directory: where to store interactive tour definition files.
Galaxy ships with several basic interface tours enabled, though a different
directory with custom tours can be specified here. The path is relative to the
Galaxy root dir. To use an absolute path begin the path with '/'. This is a
comma-separated list.
""",
        ),
    ] = "config/plugins/tours"

    webhooks_dir: Annotated[
        Optional[str],
        Field(
            title="Webhooks Dir",
            description="""Webhooks directory: where to store webhooks - plugins to extend the Galaxy UI.
By default none will be loaded. Set to config/plugins/webhooks/demo to load Galaxy's
demo webhooks. To use an absolute path begin the path with '/'. This is a
comma-separated list. Add test/functional/webhooks to this list to include the demo
webhooks used to test the webhook framework.
""",
        ),
    ] = "config/plugins/webhooks"

    job_working_directory: Annotated[
        Optional[str],
        Field(
            title="Job Working Directory",
            description="""Each job is given a unique empty directory as its current working directory.
This option defines in what parent directory those directories will be
created.

The value of this option will be resolved with respect to <data_dir>.
""",
        ),
    ] = "jobs_directory"

    template_cache_path: Annotated[
        Optional[str],
        Field(
            title="Template Cache Path",
            description="""Mako templates are compiled as needed and cached for reuse, this directory is
used for the cache
""",
        ),
    ] = "compiled_templates"

    check_job_script_integrity: Annotated[
        bool,
        Field(
            title="Check Job Script Integrity",
            description="""Set to false to disable various checks Galaxy will do to ensure it
can run job scripts before attempting to execute or submit them.
""",
        ),
    ] = True

    check_job_script_integrity_count: Annotated[
        int,
        Field(
            title="Check Job Script Integrity Count",
            description="""Number of checks to execute if check_job_script_integrity is enabled.""",
        ),
    ] = 35

    check_job_script_integrity_sleep: Annotated[
        float,
        Field(
            title="Check Job Script Integrity Sleep",
            description="""Time to sleep between checks if check_job_script_integrity is enabled (in seconds).""",
        ),
    ] = 0.25

    default_job_shell: Annotated[
        Optional[str],
        Field(
            title="Default Job Shell",
            description="""Set the default shell used by non-containerized jobs Galaxy-wide. This
defaults to bash for all jobs and can be overridden at the destination
level for heterogeneous clusters. conda job resolution requires bash or zsh
so if this is switched to /bin/sh for instance - conda resolution
should be disabled. Containerized jobs always use /bin/sh - so more maximum
portability tool authors should assume generated commands run in sh.
""",
        ),
    ] = "/bin/bash"

    enable_tool_document_cache: Annotated[
        bool,
        Field(
            title="Enable Tool Document Cache",
            description="""Whether to enable the tool document cache. This cache stores
expanded XML strings. Enabling the tool cache results in slightly faster startup
times. The tool cache is backed by a SQLite database, which cannot
be stored on certain network disks. The cache location is configurable
using the ``tool_cache_data_dir`` setting, but can be disabled completely here.
""",
        ),
    ] = False

    tool_cache_data_dir: Annotated[
        Optional[str],
        Field(
            title="Tool Cache Data Dir",
            description="""Tool related caching. Fully expanded tools and metadata will be stored at this path.
Per tool_conf cache locations can be configured in (``shed_``)tool_conf.xml files using
the tool_cache_data_dir attribute.
""",
        ),
    ] = "tool_cache"

    tool_search_index_dir: Annotated[
        Optional[str],
        Field(
            title="Tool Search Index Dir",
            description="""Directory in which the toolbox search index is stored.""",
        ),
    ] = "tool_search_index"

    biotools_content_directory: Annotated[
        Optional[str],
        Field(
            title="Biotools Content Directory",
            description="""Point Galaxy at a repository consisting of a copy of the bio.tools database (e.g.
https://github.com/bio-tools/content/) to resolve bio.tools data for tool metadata.
""",
        ),
    ] = None

    biotools_use_api: Annotated[
        bool,
        Field(
            title="Biotools Use Api",
            description="""Set this to true to attempt to resolve bio.tools metadata for tools for tool not
resovled via biotools_content_directory.
""",
        ),
    ] = False

    biotools_service_cache_type: Annotated[
        Optional[str],
        Field(
            title="Biotools Service Cache Type",
            description="""bio.tools web service request related caching. The type of beaker cache used.""",
        ),
    ] = "file"

    biotools_service_cache_data_dir: Annotated[
        Optional[str],
        Field(
            title="Biotools Service Cache Data Dir",
            description="""bio.tools web service request related caching. The data directory to point beaker cache at.""",
        ),
    ] = "biotools/data"

    biotools_service_cache_lock_dir: Annotated[
        Optional[str],
        Field(
            title="Biotools Service Cache Lock Dir",
            description="""bio.tools web service request related caching. The lock directory to point beaker cache at.""",
        ),
    ] = "biotools/locks"

    biotools_service_cache_url: Annotated[
        Optional[str],
        Field(
            title="Biotools Service Cache Url",
            description="""When biotools_service_cache_type = ext:database, this is
the url of the database used by beaker for
bio.tools web service request related caching.
The application config code will set it to the
value of database_connection if this is not set.
""",
        ),
    ] = None

    biotools_service_cache_table_name: Annotated[
        Optional[str],
        Field(
            title="Biotools Service Cache Table Name",
            description="""When biotools_service_cache_type = ext:database, this is
the database table name used by beaker for
bio.tools web service request related caching.
""",
        ),
    ] = "beaker_cache"

    biotools_service_cache_schema_name: Annotated[
        Optional[str],
        Field(
            title="Biotools Service Cache Schema Name",
            description="""When biotools_service_cache_type = ext:database, this is
the database table name used by beaker for
bio.tools web service request related caching.
""",
        ),
    ] = None

    citation_cache_type: Annotated[
        Optional[str],
        Field(
            title="Citation Cache Type",
            description="""Citation related caching. Tool citations information maybe fetched from
external sources such as https://doi.org/ by Galaxy - the following
parameters can be used to control the caching used to store this information.
""",
        ),
    ] = "file"

    citation_cache_data_dir: Annotated[
        Optional[str],
        Field(
            title="Citation Cache Data Dir",
            description="""Citation related caching. Tool citations information maybe fetched from
external sources such as https://doi.org/ by Galaxy - the following
parameters can be used to control the caching used to store this information.
""",
        ),
    ] = "citations/data"

    citation_cache_lock_dir: Annotated[
        Optional[str],
        Field(
            title="Citation Cache Lock Dir",
            description="""Citation related caching. Tool citations information maybe fetched from
external sources such as https://doi.org/ by Galaxy - the following
parameters can be used to control the caching used to store this information.
""",
        ),
    ] = "citations/locks"

    citation_cache_url: Annotated[
        Optional[str],
        Field(
            title="Citation Cache Url",
            description="""When citation_cache_type = ext:database, this is
the url of the database used by beaker for citation
caching. The application config code will set it to the
value of database_connection if this is not set.
""",
        ),
    ] = None

    citation_cache_table_name: Annotated[
        Optional[str],
        Field(
            title="Citation Cache Table Name",
            description="""When citation_cache_type = ext:database, this is
the database table name used by beaker for
citation related caching.
""",
        ),
    ] = "beaker_cache"

    citation_cache_schema_name: Annotated[
        Optional[str],
        Field(
            title="Citation Cache Schema Name",
            description="""When citation_cache_type = ext:database, this is
the database schema name of the table used by beaker for
citation related caching.
""",
        ),
    ] = None

    mulled_resolution_cache_type: Annotated[
        Optional[str],
        Field(
            title="Mulled Resolution Cache Type",
            description="""Mulled resolution caching. Mulled resolution uses external APIs of quay.io, these
requests are caching using this and the following parameters
""",
        ),
    ] = "file"

    mulled_resolution_cache_data_dir: Annotated[
        Optional[str],
        Field(
            title="Mulled Resolution Cache Data Dir",
            description="""Data directory used by beaker for caching mulled resolution requests.""",
        ),
    ] = "mulled/data"

    mulled_resolution_cache_lock_dir: Annotated[
        Optional[str],
        Field(
            title="Mulled Resolution Cache Lock Dir",
            description="""Lock directory used by beaker for caching mulled resolution requests.""",
        ),
    ] = "mulled/locks"

    mulled_resolution_cache_expire: Annotated[
        int,
        Field(
            title="Mulled Resolution Cache Expire",
            description="""Seconds until the beaker cache is considered old and a new value is created.
""",
        ),
    ] = 3600

    mulled_resolution_cache_url: Annotated[
        Optional[str],
        Field(
            title="Mulled Resolution Cache Url",
            description="""When mulled_resolution_cache_type = ext:database, this is
the url of the database used by beaker for caching mulled resolution
requests. The application config code will set it to the
value of database_connection if this is not set.
""",
        ),
    ] = None

    mulled_resolution_cache_table_name: Annotated[
        Optional[str],
        Field(
            title="Mulled Resolution Cache Table Name",
            description="""When mulled_resolution_cache_type = ext:database, this is
the database table name used by beaker for
caching mulled resolution requests.
""",
        ),
    ] = "beaker_cache"

    mulled_resolution_cache_schema_name: Annotated[
        Optional[str],
        Field(
            title="Mulled Resolution Cache Schema Name",
            description="""When mulled_resolution_cache_type = ext:database, this is
the database schema name of the table used by beaker for
caching mulled resolution requests.
""",
        ),
    ] = None

    object_store_config_file: Annotated[
        Optional[str],
        Field(
            title="Object Store Config File",
            description="""Configuration file for the object store
If this is set and exists, it overrides any other objectstore settings.
""",
        ),
    ] = "object_store_conf.xml"

    object_store_cache_monitor_driver: Annotated[
        Literal["auto", "external", "celery", "inprocess"],
        Field(
            title="Object Store Cache Monitor Driver",
            description="""Specify where cache monitoring is driven for caching object stores
such as S3, Azure, and iRODS. This option has no affect on disk object stores.
For production instances, the cache should be monitored by external tools such
as tmpwatch and this value should be set to 'external'. This will disable all
cache monitoring in Galaxy. Alternatively, 'celery' can monitor caches using
a periodic task or an 'inprocess' thread can be used - but this last option
seriously limits Galaxy's ability to scale. The default of 'auto' will use
'celery' if 'enable_celery_tasks' is set to true or 'inprocess' otherwise.
This option serves as the default for all object stores and can be overridden
on a per object store basis (but don't - just setup tmpwatch for all relevant
cache paths).
""",
        ),
    ] = "auto"

    object_store_cache_monitor_interval: Annotated[
        int,
        Field(
            title="Object Store Cache Monitor Interval",
            description="""For object store cache monitoring done by Galaxy, this is the interval between
cache checking steps. This is used by both inprocess cache monitors (which we
recommend you do not use) and by the celery task if it is configured (by setting
enable_celery_tasks to true and not setting object_store_cache_monitor_driver to
external).
""",
        ),
    ] = 600

    object_store_cache_path: Annotated[
        Optional[str],
        Field(
            title="Object Store Cache Path",
            description="""Default cache path for caching object stores if cache not configured for
that object store entry.
""",
        ),
    ] = "object_store_cache"

    object_store_cache_size: Annotated[
        int,
        Field(
            title="Object Store Cache Size",
            description="""Default cache size for caching object stores if cache not configured for
that object store entry.
""",
        ),
    ] = -1

    object_store_store_by: Annotated[
        Optional[Literal["uuid", "id"]],
        Field(
            title="Object Store Store By",
            description="""What Dataset attribute is used to reference files in an ObjectStore implementation,
this can be 'uuid' or 'id'. The default will depend on how the object store is configured,
starting with 20.05 Galaxy will try to default to 'uuid' if it can be sure this
is a new Galaxy instance - but the default will be 'id' in many cases. In particular,
if the name of the directory set in <file_path> is `objects`, the default will be set
to 'uuid', otherwise it will be 'id'.
""",
        ),
    ] = None

    smtp_server: Annotated[
        Optional[str],
        Field(
            title="Smtp Server",
            description="""Galaxy sends mail for various things: subscribing users to the mailing list
if they request it, password resets, reporting dataset errors, and sending
activation emails. To do this, it needs to send mail through an SMTP server,
which you may define here (host:port).
Galaxy will automatically try STARTTLS but will continue upon failure.
""",
        ),
    ] = None

    smtp_username: Annotated[
        Optional[str],
        Field(
            title="Smtp Username",
            description="""If your SMTP server requires a username and password, you can provide them
here (password in cleartext here, but if your server supports STARTTLS it
will be sent over the network encrypted).
""",
        ),
    ] = None

    smtp_password: Annotated[
        Optional[str],
        Field(
            title="Smtp Password",
            description="""If your SMTP server requires a username and password, you can provide them
here (password in cleartext here, but if your server supports STARTTLS it
will be sent over the network encrypted).
""",
        ),
    ] = None

    smtp_ssl: Annotated[
        bool,
        Field(
            title="Smtp Ssl",
            description="""If your SMTP server requires SSL from the beginning of the connection""",
        ),
    ] = False

    mailing_join_subject: Annotated[
        Optional[str],
        Field(
            title="Mailing Join Subject",
            description="""The subject of the email sent to the mailing list join address. See the
`mailing_join_addr` option for more information.
""",
        ),
    ] = "Join Mailing List"

    mailing_join_body: Annotated[
        Optional[str],
        Field(
            title="Mailing Join Body",
            description="""The body of the email sent to the mailing list join address. See the
`mailing_join_addr` option for more information.
""",
        ),
    ] = "Join Mailing List"

    error_email_to: Annotated[
        Optional[str],
        Field(
            title="Error Email To",
            description="""Datasets in an error state include a link to report the error. Those reports
will be sent to this address. Error reports are disabled if no address is
set. Also this email is shown as a contact to user in case of Galaxy
misconfiguration and other events user may encounter.
""",
        ),
    ] = None

    email_from: Annotated[
        Optional[str],
        Field(
            title="Email From",
            description="""Email address to use in the 'From' field when sending emails for
account activations, workflow step notifications, password resets, and
tool error reports. We recommend using a string in the following format:
Galaxy Project <galaxy-no-reply@example.com>.
If not configured, '<galaxy-no-reply@HOSTNAME>' will be used.
""",
        ),
    ] = None

    custom_activation_email_message: Annotated[
        Optional[str],
        Field(
            title="Custom Activation Email Message",
            description="""This text will be inserted at the end of the activation email's message, before
the 'Your Galaxy Team' signature.
""",
        ),
    ] = None

    instance_resource_url: Annotated[
        Optional[str],
        Field(
            title="Instance Resource Url",
            description="""URL of the support resource for the galaxy instance. Used in activation emails.""",
            example="https://galaxyproject.org/",
        ),
    ] = None

    email_domain_blocklist_file: Annotated[
        Optional[str],
        Field(
            title="Email Domain Blocklist File",
            description="""E-mail domains blocklist is used for filtering out users that are using
disposable email addresses at registration. If their address's base domain
matches any domain on the list, they are refused registration. Address subdomains
are ignored (both 'name@spam.com' and 'name@foo.spam.com' will match 'spam.com').

The value of this option will be resolved with respect to <config_dir>.
""",
            example="email_blocklist.conf",
        ),
    ] = None

    email_domain_allowlist_file: Annotated[
        Optional[str],
        Field(
            title="Email Domain Allowlist File",
            description="""E-mail domains allowlist is used to specify allowed email address domains.
If the list is non-empty and a user attempts registration using an email
address belonging to a domain that is not on the list, registration will be
denied. Unlike <email_domain_allowlist_file> which matches the address's
base domain, here email addresses are matched against the full domain (base + subdomain).
This is a more restrictive option than <email_domain_blocklist_file>, and
therefore, in case <email_domain_allowlist_file> is set and is not empty,
<email_domain_blocklist_file> will be ignored.

The value of this option will be resolved with respect to <config_dir>.
""",
            example="email_allowlist.conf",
        ),
    ] = None

    user_activation_on: Annotated[
        bool,
        Field(
            title="User Activation On",
            description="""User account activation feature global flag. If set to false, the rest of
the Account activation configuration is ignored and user activation is
disabled (i.e. accounts are active since registration).
The activation is also not working in case the SMTP server is not defined.
""",
        ),
    ] = False

    activation_grace_period: Annotated[
        int,
        Field(
            title="Activation Grace Period",
            description="""Activation grace period (in hours). Activation is not forced (login is not
disabled) until grace period has passed. Users under grace period can't run
jobs. Enter 0 to disable grace period.
""",
        ),
    ] = 3

    password_expiration_period: Annotated[
        int,
        Field(
            title="Password Expiration Period",
            description="""Password expiration period (in days). Users are required to change their
password every x days. Users will be redirected to the change password
screen when they log in after their password expires. Enter 0 to disable
password expiration.
""",
        ),
    ] = 0

    session_duration: Annotated[
        int,
        Field(
            title="Session Duration",
            description="""Galaxy Session Timeout
This provides a timeout (in minutes) after which a user will have to log back in.
A duration of 0 disables this feature.
""",
        ),
    ] = 0

    display_servers: Annotated[
        Optional[str],
        Field(
            title="Display Servers",
            description="""Galaxy can display data at various external browsers. These options specify
which browsers should be available. URLs and builds available at these
browsers are defined in the specified files.

If use_remote_user is set to true, display application servers will be denied access
to Galaxy and so displaying datasets in these sites will fail.
display_servers contains a list of hostnames which should be allowed to
bypass security to display datasets. Please be aware that there are security
implications if this is allowed. More details (including required changes to
the proxy server config) are available in the Apache proxy documentation on
the Galaxy Community Hub.

The list of servers in this sample config are for the UCSC Main, Test and
Archaea browsers, but the default if left commented is to not allow any
display sites to bypass security (you must uncomment the line below to allow
them).
""",
        ),
    ] = "hgw1.cse.ucsc.edu,hgw2.cse.ucsc.edu,hgw3.cse.ucsc.edu,hgw4.cse.ucsc.edu,hgw5.cse.ucsc.edu,hgw6.cse.ucsc.edu,hgw7.cse.ucsc.edu,hgw8.cse.ucsc.edu,lowepub.cse.ucsc.edu"

    enable_old_display_applications: Annotated[
        bool,
        Field(
            title="Enable Old Display Applications",
            description="""Set this to false to disable the old-style display applications that
are hardcoded into datatype classes.
This may be desirable due to using the new-style, XML-defined, display
applications that have been defined for many of the datatypes that have the
old-style.
There is also a potential security concern with the old-style applications,
where a malicious party could provide a link that appears to reference the
Galaxy server, but contains a redirect to a third-party server, tricking a
Galaxy user to access said site.
""",
        ),
    ] = True

    interactivetools_upstream_proxy: Annotated[
        bool,
        Field(
            title="Interactivetools Upstream Proxy",
            description="""Set this to false to redirect users of Interactive tools directly to the Interactive tools proxy. `interactivetools_upstream_proxy` should only be set to false in development.""",
        ),
    ] = True

    interactivetools_proxy_host: Annotated[
        Optional[str],
        Field(
            title="Interactivetools Proxy Host",
            description="""Hostname and port of Interactive tools proxy. It is assumed to be hosted on the same hostname and port as
Galaxy by default.
""",
        ),
    ] = None

    interactivetools_base_path: Annotated[
        Optional[str],
        Field(
            title="Interactivetools Base Path",
            description="""Base path for interactive tools running at a subpath without a subdomain. Defaults to "/".""",
        ),
    ] = "/"

    interactivetools_map: Annotated[
        Optional[str],
        Field(
            title="Interactivetools Map",
            description="""Map for interactivetool proxy.""",
        ),
    ] = "interactivetools_map.sqlite"

    interactivetools_prefix: Annotated[
        Optional[str],
        Field(
            title="Interactivetools Prefix",
            description="""Prefix to use in the formation of the subdomain or path for interactive tools""",
        ),
    ] = "interactivetool"

    interactivetools_shorten_url: Annotated[
        bool,
        Field(
            title="Interactivetools Shorten Url",
            description="""Shorten the uuid portion of the subdomain or path for interactive tools.
Especially useful for avoiding the need for wildcard certificates by keeping
subdomain under 63 chars
""",
        ),
    ] = False

    retry_interactivetool_metadata_internally: Annotated[
        bool,
        Field(
            title="Retry Interactivetool Metadata Internally",
            description="""Galaxy Interactive Tools (GxITs) can be stopped from within the Galaxy
interface, killing the GxIT job without completing its metadata setting post-job
steps. In such a case it may be desirable to set metadata on job outputs
internally (in the Galaxy job handler process). The default is is the value of
`retry_metadata_internally`, which defaults to `true`.
""",
        ),
    ] = True

    display_galaxy_brand: Annotated[
        bool,
        Field(
            title="Display Galaxy Brand",
            description="""This option has been deprecated, use the `logo_src` instead to change the
default logo including the galaxy brand title.
""",
        ),
    ] = True

    pretty_datetime_format: Annotated[
        Optional[str],
        Field(
            title="Pretty Datetime Format",
            description="""Format string used when showing date and time information.
The string may contain:
- the directives used by Python time.strftime() function (see
 https://docs.python.org/library/time.html#time.strftime),
- $locale (complete format string for the server locale),
- $iso8601 (complete format string as specified by ISO 8601 international
 standard).
""",
        ),
    ] = "$locale (UTC)"

    trs_servers_config_file: Annotated[
        Optional[str],
        Field(
            title="Trs Servers Config File",
            description="""Allow import of workflows from the TRS servers configured in
the specified YAML or JSON file. The file should be a list with
'id', 'label', and 'api_url' for each entry. Optionally,
'link_url' and 'doc' may be be specified as well for each entry.

If this is null (the default), a simple configuration containing
just Dockstore will be used.
""",
        ),
    ] = "trs_servers_conf.yml"

    user_preferences_extra_conf_path: Annotated[
        Optional[str],
        Field(
            title="User Preferences Extra Conf Path",
            description="""Location of the configuration file containing extra user preferences.""",
        ),
    ] = "user_preferences_extra_conf.yml"

    galaxy_url_prefix: Annotated[
        Optional[str],
        Field(
            title="Galaxy Url Prefix",
            description="""URL prefix for Galaxy application. If Galaxy should be served under a prefix set this to
the desired prefix value.
""",
        ),
    ] = "/"

    galaxy_infrastructure_url: Annotated[
        Optional[str],
        Field(
            title="Galaxy Infrastructure Url",
            description="""URL (with schema http/https) of the Galaxy instance as accessible
within your local network. This URL is used as a default by pulsar
file staging and Interactive Tool containers for communicating back with
Galaxy via the API.

If you plan to run Interactive Tools make sure the docker container
can reach this URL.
""",
        ),
    ] = "http://localhost:8080"

    galaxy_infrastructure_web_port: Annotated[
        int,
        Field(
            title="Galaxy Infrastructure Web Port",
            description="""If the above URL cannot be determined ahead of time in dynamic environments
but the port which should be used to access Galaxy can be - this should be
set to prevent Galaxy from having to guess. For example if Galaxy is sitting
behind a proxy with REMOTE_USER enabled - infrastructure shouldn't talk to
Python processes directly and this should be set to 80 or 443, etc... If
unset this file will be read for a server block defining a port corresponding
to the webapp.
""",
        ),
    ] = 8080

    static_enabled: Annotated[
        bool,
        Field(
            title="Static Enabled",
            description="""Serve static content, which must be enabled if you're not serving it via a
proxy server. These options should be self explanatory and so are not
documented individually. You can use these paths (or ones in the proxy
server) to point to your own styles.
""",
        ),
    ] = True

    static_cache_time: Annotated[
        int,
        Field(
            title="Static Cache Time",
            description="""Serve static content, which must be enabled if you're not serving it via a
proxy server. These options should be self explanatory and so are not
documented individually. You can use these paths (or ones in the proxy
server) to point to your own styles.
""",
        ),
    ] = 360

    static_dir: Annotated[
        Optional[str],
        Field(
            title="Static Dir",
            description="""Serve static content, which must be enabled if you're not serving it via a
proxy server. These options should be self explanatory and so are not
documented individually. You can use these paths (or ones in the proxy
server) to point to your own styles.
""",
        ),
    ] = "static/"

    static_images_dir: Annotated[
        Optional[str],
        Field(
            title="Static Images Dir",
            description="""Serve static content, which must be enabled if you're not serving it via a
proxy server. These options should be self explanatory and so are not
documented individually. You can use these paths (or ones in the proxy
server) to point to your own styles.
""",
        ),
    ] = "static/images"
    static_favicon_dir: Annotated[
        Optional[str],
        Field(
            title="Static Favicon Dir",
            description="""Serve static content, which must be enabled if you're not serving it via a
proxy server. These options should be self explanatory and so are not
documented individually. You can use these paths (or ones in the proxy
server) to point to your own styles.
""",
        ),
    ] = "static/favicon.ico"

    static_scripts_dir: Annotated[
        Optional[str],
        Field(
            title="Static Scripts Dir",
            description="""Serve static content, which must be enabled if you're not serving it via a
proxy server. These options should be self explanatory and so are not
documented individually. You can use these paths (or ones in the proxy
server) to point to your own styles.
""",
        ),
    ] = "static/scripts/"

    static_style_dir: Annotated[
        Optional[str],
        Field(
            title="Static Style Dir",
            description="""Serve static content, which must be enabled if you're not serving it via a
proxy server. These options should be self explanatory and so are not
documented individually. You can use these paths (or ones in the proxy
server) to point to your own styles.
""",
        ),
    ] = "static/style"

    static_robots_txt: Annotated[
        Optional[str],
        Field(
            title="Static Robots Txt",
            description="""Serve static content, which must be enabled if you're not serving it via a
proxy server. These options should be self explanatory and so are not
documented individually. You can use these paths (or ones in the proxy
server) to point to your own styles.
""",
        ),
    ] = "static/robots.txt"

    display_chunk_size: Annotated[
        int,
        Field(
            title="Display Chunk Size",
            description="""Incremental Display Options""",
        ),
    ] = 65536

    apache_xsendfile: Annotated[
        bool,
        Field(
            title="Apache Xsendfile",
            description="""For help on configuring the Advanced proxy features, see:
https://docs.galaxyproject.org/en/master/admin/production.html

Apache can handle file downloads (Galaxy-to-user) via mod_xsendfile. Set
this to true to inform Galaxy that mod_xsendfile is enabled upstream.
""",
        ),
    ] = False

    nginx_x_accel_redirect_base: Annotated[
        Optional[str],
        Field(
            title="Nginx X Accel Redirect Base",
            description="""The same download handling can be done by nginx using X-Accel-Redirect. This
should be set to the path defined in the nginx config as an internal redirect
with access to Galaxy's data files (see documentation linked above).
""",
        ),
    ] = None

    upstream_gzip: Annotated[
        bool,
        Field(
            title="Upstream Gzip",
            description="""If using compression in the upstream proxy server, use this option to disable
gzipping of dataset collection and library archives, since the upstream server
will do it faster on the fly. To enable compression add ``application/zip``
to the proxy's compressable mimetypes.
""",
        ),
    ] = False

    upstream_mod_zip: Annotated[
        bool,
        Field(
            title="Upstream Mod Zip",
            description="""If using the mod-zip module in nginx, use this option to assemble
zip archives in nginx. This is preferable over the upstream_gzip option
as Galaxy does not need to serve the archive.
Requires setting up internal nginx locations to all paths that can be archived.
See https://docs.galaxyproject.org/en/master/admin/nginx.html#creating-archives-with-mod-zip
for details.
""",
        ),
    ] = False

    x_frame_options: Annotated[
        Optional[str],
        Field(
            title="X Frame Options",
            description="""The following default adds a header to web request responses that
will cause modern web browsers to not allow Galaxy to be embedded in
the frames of web applications hosted at other hosts - this can help
prevent a class of attack called clickjacking
(https://www.owasp.org/index.php/Clickjacking). If you configure a
proxy in front of Galaxy - please ensure this header remains intact
to protect your users. Uncomment and leave empty to not set the
`X-Frame-Options` header.
""",
        ),
    ] = "SAMEORIGIN"

    nginx_upload_store: Annotated[
        Optional[str],
        Field(
            title="Nginx Upload Store",
            description="""nginx can also handle file uploads (user-to-Galaxy) via nginx_upload_module.
Configuration for this is complex and explained in detail in the
documentation linked above. The upload store is a temporary directory in
which files uploaded by the upload module will be placed.
""",
        ),
    ] = None

    nginx_upload_job_files_store: Annotated[
        Optional[str],
        Field(
            title="Nginx Upload Job Files Store",
            description="""Galaxy can also use nginx_upload_module to receive files staged out upon job
completion by remote job runners (i.e. Pulsar) that initiate staging
operations on the remote end. See the Galaxy nginx documentation for the
corresponding nginx configuration.
""",
        ),
    ] = None

    nginx_upload_job_files_path: Annotated[
        Optional[str],
        Field(
            title="Nginx Upload Job Files Path",
            description="""Galaxy can also use nginx_upload_module to receive files staged out upon job
completion by remote job runners (i.e. Pulsar) that initiate staging
operations on the remote end. See the Galaxy nginx documentation for the
corresponding nginx configuration.
""",
        ),
    ] = None

    tus_upload_store: Annotated[
        Optional[str],
        Field(
            title="Tus Upload Store",
            description="""The upload store is a temporary directory in which files uploaded by the
tus middleware or server will be placed.
Defaults to new_file_path if not set.
""",
        ),
    ] = None

    dynamic_proxy_manage: Annotated[
        bool,
        Field(
            title="Dynamic Proxy Manage",
            description="""Have Galaxy manage dynamic proxy component for routing requests to other
services based on Galaxy's session cookie. It will attempt to do this by
default though you do need to install node+npm and do an npm install from
`lib/galaxy/web/proxy/js`. It is generally more robust to configure this
externally, managing it in the same way Galaxy itself is managed. If true, Galaxy will only
launch the proxy if it is actually going to be used (e.g. for Jupyter).
""",
        ),
    ] = True

    dynamic_proxy: Annotated[
        Literal["node", "golang"],
        Field(
            title="Dynamic Proxy",
            description="""As of 16.04 Galaxy supports multiple proxy types. The original NodeJS
implementation, alongside a new Golang single-binary-no-dependencies
version. Valid values are (node, golang)
""",
        ),
    ] = "node"

    dynamic_proxy_session_map: Annotated[
        Optional[str],
        Field(
            title="Dynamic Proxy Session Map",
            description="""The NodeJS dynamic proxy can use an SQLite database or a JSON file for IPC,
set that here.
""",
        ),
    ] = "session_map.sqlite"

    dynamic_proxy_bind_port: Annotated[
        int,
        Field(
            title="Dynamic Proxy Bind Port",
            description="""Set the port and IP for the dynamic proxy to bind to, this must match
the external configuration if dynamic_proxy_manage is set to false.
""",
        ),
    ] = 8800

    dynamic_proxy_bind_ip: Annotated[
        Optional[str],
        Field(
            title="Dynamic Proxy Bind Ip",
            description="""Set the port and IP for the dynamic proxy to bind to, this must match
the external configuration if dynamic_proxy_manage is set to false.
""",
        ),
    ] = "0.0.0.0"

    dynamic_proxy_debug: Annotated[
        bool,
        Field(
            title="Dynamic Proxy Debug",
            description="""Enable verbose debugging of Galaxy-managed dynamic proxy.""",
        ),
    ] = False

    dynamic_proxy_external_proxy: Annotated[
        bool,
        Field(
            title="Dynamic Proxy External Proxy",
            description="""The dynamic proxy is proxied by an external proxy (e.g. apache frontend to
nodejs to wrap connections in SSL).
""",
        ),
    ] = False

    dynamic_proxy_prefix: Annotated[
        Optional[str],
        Field(
            title="Dynamic Proxy Prefix",
            description="""Additionally, when the dynamic proxy is proxied by an upstream server, you'll
want to specify a prefixed URL so both Galaxy and the proxy reside under the
same path that your cookies are under. This will result in a url like
https://FQDN/galaxy-prefix/gie_proxy for proxying
""",
        ),
    ] = "gie_proxy"

    dynamic_proxy_golang_noaccess: Annotated[
        int,
        Field(
            title="Dynamic Proxy Golang Noaccess",
            description="""This attribute governs the minimum length of time between consecutive HTTP/WS
requests through the proxy, before the proxy considers a container as being
inactive and kills it.
""",
        ),
    ] = 60

    dynamic_proxy_golang_clean_interval: Annotated[
        int,
        Field(
            title="Dynamic Proxy Golang Clean Interval",
            description="""In order to kill containers, the golang proxy has to check at some interval
for possibly dead containers. This is exposed as a configurable parameter,
but the default value is probably fine.
""",
        ),
    ] = 10

    dynamic_proxy_golang_docker_address: Annotated[
        Optional[str],
        Field(
            title="Dynamic Proxy Golang Docker Address",
            description="""The golang proxy needs to know how to talk to your docker daemon. Currently
TLS is not supported, that will come in an update.
""",
        ),
    ] = "unix:///var/run/docker.sock"

    dynamic_proxy_golang_api_key: Annotated[
        Optional[str],
        Field(
            title="Dynamic Proxy Golang Api Key",
            description="""The golang proxy uses a RESTful HTTP API for communication with Galaxy
instead of a JSON or SQLite file for IPC. If you do not specify this, it will
be set randomly for you. You should set this if you are managing the proxy
manually.
""",
        ),
    ] = None

    auto_configure_logging: Annotated[
        bool,
        Field(
            title="Auto Configure Logging",
            description="""If true, Galaxy will attempt to configure a simple root logger if a
"loggers" section does not appear in this configuration file.
""",
        ),
    ] = True

    log_destination: Annotated[
        Optional[str],
        Field(
            title="Log Destination",
            description="""Log destination, defaults to special value "stdout" that logs to standard output. If set to anything else,
then it will be interpreted as a path that will be used as the log file, and logging to stdout will be
disabled.
""",
        ),
    ] = "stdout"

    log_rotate_size: Annotated[
        Optional[str],
        Field(
            title="Log Rotate Size",
            description="""Size of log file at which size it will be rotated as per the documentation in
https://docs.python.org/library/logging.handlers.html#logging.handlers.RotatingFileHandler
If log_rotate_count is not also set, no log rotation will be performed. A value of 0 (the default) means no
rotation. Size can be a number of bytes or a human-friendly representation like "100 MB" or "1G".
""",
        ),
    ] = "0"

    log_rotate_count: Annotated[
        int,
        Field(
            title="Log Rotate Count",
            description="""Number of log file backups to keep, per the documentation in
https://docs.python.org/library/logging.handlers.html#logging.handlers.RotatingFileHandler
Any additional rotated log files will automatically be pruned. If log_rotate_size is not also set, no log
rotation will be performed. A value of 0 (the default) means no rotation.
""",
        ),
    ] = 0

    log_level: Annotated[
        Optional[Literal["NOTSET", "TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]],
        Field(
            title="Log Level",
            description="""Verbosity of console log messages. Acceptable values can be found here:
https://docs.python.org/library/logging.html#logging-levels
A custom debug level of "TRACE" is available for even more verbosity.
""",
        ),
    ] = "DEBUG"

    logging: Annotated[
        Optional[Dict[str, Any]],
        Field(
            title="Logging",
            description="""Controls where and how the server logs messages. If set, overrides all settings in the log_* configuration
options. Configuration is described in the documentation at:
https://docs.galaxyproject.org/en/master/admin/config_logging.html
""",
        ),
    ] = None

    database_engine_option_echo: Annotated[
        bool,
        Field(
            title="Database Engine Option Echo",
            description="""Print database operations to the server log (warning, quite verbose!).""",
        ),
    ] = False

    database_engine_option_echo_pool: Annotated[
        bool,
        Field(
            title="Database Engine Option Echo Pool",
            description="""Print database pool operations to the server log (warning, quite verbose!).""",
        ),
    ] = False

    log_events: Annotated[
        bool,
        Field(
            title="Log Events",
            description="""Turn on logging of application events and some user events to the database.""",
        ),
    ] = False

    log_actions: Annotated[
        bool,
        Field(
            title="Log Actions",
            description="""Turn on logging of user actions to the database. Actions currently logged
are grid views, tool searches, and use of "recently" used tools menu. The
log_events and log_actions functionality will eventually be merged.
""",
        ),
    ] = False

    fluent_log: Annotated[
        bool,
        Field(
            title="Fluent Log",
            description="""Fluentd configuration. Various events can be logged to the fluentd instance
configured below by enabling fluent_log.
""",
        ),
    ] = False

    fluent_host: Annotated[
        Optional[str],
        Field(
            title="Fluent Host",
            description="""Fluentd configuration. Various events can be logged to the fluentd instance
configured below by enabling fluent_log.
""",
        ),
    ] = "localhost"

    fluent_port: Annotated[
        int,
        Field(
            title="Fluent Port",
            description="""Fluentd configuration. Various events can be logged to the fluentd instance
configured below by enabling fluent_log.
""",
        ),
    ] = 24224

    sanitize_all_html: Annotated[
        bool,
        Field(
            title="Sanitize All Html",
            description="""Sanitize all HTML tool output. By default, all tool output served as
'text/html' will be sanitized thoroughly. This can be disabled if you have
special tools that require unaltered output. WARNING: disabling this does
make the Galaxy instance susceptible to XSS attacks initiated by your users.
""",
        ),
    ] = True

    sanitize_allowlist_file: Annotated[
        Optional[str],
        Field(
            title="Sanitize Allowlist File",
            description="""Datasets created by tools listed in this file are trusted and will not have
their HTML sanitized on display. This can be manually edited or manipulated
through the Admin control panel -- see "Manage Allowlist"

The value of this option will be resolved with respect to <managed_config_dir>.
""",
        ),
    ] = "sanitize_allowlist.txt"

    serve_xss_vulnerable_mimetypes: Annotated[
        bool,
        Field(
            title="Serve Xss Vulnerable Mimetypes",
            description="""By default Galaxy will serve non-HTML tool output that may potentially
contain browser executable JavaScript content as plain text. This will for
instance cause SVG datasets to not render properly and so may be disabled
by setting this option to true.
""",
        ),
    ] = False

    allowed_origin_hostnames: Annotated[
        Optional[str],
        Field(
            title="Allowed Origin Hostnames",
            description="""Return a Access-Control-Allow-Origin response header that matches the Origin
header of the request if that Origin hostname matches one of the strings or
regular expressions listed here. This is a comma-separated list of hostname
strings or regular expressions beginning and ending with /.
E.g. mysite.com,google.com,usegalaxy.org,/^[\\w\\.]*example\\.com/
See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
""",
        ),
    ] = None

    trust_jupyter_notebook_conversion: Annotated[
        bool,
        Field(
            title="Trust Jupyter Notebook Conversion",
            description="""Set to true to use Jupyter nbconvert to build HTML from Jupyter
notebooks in Galaxy histories. This process may allow users to execute
arbitrary code or serve arbitrary HTML. If enabled, Jupyter must be
available and on Galaxy's PATH, to do this run
`pip install jinja2 pygments jupyter` in Galaxy's virtualenv.
""",
        ),
    ] = False

    debug: Annotated[
        bool,
        Field(
            title="Debug",
            description="""Debug enables access to various config options useful for development
and debugging: use_lint, use_profile, and use_printdebug. It also
causes the files used by PBS/SGE (submission script, output, and error)
to remain on disk after the job is complete.
""",
        ),
    ] = False

    use_lint: Annotated[
        bool,
        Field(
            title="Use Lint",
            description="""Check for WSGI compliance.""",
        ),
    ] = False

    use_profile: Annotated[
        bool,
        Field(
            title="Use Profile",
            description="""Run the Python profiler on each request.""",
        ),
    ] = False

    use_printdebug: Annotated[
        bool,
        Field(
            title="Use Printdebug",
            description="""Intercept print statements and show them on the returned page.""",
        ),
    ] = True

    monitor_thread_join_timeout: Annotated[
        int,
        Field(
            title="Monitor Thread Join Timeout",
            description="""When stopping Galaxy cleanly, how much time to give various monitoring/polling
threads to finish before giving up on joining them. Set to 0 to disable this and
terminate without waiting. Among others, these threads include the job handler
workers, which are responsible for preparing/submitting and collecting/finishing
jobs, and which can cause job errors if not shut down cleanly. If using
supervisord, consider also increasing the value of `stopwaitsecs`. See the
Galaxy Admin Documentation for more.
""",
        ),
    ] = 30

    use_heartbeat: Annotated[
        bool,
        Field(
            title="Use Heartbeat",
            description="""Write thread status periodically to 'heartbeat.log', (careful, uses disk
space rapidly!). Useful to determine why your processes may be consuming a
lot of CPU.
""",
        ),
    ] = False

    heartbeat_interval: Annotated[
        int,
        Field(
            title="Heartbeat Interval",
            description="""Control the period (in seconds) between dumps. Use -1 to disable. Regardless
of this setting, if use_heartbeat is enabled, you can send a Galaxy process
SIGUSR1 (`kill -USR1`) to force a dump.
""",
        ),
    ] = 20

    heartbeat_log: Annotated[
        Optional[str],
        Field(
            title="Heartbeat Log",
            description="""Heartbeat log filename. Can accept the template variables {server_name} and {pid}""",
        ),
    ] = "heartbeat_{server_name}.log"

    sentry_dsn: Annotated[
        Optional[str],
        Field(
            title="Sentry Dsn",
            description="""Log to Sentry
Sentry is an open source logging and error aggregation platform. Setting
sentry_dsn will enable the Sentry middleware and errors will be sent to the
indicated sentry instance. This connection string is available in your
sentry instance under <project_name> -> Settings -> API Keys.
""",
        ),
    ] = None

    sentry_event_level: Annotated[
        Optional[str],
        Field(
            title="Sentry Event Level",
            description="""Determines the minimum log level that will be sent as an event to Sentry.
Possible values are DEBUG, INFO, WARNING, ERROR or CRITICAL.
""",
        ),
    ] = "ERROR"

    sentry_traces_sample_rate: Annotated[
        float,
        Field(
            title="Sentry Traces Sample Rate",
            description="""Set to a number between 0 and 1. With this option set, every transaction created
will have that percentage chance of being sent to Sentry. A value higher than 0
is required to analyze performance.
""",
        ),
    ] = 0.0

    sentry_ca_certs: Annotated[
        Optional[str],
        Field(
            title="Sentry Ca Certs",
            description="""Use this option to provide the path to location of the CA (Certificate Authority)
certificate file if the sentry server uses a self-signed certificate.
""",
        ),
    ] = None

    statsd_host: Annotated[
        Optional[str],
        Field(
            title="Statsd Host",
            description="""Log to statsd
Statsd is an external statistics aggregator (https://github.com/etsy/statsd)
Enabling the following options will cause galaxy to log request timing and
other statistics to the configured statsd instance. The statsd_prefix is
useful if you are running multiple Galaxy instances and want to segment
statistics between them within the same aggregator.
""",
        ),
    ] = None

    statsd_port: Annotated[
        int,
        Field(
            title="Statsd Port",
            description="""Log to statsd
Statsd is an external statistics aggregator (https://github.com/etsy/statsd)
Enabling the following options will cause galaxy to log request timing and
other statistics to the configured statsd instance. The statsd_prefix is
useful if you are running multiple Galaxy instances and want to segment
statistics between them within the same aggregator.
""",
        ),
    ] = 8125

    statsd_prefix: Annotated[
        Optional[str],
        Field(
            title="Statsd Prefix",
            description="""Log to statsd
Statsd is an external statistics aggregator (https://github.com/etsy/statsd)
Enabling the following options will cause galaxy to log request timing and
other statistics to the configured statsd instance. The statsd_prefix is
useful if you are running multiple Galaxy instances and want to segment
statistics between them within the same aggregator.
""",
        ),
    ] = "galaxy"

    statsd_influxdb: Annotated[
        bool,
        Field(
            title="Statsd Influxdb",
            description="""If you are using telegraf to collect these metrics and then sending
them to InfluxDB, Galaxy can provide more nicely tagged metrics.
Instead of sending prefix + dot-separated-path, Galaxy will send
prefix with a tag path set to the page url
""",
        ),
    ] = False

    statsd_mock_calls: Annotated[
        bool,
        Field(
            title="Statsd Mock Calls",
            description="""Mock out statsd client calls - only used by testing infrastructure really.
Do not set this in production environments.
""",
        ),
    ] = False

    user_library_import_dir_auto_creation: Annotated[
        bool,
        Field(
            title="User Library Import Dir Auto Creation",
            description="""If user_library_import_dir is set, this option will auto create a library
import directory for every user (based on their email) upon login.
""",
        ),
    ] = False

    user_library_import_symlink_allowlist: Annotated[
        Optional[str],
        Field(
            title="User Library Import Symlink Allowlist",
            description="""For security reasons, users may not import any files that actually lie
outside of their `user_library_import_dir` (e.g. using symbolic links). A
list of directories can be allowed by setting the following option (the list
is comma-separated). Be aware that *any* user with library import permissions
can import from anywhere in these directories (assuming they are able to
create symlinks to them).
""",
        ),
    ] = None

    user_library_import_check_permissions: Annotated[
        bool,
        Field(
            title="User Library Import Check Permissions",
            description="""In conjunction or alternatively, Galaxy can restrict user library imports to
those files that the user can read (by checking basic unix permissions).
For this to work, the username has to match the username on the filesystem.
""",
        ),
    ] = False

    allow_path_paste: Annotated[
        bool,
        Field(
            title="Allow Path Paste",
            description="""Allow admins to paste filesystem paths during upload. For libraries this
adds an option to the admin library upload tool allowing admins to paste
filesystem paths to files and directories in a box, and these paths will be
added to a library. For history uploads, this allows pasting in paths as URIs.
(i.e. prefixed with file://). Set to true to enable. Please note the security
implication that this will give Galaxy Admins access to anything your Galaxy
user has access to.
""",
        ),
    ] = False

    disable_library_comptypes: Annotated[
        Optional[str],
        Field(
            title="Disable Library Comptypes",
            description="""Users may choose to download multiple files from a library in an archive. By
default, Galaxy allows users to select from a few different archive formats
if testing shows that Galaxy is able to create files using these formats.
Specific formats can be disabled with this option, separate more than one
format with commas. Available formats are currently 'zip', 'gz', and 'bz2'.
""",
        ),
    ] = None

    tool_name_boost: Annotated[
        float,
        Field(
            title="Tool Name Boost",
            description="""In tool search, a query match against a tool's name text will receive
this score multiplier.
""",
        ),
    ] = 20.0

    tool_name_exact_multiplier: Annotated[
        float,
        Field(
            title="Tool Name Exact Multiplier",
            description="""If a search query matches a tool name exactly, the score will be
multiplied by this factor.
""",
        ),
    ] = 10.0

    tool_id_boost: Annotated[
        float,
        Field(
            title="Tool Id Boost",
            description="""In tool search, a query match against a tool's ID text will receive
this score multiplier. The query must be an exact match against ID
in order to be counted as a match.
""",
        ),
    ] = 20.0

    tool_section_boost: Annotated[
        float,
        Field(
            title="Tool Section Boost",
            description="""In tool search, a query match against a tool's section text will
receive this score multiplier.
""",
        ),
    ] = 3.0

    tool_description_boost: Annotated[
        float,
        Field(
            title="Tool Description Boost",
            description="""In tool search, a query match against a tool's description text will
receive this score multiplier.
""",
        ),
    ] = 8.0

    tool_label_boost: Annotated[
        float,
        Field(
            title="Tool Label Boost",
            description="""In tool search, a query match against a tool's label text will
receive this score multiplier.
""",
        ),
    ] = 1.0

    tool_stub_boost: Annotated[
        float,
        Field(
            title="Tool Stub Boost",
            description="""A stub is parsed from the GUID as "owner/repo/tool_id".
In tool search, a query match against a tool's stub text will receive
this score multiplier.
""",
        ),
    ] = 2.0

    tool_help_boost: Annotated[
        float,
        Field(
            title="Tool Help Boost",
            description="""In tool search, a query match against a tool's help text will receive
this score multiplier.
""",
        ),
    ] = 1.0

    tool_help_bm25f_k1: Annotated[
        float,
        Field(
            title="Tool Help Bm25F K1",
            description="""The lower this parameter, the greater the diminishing reward for
term frequency in the help text. A higher K1 increases the level
of reward for additional occurences of a term. The default value will
provide a slight increase in score for the first, second and third
occurrence and little reward thereafter.
""",
        ),
    ] = 0.5

    tool_search_limit: Annotated[
        int,
        Field(
            title="Tool Search Limit",
            description="""Limits the number of results in toolbox search. Use to set the
maximum number of tool search results to display.
""",
        ),
    ] = 20

    tool_enable_ngram_search: Annotated[
        bool,
        Field(
            title="Tool Enable Ngram Search",
            description="""Disabling this will prevent partial matches on tool names.
Enable/disable Ngram-search for tools. It makes tool
search results tolerant for spelling mistakes in the query, and will
also match query substrings e.g. "genome" will match "genomics" or
"metagenome".
""",
        ),
    ] = True

    tool_ngram_minsize: Annotated[
        int,
        Field(
            title="Tool Ngram Minsize",
            description="""Set minimum character length of ngrams""",
        ),
    ] = 3

    tool_ngram_maxsize: Annotated[
        int,
        Field(
            title="Tool Ngram Maxsize",
            description="""Set maximum character length of ngrams""",
        ),
    ] = 4

    tool_ngram_factor: Annotated[
        float,
        Field(
            title="Tool Ngram Factor",
            description="""Ngram matched scores will be multiplied by this factor. Should always
be below 1, because an ngram match is a partial match of a search term.
""",
        ),
    ] = 0.2

    tool_test_data_directories: Annotated[
        Optional[str],
        Field(
            title="Tool Test Data Directories",
            description="""Set tool test data directory. The test framework sets this value to
'test-data,https://github.com/galaxyproject/galaxy-test-data.git' which will
cause Galaxy to clone down extra test data on the fly for certain tools
distributed with Galaxy but this is likely not appropriate for production systems.
Instead one can simply clone that repository directly and specify a path here
instead of a Git HTTP repository.
""",
        ),
    ] = "test-data"

    id_secret: Annotated[
        Optional[str],
        Field(
            title="Id Secret",
            description="""Galaxy encodes various internal values when these values will be output in
some format (for example, in a URL or cookie). You should set a key to be
used by the algorithm that encodes and decodes these values. It can be any
string with a length between 5 and 56 bytes.
One simple way to generate a value for this is with the shell command:
 python -c 'from __future__ import print_function; import time; print(time.time())' | md5sum | cut -f 1 -d ' '
""",
        ),
    ] = "USING THE DEFAULT IS NOT SECURE!"

    remote_user_maildomain: Annotated[
        Optional[str],
        Field(
            title="Remote User Maildomain",
            description="""If use_remote_user is enabled and your external authentication
method just returns bare usernames, set a default mail domain to be appended
to usernames, to become your Galaxy usernames (email addresses).
""",
        ),
    ] = None

    remote_user_header: Annotated[
        Optional[str],
        Field(
            title="Remote User Header",
            description="""If use_remote_user is enabled, the header that the upstream proxy provides
the remote username in defaults to HTTP_REMOTE_USER (the ``HTTP_`` is prepended
by WSGI). This option allows you to change the header. Note, you still need
to prepend ``HTTP_`` to the header in this option, but your proxy server should
*not* include ``HTTP_`` at the beginning of the header name.
""",
        ),
    ] = "HTTP_REMOTE_USER"

    remote_user_secret: Annotated[
        Optional[str],
        Field(
            title="Remote User Secret",
            description="""If use_remote_user is enabled, anyone who can log in to the Galaxy host may
impersonate any other user by simply sending the appropriate header. Thus a
secret shared between the upstream proxy server, and Galaxy is required.
If anyone other than the Galaxy user is using the server, then apache/nginx
should pass a value in the header 'GX_SECRET' that is identical to the one
below.
""",
        ),
    ] = "USING THE DEFAULT IS NOT SECURE!"

    normalize_remote_user_email: Annotated[
        bool,
        Field(
            title="Normalize Remote User Email",
            description="""If your proxy and/or authentication source does not normalize e-mail
addresses or user names being passed to Galaxy - set this option
to true to force these to lower case.
""",
        ),
    ] = False

    admin_users: Annotated[
        Optional[str],
        Field(
            title="Admin Users",
            description="""Administrative users - set this to a comma-separated list of valid Galaxy
users (email addresses). These users will have access to the Admin section
of the server, and will have access to create users, groups, roles,
libraries, and more. For more information, see:
 https://galaxyproject.org/admin/
""",
        ),
    ] = None

    show_user_prepopulate_form: Annotated[
        bool,
        Field(
            title="Show User Prepopulate Form",
            description="""When using LDAP for authentication, allow administrators to pre-populate users
using an additional form on 'Create new user'
""",
        ),
    ] = False

    new_user_dataset_access_role_default_private: Annotated[
        bool,
        Field(
            title="New User Dataset Access Role Default Private",
            description="""By default, users' data will be public, but setting this to true will cause
it to be private. Does not affect existing users and data, only ones created
after this option is set. Users may still change their default back to
public.
""",
        ),
    ] = False

    expose_user_name: Annotated[
        bool,
        Field(
            title="Expose User Name",
            description="""Expose user list. Setting this to true will expose the user list to
authenticated users. This makes sharing datasets in smaller galaxy instances
much easier as they can type a name/email and have the correct user show up.
This makes less sense on large public Galaxy instances where that data
shouldn't be exposed. For semi-public Galaxies, it may make sense to expose
just the username and not email, or vice versa.

If enable_beta_gdpr is set to true, then this option will be
overridden and set to false.
""",
        ),
    ] = False

    fetch_url_allowlist: Annotated[
        Optional[str],
        Field(
            title="Fetch Url Allowlist",
            description="""List of allowed local network addresses for "Upload from URL" dialog.
By default, Galaxy will deny access to the local network address space, to
prevent users making requests to services which the administrator did not
intend to expose. Previously, you could request any network service that
Galaxy might have had access to, even if the user could not normally access it.
It should be a comma-separated list of IP addresses or IP address/mask, e.g.
10.10.10.10,10.0.1.0/24,fd00::/8
""",
        ),
    ] = None

    enable_beta_gdpr: Annotated[
        bool,
        Field(
            title="Enable Beta Gdpr",
            description="""Enables GDPR Compliance mode. This makes several changes to the way
Galaxy logs and exposes data externally such as removing emails and
usernames from logs and bug reports. It also causes the delete user
admin action to permanently redact their username and password, but
not to delete data associated with the account as this is not
currently easily implementable.

You are responsible for removing personal data from backups.

This forces expose_user_email and expose_user_name to be false, and
forces user_deletion to be true to support the right to erasure.

Please read the GDPR section under the special topics area of the
admin documentation.
""",
        ),
    ] = False

    enable_beta_workflow_modules: Annotated[
        bool,
        Field(
            title="Enable Beta Workflow Modules",
            description="""Enable beta workflow modules that should not yet be considered part of Galaxy's
stable API. (The module state definitions may change and workflows built using
these modules may not function in the future.)
""",
        ),
    ] = False

    edam_panel_views: Annotated[
        Optional[str],
        Field(
            title="Edam Panel Views",
            description="""Comma-separated list of the EDAM panel views to load - choose from merged, operations, topics.
Set to empty string to disable EDAM all together. Set default_panel_view to 'ontology:edam_topics'
to override default tool panel to use an EDAM view.
""",
        ),
    ] = "operations,topics"

    edam_toolbox_ontology_path: Annotated[
        Optional[str],
        Field(
            title="Edam Toolbox Ontology Path",
            description="""Sets the path to EDAM ontology file - if the path doesn't exist PyPI package data will be loaded.""",
        ),
    ] = "EDAM.tsv"

    panel_views_dir: Annotated[
        Optional[str],
        Field(
            title="Panel Views Dir",
            description="""Directory to check out for toolbox tool panel views. The path is relative to the
Galaxy root dir. To use an absolute path begin the path with '/'. This is a
comma-separated list.
""",
        ),
    ] = "config/plugins/activities"

    default_workflow_export_format: Annotated[
        Optional[str],
        Field(
            title="Default Workflow Export Format",
            description="""Default format for the export of workflows. Possible values are 'ga'
or 'format2'.
""",
        ),
    ] = "ga"

    parallelize_workflow_scheduling_within_histories: Annotated[
        bool,
        Field(
            title="Parallelize Workflow Scheduling Within Histories",
            description="""If multiple job handlers are enabled, allow Galaxy to schedule workflow invocations
in multiple handlers simultaneously. This is discouraged because it results in a
less predictable order of workflow datasets within in histories.
""",
        ),
    ] = False

    maximum_workflow_invocation_duration: Annotated[
        int,
        Field(
            title="Maximum Workflow Invocation Duration",
            description="""This is the maximum amount of time a workflow invocation may stay in an active
scheduling state in seconds. Set to -1 to disable this maximum and allow any workflow
invocation to schedule indefinitely. The default corresponds to 1 month.
""",
        ),
    ] = 2678400

    maximum_workflow_jobs_per_scheduling_iteration: Annotated[
        int,
        Field(
            title="Maximum Workflow Jobs Per Scheduling Iteration",
            description="""Specify a maximum number of jobs that any given workflow scheduling iteration can create.
Set this to a positive integer to prevent large collection jobs in a workflow from
preventing other jobs from executing. This may also mitigate memory issues associated with
scheduling workflows at the expense of increased total DB traffic because model objects
are expunged from the SQL alchemy session between workflow invocation scheduling iterations.
Set to -1 to disable any such maximum.
""",
        ),
    ] = 1000

    flush_per_n_datasets: Annotated[
        int,
        Field(
            title="Flush Per N Datasets",
            description="""Maximum number of datasets to create before flushing created datasets to database.
This affects tools that create many output datasets.
Higher values will lead to fewer database flushes and faster execution, but require
more memory. Set to -1 to disable creating datasets in batches.
""",
        ),
    ] = 1000

    max_discovered_files: Annotated[
        int,
        Field(
            title="Max Discovered Files",
            description="""Set this to a positive integer value to limit the number of datasets that can be discovered by
a single job. This prevents accidentally creating large numbers of datasets when running tools
that create a potentially unlimited number of output datasets, such as tools that split a file
into a collection of datasets for each line in an input dataset.
""",
        ),
    ] = 10000

    history_local_serial_workflow_scheduling: Annotated[
        bool,
        Field(
            title="History Local Serial Workflow Scheduling",
            description="""Force serial scheduling of workflows within the context of a particular history""",
        ),
    ] = False

    oidc_config_file: Annotated[
        Optional[str],
        Field(
            title="Oidc Config File",
            description="""Sets the path to OIDC configuration file.""",
        ),
    ] = "oidc_config.xml"

    oidc_backends_config_file: Annotated[
        Optional[str],
        Field(
            title="Oidc Backends Config File",
            description="""Sets the path to OIDC backends configuration file.""",
        ),
    ] = "oidc_backends_config.xml"

    auth_config_file: Annotated[
        Optional[str],
        Field(
            title="Auth Config File",
            description="""XML config file that allows the use of different authentication providers
(e.g. LDAP) instead or in addition to local authentication (.sample is used
if default does not exist).
""",
        ),
    ] = "auth_conf.xml"

    api_allow_run_as: Annotated[
        Optional[str],
        Field(
            title="Api Allow Run As",
            description="""Optional list of email addresses of API users who can make calls on behalf of
other users.
""",
        ),
    ] = None

    bootstrap_admin_api_key: Annotated[
        Optional[str],
        Field(
            title="Bootstrap Admin Api Key",
            description="""API key that allows performing some admin actions without actually
having a real admin user in the database and config.
Only set this if you need to bootstrap Galaxy, in particular to create
a real admin user account via API.
You should probably not set this on a production server.
""",
        ),
    ] = None

    ga4gh_service_id: Annotated[
        Optional[str],
        Field(
            title="Ga4Gh Service Id",
            description="""Service ID for GA4GH services (exposed via the service-info endpoint for the Galaxy DRS API).
If unset, one will be generated using the URL the target API requests are made against.

For more information on GA4GH service definitions - check out
https://github.com/ga4gh-discovery/ga4gh-service-registry
and https://editor.swagger.io/?url=https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-registry/develop/service-registry.yaml

This value should likely reflect your service's URL. For instance for usegalaxy.org
this value should be org.usegalaxy. Particular Galaxy implementations will treat this
value as a prefix and append the service type to this ID. For instance for the DRS
service "id" (available via the DRS API) for the above configuration value would be
org.usegalaxy.drs.
""",
        ),
    ] = None

    ga4gh_service_organization_name: Annotated[
        Optional[str],
        Field(
            title="Ga4Gh Service Organization Name",
            description="""Service name for host organization (exposed via the service-info endpoint for the Galaxy DRS API).
If unset, one will be generated using ga4gh_service_id.

For more information on GA4GH service definitions - check out
https://github.com/ga4gh-discovery/ga4gh-service-registry
and https://editor.swagger.io/?url=https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-registry/develop/service-registry.yaml
""",
        ),
    ] = None

    ga4gh_service_organization_url: Annotated[
        Optional[str],
        Field(
            title="Ga4Gh Service Organization Url",
            description="""Organization URL for host organization (exposed via the service-info endpoint for the Galaxy DRS API).
If unset, one will be generated using the URL the target API requests are made against.

For more information on GA4GH service definitions - check out
https://github.com/ga4gh-discovery/ga4gh-service-registry
and https://editor.swagger.io/?url=https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-registry/develop/service-registry.yaml
""",
        ),
    ] = None

    ga4gh_service_environment: Annotated[
        Optional[str],
        Field(
            title="Ga4Gh Service Environment",
            description="""Service environment (exposed via the service-info endpoint for the Galaxy DRS API) for
implemented GA4GH services.

Suggested values are prod, test, dev, staging.

For more information on GA4GH service definitions - check out
https://github.com/ga4gh-discovery/ga4gh-service-registry
and https://editor.swagger.io/?url=https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-registry/develop/service-registry.yaml
""",
        ),
    ] = None

    enable_tool_tags: Annotated[
        bool,
        Field(
            title="Enable Tool Tags",
            description="""Enable tool tags (associating tools with tags). This has its own option
since its implementation has a few performance implications on startup for
large servers.
""",
        ),
    ] = False

    ftp_upload_dir: Annotated[
        Optional[str],
        Field(
            title="Ftp Upload Dir",
            description="""This should point to a directory containing subdirectories matching users'
identifier (defaults to e-mail), where Galaxy will look for files.
""",
        ),
    ] = None

    ftp_upload_dir_identifier: Annotated[
        Optional[str],
        Field(
            title="Ftp Upload Dir Identifier",
            description="""User attribute to use as subdirectory in calculating default ftp_upload_dir
pattern. By default this will be email so a user's FTP upload directory will be
${ftp_upload_dir}/${user.email}. Can set this to other attributes such as id or
username though.
""",
        ),
    ] = "email"

    ftp_upload_dir_template: Annotated[
        Optional[str],
        Field(
            title="Ftp Upload Dir Template",
            description="""Python string template used to determine an FTP upload directory for a
particular user.

Defaults to '${ftp_upload_dir}/${ftp_upload_dir_identifier}'.
""",
        ),
    ] = None

    ftp_upload_purge: Annotated[
        bool,
        Field(
            title="Ftp Upload Purge",
            description="""Set to false to prevent Galaxy from deleting uploaded FTP files
as it imports them.
""",
        ),
    ] = True

    expose_dataset_path: Annotated[
        bool,
        Field(
            title="Expose Dataset Path",
            description="""This option allows users to see the full path of datasets via the "View
Details" option in the history. This option also exposes the command line to
non-administrative users. Administrators can always see dataset paths.
""",
        ),
    ] = False

    job_metrics_config_file: Annotated[
        Optional[str],
        Field(
            title="Job Metrics Config File",
            description="""XML config file that contains the job metric collection configuration.""",
        ),
    ] = "job_metrics_conf.xml"

    expose_potentially_sensitive_job_metrics: Annotated[
        bool,
        Field(
            title="Expose Potentially Sensitive Job Metrics",
            description="""This option allows users to see the job metrics (except for environment
variables).
""",
        ),
    ] = False

    enable_legacy_sample_tracking_api: Annotated[
        bool,
        Field(
            title="Enable Legacy Sample Tracking Api",
            description="""Enable the API for sample tracking""",
        ),
    ] = False

    enable_data_manager_user_view: Annotated[
        bool,
        Field(
            title="Enable Data Manager User View",
            description="""Allow non-admin users to view available Data Manager options.""",
        ),
    ] = False

    data_manager_config_file: Annotated[
        Optional[str],
        Field(
            title="Data Manager Config File",
            description="""File where Data Managers are configured (.sample used if default does not exist).""",
        ),
    ] = "data_manager_conf.xml"

    shed_data_manager_config_file: Annotated[
        Optional[str],
        Field(
            title="Shed Data Manager Config File",
            description="""File where Tool Shed based Data Managers are configured. This file will be created
automatically upon data manager installation.
""",
        ),
    ] = "shed_data_manager_conf.xml"

    galaxy_data_manager_data_path: Annotated[
        Optional[str],
        Field(
            title="Galaxy Data Manager Data Path",
            description="""Directory to store Data Manager based tool-data. Defaults to the value of the
<tool_data_path> option.
""",
        ),
    ] = None

    job_config_file: Annotated[
        Optional[str],
        Field(
            title="Job Config File",
            description="""To increase performance of job execution and the web interface, you can
separate Galaxy into multiple processes. There are more than one way to do
this, and they are explained in detail in the documentation:

https://docs.galaxyproject.org/en/master/admin/scaling.html

By default, Galaxy manages and executes jobs from within a single process and
notifies itself of new jobs via in-memory queues. Jobs are run locally on
the system on which Galaxy is started. Advanced job running capabilities can
be configured through the job configuration file or the <job_config> option.
""",
        ),
    ] = "job_conf.yml"

    job_config: Annotated[
        # TODO: add model from job_config_schema.yml
        Optional[Dict[str, Any]],
        Field(
            title="Job Config",
            description="""Description of job running configuration, can be embedded into Galaxy configuration or loaded from an additional file with the job_config_file option.""",
        ),
    ] = None

    dependency_resolvers: Annotated[
        Optional[List[Any]],
        Field(
            title="Dependency Resolvers",
            description="""Rather than specifying a dependency_resolvers_config_file, the definition of the
resolvers to enable can be embedded into Galaxy's config with this option.
This has no effect if a dependency_resolvers_config_file is used.

The syntax, available resolvers, and documentation of their options is explained in detail in the
documentation:

https://docs.galaxyproject.org/en/master/admin/dependency_resolvers.html
""",
        ),
    ] = None

    dependency_resolution: Annotated[
        Optional[Dict[str, Any]],
        Field(
            title="Dependency Resolution",
            description="""Alternative representation of various dependency resolution parameters. Takes the
dictified version of a DependencyManager object - so this is ideal for automating the
configuration of dependency resolution from one application that uses a DependencyManager
to another.
""",
        ),
    ] = None

    default_job_resubmission_condition: Annotated[
        Optional[str],
        Field(
            title="Default Job Resubmission Condition",
            description="""When jobs fail due to job runner problems, Galaxy can be configured to retry
these or reroute the jobs to new destinations. Very fine control of this is
available with resubmit declarations in the job config. For simple deployments
of Galaxy though, the following attribute can define resubmission conditions
for all job destinations. If any job destination defines even one
resubmission condition explicitly in the job config - the condition described
by this option will not apply to that destination. For instance, the condition:
'attempt < 3 and unknown_error and (time_running < 300 or time_since_queued < 300)'
would retry up to two times jobs that didn't fail due to detected memory or
walltime limits but did fail quickly (either while queueing or running). The
commented out default below results in no default job resubmission condition,
failing jobs are just failed outright.
""",
        ),
    ] = None

    track_jobs_in_database: Annotated[
        bool,
        Field(
            title="Track Jobs In Database",
            description="""This option is deprecated, use the `mem-self` handler assignment option in the
job configuration instead.
""",
        ),
    ] = True

    use_tasked_jobs: Annotated[
        bool,
        Field(
            title="Use Tasked Jobs",
            description="""This enables splitting of jobs into tasks, if specified by the particular tool
config.
This is a new feature and not recommended for production servers yet.
""",
        ),
    ] = False

    local_task_queue_workers: Annotated[
        int,
        Field(
            title="Local Task Queue Workers",
            description="""This enables splitting of jobs into tasks, if specified by the particular tool
config.
This is a new feature and not recommended for production servers yet.
""",
        ),
    ] = 2

    job_handler_monitor_sleep: Annotated[
        float,
        Field(
            title="Job Handler Monitor Sleep",
            description="""Each Galaxy job handler process runs one thread responsible for discovering jobs and
dispatching them to runners. This thread operates in a loop and sleeps for the given
number of seconds at the end of each iteration. This can be decreased if extremely high
job throughput is necessary, but doing so can increase CPU usage of handler processes.
Float values are allowed.
""",
        ),
    ] = 1.0

    job_runner_monitor_sleep: Annotated[
        float,
        Field(
            title="Job Runner Monitor Sleep",
            description="""Each Galaxy job handler process runs one thread per job runner plugin responsible for
checking the state of queued and running jobs. This thread operates in a loop and
sleeps for the given number of seconds at the end of each iteration. This can be
decreased if extremely high job throughput is necessary, but doing so can increase CPU
usage of handler processes. Float values are allowed.
""",
        ),
    ] = 1.0

    workflow_monitor_sleep: Annotated[
        float,
        Field(
            title="Workflow Monitor Sleep",
            description="""Each Galaxy workflow handler process runs one thread responsible for
checking the state of active workflow invocations. This thread operates in a loop and
sleeps for the given number of seconds at the end of each iteration. This can be
decreased if extremely high job throughput is necessary, but doing so can increase CPU
usage of handler processes. Float values are allowed.
""",
        ),
    ] = 1.0

    metadata_strategy: Annotated[
        Literal["directory", "extended", "directory_celery", "extended_celery", "legacy"],
        Field(
            title="Metadata Strategy",
            description="""Determines how metadata will be set. Valid values are `directory`, `extended`,
`directory_celery` and `extended_celery`.
In extended mode jobs will decide if a tool run failed, the object stores
configuration is serialized and made available to the job and is used for
writing output datasets to the object store as part of the job and dynamic
output discovery (e.g. discovered datasets <discover_datasets>, unpopulated collections,
etc) happens as part of the job. In `directory_celery` and `extended_celery` metadata
will be set within a celery task.
""",
        ),
    ] = "directory"

    retry_metadata_internally: Annotated[
        bool,
        Field(
            title="Retry Metadata Internally",
            description="""Although it is fairly reliable, setting metadata can occasionally fail. In
these instances, you can choose to retry setting it internally or leave it in
a failed state (since retrying internally may cause the Galaxy process to be
unresponsive). If this option is set to false, the user will be given the
option to retry externally, or set metadata manually (when possible).
""",
        ),
    ] = True

    max_metadata_value_size: Annotated[
        int,
        Field(
            title="Max Metadata Value Size",
            description="""Very large metadata values can cause Galaxy crashes. This will allow
limiting the maximum metadata key size (in bytes used in memory, not the end
result database value size) Galaxy will attempt to save with a dataset. Use
0 to disable this feature. The default is 5MB, but as low as 1MB seems to be
a reasonable size.
""",
        ),
    ] = 5242880

    outputs_to_working_directory: Annotated[
        bool,
        Field(
            title="Outputs To Working Directory",
            description="""This option will override tool output paths to write outputs to the job
working directory (instead of to the file_path) and the job manager will move
the outputs to their proper place in the dataset directory on the Galaxy
server after the job completes. This is necessary (for example) if jobs run
on a cluster and datasets can not be created by the user running the jobs (e.g.
if the filesystem is mounted read-only or the jobs are run by a different
user than the galaxy user).
""",
        ),
    ] = False

    retry_job_output_collection: Annotated[
        int,
        Field(
            title="Retry Job Output Collection",
            description="""If your network filesystem's caching prevents the Galaxy server from seeing
the job's stdout and stderr files when it completes, you can retry reading
these files. The job runner will retry the number of times specified below,
waiting 1 second between tries. For NFS, you may want to try the -noac mount
option (Linux) or -actimeo=0 (Solaris).
""",
        ),
    ] = 0

    tool_evaluation_strategy: Annotated[
        Optional[Literal["local", "remote"]],
        Field(
            title="Tool Evaluation Strategy",
            description="""Determines which process will evaluate the tool command line. If set to "local" the tool command
line, configuration files and other dynamic values will be templated in the job
handler process. If set to ``remote`` the tool command line will be built as part of the
submitted job. Note that ``remote`` is a beta setting that will be useful for materializing
deferred datasets as part of the submitted job. Note also that you have to set ``metadata_strategy``
to ``extended`` if you set this option to ``remote``.
""",
        ),
    ] = "local"

    preserve_python_environment: Annotated[
        Optional[Literal["legacy_only", "legacy_and_local", "always"]],
        Field(
            title="Preserve Python Environment",
            description="""In the past Galaxy would preserve its Python environment when running jobs (
and still does for internal tools packaged with Galaxy). This behavior exposes
Galaxy internals to tools and could result in problems when activating
Python environments for tools (such as with Conda packaging). The default
legacy_only will restrict this behavior to tools identified by the Galaxy
team as requiring this environment. Set this to "always" to restore the
previous behavior (and potentially break Conda dependency resolution for many
tools). Set this to legacy_and_local to preserve the environment for legacy
tools and locally managed tools (this might be useful for instance if you are
installing software into Galaxy's virtualenv for tool development).
""",
        ),
    ] = "legacy_only"

    cleanup_job: Annotated[
        Optional[Literal["always", "onsuccess", "never"]],
        Field(
            title="Cleanup Job",
            description="""Clean up various bits of jobs left on the filesystem after completion. These
bits include the job working directory, external metadata temporary files,
and DRM stdout and stderr files (if using a DRM). Possible values are:
always, onsuccess, never
""",
        ),
    ] = "always"

    drmaa_external_runjob_script: Annotated[
        Optional[str],
        Field(
            title="Drmaa External Runjob Script",
            description="""When running DRMAA jobs as the Galaxy user
(https://docs.galaxyproject.org/en/master/admin/cluster.html#submitting-jobs-as-the-real-user)
this script is used to run the job script Galaxy generates for a tool execution.

Example value 'sudo -E scripts/drmaa_external_runner.py --assign_all_groups'
""",
        ),
    ] = None

    drmaa_external_killjob_script: Annotated[
        Optional[str],
        Field(
            title="Drmaa External Killjob Script",
            description="""When running DRMAA jobs as the Galaxy user
(https://docs.galaxyproject.org/en/master/admin/cluster.html#submitting-jobs-as-the-real-user)
this script is used to kill such jobs by Galaxy (e.g. if the user cancels
the job).

Example value 'sudo -E scripts/drmaa_external_killer.py'
""",
        ),
    ] = None

    external_chown_script: Annotated[
        Optional[str],
        Field(
            title="External Chown Script",
            description="""When running DRMAA jobs as the Galaxy user
(https://docs.galaxyproject.org/en/master/admin/cluster.html#submitting-jobs-as-the-real-user)
this script is used transfer permissions back and forth between the Galaxy user
and the user that is running the job.

Example value 'sudo -E scripts/external_chown_script.py'
""",
        ),
    ] = None

    real_system_username: Annotated[
        Optional[str],
        Field(
            title="Real System Username",
            description="""When running DRMAA jobs as the Galaxy user
(https://docs.galaxyproject.org/en/master/admin/cluster.html#submitting-jobs-as-the-real-user)
Galaxy can extract the user name from the email address (actually the local-part before the @)
or the username which are both stored in the Galaxy data base.
The latter option is particularly useful for installations that get the
authentication from LDAP.
Also, Galaxy can accept the name of a common system user (eg. galaxy_worker)
who can run every job being submitted. This user should not be the same user
running the galaxy system.
Possible values are user_email (default), username or <common_system_user>
""",
        ),
    ] = "user_email"

    environment_setup_file: Annotated[
        Optional[str],
        Field(
            title="Environment Setup File",
            description="""File to source to set up the environment when running jobs. By default, the
environment in which the Galaxy server starts is used when running jobs
locally, and the environment set up per the DRM's submission method and
policy is used when running jobs on a cluster (try testing with `qsub` on the
command line). environment_setup_file can be set to the path of a file on
the cluster that should be sourced by the user to set up the environment
prior to running tools. This can be especially useful for running jobs as
the actual user, to remove the need to configure each user's environment
individually.
""",
        ),
    ] = None

    markdown_export_css: Annotated[
        Optional[str],
        Field(
            title="Markdown Export Css",
            description="""CSS file to apply to all Markdown exports to PDF - currently used by
WeasyPrint during rendering an HTML export of the document to PDF.
""",
        ),
    ] = "markdown_export.css"

    markdown_export_css_pages: Annotated[
        Optional[str],
        Field(
            title="Markdown Export Css Pages",
            description="""CSS file to apply to "Galaxy Page" exports to PDF. Generally prefer
markdown_export_css, but this is here for deployments that
would like to tailor different kinds of exports.
""",
        ),
    ] = "markdown_export_pages.css"

    markdown_export_css_invocation_reports: Annotated[
        Optional[str],
        Field(
            title="Markdown Export Css Invocation Reports",
            description="""CSS file to apply to invocation report exports to PDF. Generally prefer
markdown_export_css, but this is here for deployments that
would like to tailor different kinds of exports.
""",
        ),
    ] = "markdown_export_invocation_reports.css"

    markdown_export_prologue: Annotated[
        str,
        Field(
            title="Markdown Export Prologue",
            description="""Prologue Markdown/HTML to apply to markdown exports to PDF. Allowing
branded headers.
""",
        ),
    ] = ""

    markdown_export_epilogue: Annotated[
        str,
        Field(
            title="Markdown Export Epilogue",
            description="""Prologue Markdown/HTML to apply to markdown exports to PDF. Allowing
branded footers.
""",
        ),
    ] = ""

    markdown_export_prologue_pages: Annotated[
        str,
        Field(
            title="Markdown Export Prologue Pages",
            description="""Alternative to markdown_export_prologue that applies just to page exports.""",
        ),
    ] = ""

    markdown_export_prologue_invocation_reports: Annotated[
        str,
        Field(
            title="Markdown Export Prologue Invocation Reports",
            description="""Alternative to markdown_export_prologue that applies just to invocation report
exports.
""",
        ),
    ] = ""

    markdown_export_epilogue_pages: Annotated[
        str,
        Field(
            title="Markdown Export Epilogue Pages",
            description="""Alternative to markdown_export_epilogue that applies just to page exports.""",
        ),
    ] = ""

    markdown_export_epilogue_invocation_reports: Annotated[
        str,
        Field(
            title="Markdown Export Epilogue Invocation Reports",
            description="""Alternative to markdown_export_epilogue that applies just to invocation report exports.""",
        ),
    ] = ""

    job_resource_params_file: Annotated[
        Optional[str],
        Field(
            title="Job Resource Params File",
            description="""Optional file containing job resource data entry fields definition.
These fields will be presented to users in the tool forms and allow them to
overwrite default job resources such as number of processors, memory and
walltime.
""",
        ),
    ] = "job_resource_params_conf.xml"

    workflow_resource_params_file: Annotated[
        Optional[str],
        Field(
            title="Workflow Resource Params File",
            description="""Similar to the above parameter, workflows can describe parameters used to
influence scheduling of jobs within the workflow. This requires both a description
of the fields available (which defaults to the definitions in
job_resource_params_file if not set).
""",
        ),
    ] = "workflow_resource_params_conf.xml"

    workflow_resource_params_mapper: Annotated[
        Optional[str],
        Field(
            title="Workflow Resource Params Mapper",
            description="""This parameter describes how to map users and workflows to a set of workflow
resource parameter to present (typically input IDs from workflow_resource_params_file).
If this this is a function reference it will be passed various inputs (workflow model
object and user) and it should produce a list of input IDs. If it is a path
it is expected to be an XML or YAML file describing how to map group names to parameter
descriptions (additional types of mappings via these files could be implemented but
haven't yet - for instance using workflow tags to do the mapping).

Sample default path 'config/workflow_resource_mapper_conf.yml.sample'
""",
        ),
    ] = None

    workflow_schedulers_config_file: Annotated[
        Optional[str],
        Field(
            title="Workflow Schedulers Config File",
            description="""Optional configuration file similar to `job_config_file` to specify
which Galaxy processes should schedule workflows.
""",
        ),
    ] = "workflow_schedulers_conf.xml"

    cache_user_job_count: Annotated[
        bool,
        Field(
            title="Cache User Job Count",
            description="""If using job concurrency limits (configured in job_config_file), several
extra database queries must be performed to determine the number of jobs a
user has dispatched to a given destination. By default, these queries will
happen for every job that is waiting to run, but if cache_user_job_count is
set to true, it will only happen once per iteration of the handler queue.
Although better for performance due to reduced queries, the trade-off is a
greater possibility that jobs will be dispatched past the configured limits
if running many handlers.
""",
        ),
    ] = False

    tool_filters: Annotated[
        Optional[str],
        Field(
            title="Tool Filters",
            description="""Define toolbox filters (https://galaxyproject.org/user-defined-toolbox-filters/)
that admins may use to restrict the tools to display.
""",
        ),
    ] = None

    tool_label_filters: Annotated[
        Optional[str],
        Field(
            title="Tool Label Filters",
            description="""Define toolbox filters (https://galaxyproject.org/user-defined-toolbox-filters/)
that admins may use to restrict the tool labels to display.
""",
        ),
    ] = None

    tool_section_filters: Annotated[
        Optional[str],
        Field(
            title="Tool Section Filters",
            description="""Define toolbox filters (https://galaxyproject.org/user-defined-toolbox-filters/)
that admins may use to restrict the tool sections to display.
""",
        ),
    ] = None

    user_tool_filters: Annotated[
        Optional[str],
        Field(
            title="User Tool Filters",
            description="""Define toolbox filters (https://galaxyproject.org/user-defined-toolbox-filters/)
that users may use to restrict the tools to display.
""",
        ),
    ] = "examples:restrict_upload_to_admins, examples:restrict_encode"

    user_tool_section_filters: Annotated[
        Optional[str],
        Field(
            title="User Tool Section Filters",
            description="""Define toolbox filters (https://galaxyproject.org/user-defined-toolbox-filters/)
that users may use to restrict the tool sections to display.
""",
        ),
    ] = "examples:restrict_text"

    user_tool_label_filters: Annotated[
        Optional[str],
        Field(
            title="User Tool Label Filters",
            description="""Define toolbox filters (https://galaxyproject.org/user-defined-toolbox-filters/)
that users may use to restrict the tool labels to display.
""",
        ),
    ] = "examples:restrict_upload_to_admins, examples:restrict_encode"

    toolbox_filter_base_modules: Annotated[
        Optional[str],
        Field(
            title="Toolbox Filter Base Modules",
            description="""The base module(s) that are searched for modules for toolbox filtering
(https://galaxyproject.org/user-defined-toolbox-filters/) functions.
""",
        ),
    ] = "galaxy.tools.filters,galaxy.tools.toolbox.filters,galaxy.tool_util.toolbox.filters"

    amqp_internal_connection: Annotated[
        Optional[str],
        Field(
            title="Amqp Internal Connection",
            description="""Galaxy uses AMQP internally for communicating between processes. For
example, when reloading the toolbox or locking job execution, the process
that handled that particular request will tell all others to also reload,
lock jobs, etc.
For connection examples, see https://docs.celeryq.dev/projects/kombu/en/stable/userguide/connections.html

Without specifying anything here, galaxy will first attempt to use your
specified database_connection above. If that's not specified either, Galaxy
will automatically create and use a separate sqlite database located in your
<galaxy>/database folder (indicated in the commented out line below).
""",
        ),
    ] = "sqlalchemy+sqlite:///./database/control.sqlite?isolation_level=IMMEDIATE"

    celery_conf: Annotated[
        Any,
        Field(
            title="Celery Conf",
            description="""Configuration options passed to Celery.

To refer to a task by name, use the template `galaxy.foo` where `foo` is the function name
of the task defined in the galaxy.celery.tasks module.

The `broker_url` option, if unset, defaults to the value of `amqp_internal_connection`.
The `result_backend` option must be set if the `enable_celery_tasks` option is set.

The galaxy.fetch_data task can be disabled by setting its route to "disabled": `galaxy.fetch_data: disabled`.
(Other tasks cannot be disabled on a per-task basis at this time.)

For details, see Celery documentation at https://docs.celeryq.dev/en/stable/userguide/configuration.html.
""",
        ),
    ] = {"task_routes": {"galaxy.fetch_data": "galaxy.external", "galaxy.set_job_metadata": "galaxy.external"}}

    celery_user_rate_limit: Annotated[
        float,
        Field(
            title="Celery User Rate Limit",
            description="""If set to a non-0 value, upper limit on number of
tasks that can be executed per user per second.
""",
        ),
    ] = 0.0

    use_pbkdf2: Annotated[
        bool,
        Field(
            title="Use Pbkdf2",
            description="""Allow disabling pbkdf2 hashing of passwords for legacy situations.
This should normally be left enabled unless there is a specific
reason to disable it.
""",
        ),
    ] = True

    error_report_file: Annotated[
        Optional[str],
        Field(
            title="Error Report File",
            description="""Path to error reports configuration file.""",
        ),
    ] = "error_report.yml"

    tool_destinations_config_file: Annotated[
        Optional[str],
        Field(
            title="Tool Destinations Config File",
            description="""Path to dynamic tool destinations configuration file.""",
        ),
    ] = "tool_destinations.yml"

    vault_config_file: Annotated[
        Optional[str],
        Field(
            title="Vault Config File",
            description="""Vault config file.""",
        ),
    ] = "vault_conf.yml"

    display_builtin_converters: Annotated[
        bool,
        Field(
            title="Display Builtin Converters",
            description="""Display built-in converters in the tool panel.""",
        ),
    ] = True

    themes_config_file: Annotated[
        Optional[str],
        Field(
            title="Themes Config File",
            description="""Optional file containing one or more themes for galaxy. If several themes
are defined, users can choose their preferred theme in the client.
""",
        ),
    ] = "themes_conf.yml"

    expired_notifications_cleanup_interval: Annotated[
        int,
        Field(
            title="Expired Notifications Cleanup Interval",
            description="""The interval in seconds between attempts to delete all expired notifications from the database (every 24 hours by default). Runs in a Celery task.""",
        ),
    ] = 86400


class UserConfigResponse(UserOnlyComputedGalaxyConfig, ExposableGalaxyConfig, ApiCompatibleConfigValues):
    """Configuration values that can be exposed to users."""

    pass


class AdminOnlyConfigResponse(AdminOnlyComputedGalaxyConfig, AdminExposableGalaxyConfig, ApiCompatibleConfigValues):
    """Configuration values that can be exposed to admins."""

    pass


AnyGalaxyConfigResponse = Annotated[
    Union[UserConfigResponse, AdminOnlyConfigResponse], Field(discriminator="is_admin_user")
]
