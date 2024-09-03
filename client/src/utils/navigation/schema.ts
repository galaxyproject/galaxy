import { type Component, ROOT_COMPONENT as raw_root_component, type SelectorTemplate } from "./index";

interface Root_messages extends Component {
    all: SelectorTemplate;
    error: SelectorTemplate;
    warning: SelectorTemplate;
    done: SelectorTemplate;
    info: SelectorTemplate;
    donelarge: SelectorTemplate;
    infolarge: SelectorTemplate;
    require_login: SelectorTemplate;
}
interface Root_ extends Component {
    editable_text: SelectorTemplate;
    tooltip_balloon: SelectorTemplate;
    left_panel_drag: SelectorTemplate;
    left_panel_collapse: SelectorTemplate;
    right_panel_drag: SelectorTemplate;
    right_panel_collapse: SelectorTemplate;
    by_attribute: SelectorTemplate;
    messages: Root_messages;
}
interface Rootmasthead extends Component {
    _: SelectorTemplate;
    user: SelectorTemplate;
    register_or_login: SelectorTemplate;
    user_menu: SelectorTemplate;
    workflow: SelectorTemplate;
    username: SelectorTemplate;
    logged_in_only: SelectorTemplate;
    logged_out_only: SelectorTemplate;
}
interface Rootpreferencesobject_store_selection extends Component {
    option_buttons: SelectorTemplate;
    option_button: SelectorTemplate;
}
interface Rootpreferences extends Component {
    sign_out: SelectorTemplate;
    change_password: SelectorTemplate;
    manage_information: SelectorTemplate;
    toolbox_filters: SelectorTemplate;
    manage_api_key: SelectorTemplate;
    current_email: SelectorTemplate;
    get_new_key: SelectorTemplate;
    api_key_input: SelectorTemplate;
    object_store: SelectorTemplate;
    delete_account: SelectorTemplate;
    delete_account_input: SelectorTemplate;
    delete_account_ok_btn: SelectorTemplate;
    email_input: SelectorTemplate;
    username_input: SelectorTemplate;
    object_store_selection: Rootpreferencesobject_store_selection;
}
interface Roottoolbox_filters extends Component {
    input: SelectorTemplate;
    submit: SelectorTemplate;
}
interface Rootchange_user_email extends Component {
    submit: SelectorTemplate;
}
interface Rootchange_user_password extends Component {
    submit: SelectorTemplate;
}
interface Rootchange_user_address extends Component {
    address_button: SelectorTemplate;
}
interface Rootsign_out extends Component {
    cancel_button: SelectorTemplate;
    sign_out_button: SelectorTemplate;
}
interface Rootdataset_details extends Component {
    _: SelectorTemplate;
    tool_parameters: SelectorTemplate;
    transform_action: SelectorTemplate;
    deferred_source_uri: SelectorTemplate;
}
interface Rootobject_store_details extends Component {
    badge_of_type: SelectorTemplate;
}
type Roothistory_panelmenu = Component;
interface Roothistory_panelitem extends Component {
    _: SelectorTemplate;
    title: SelectorTemplate;
    hid: SelectorTemplate;
    name: SelectorTemplate;
    datatype: SelectorTemplate;
    details: SelectorTemplate;
    title_button_area: SelectorTemplate;
    primary_action_buttons: SelectorTemplate;
    secondary_action_buttons: SelectorTemplate;
    summary: SelectorTemplate;
    blurb: SelectorTemplate;
    dbkey: SelectorTemplate;
    info: SelectorTemplate;
    peek: SelectorTemplate;
    toolhelp_title: SelectorTemplate;
    state_icon: SelectorTemplate;
    display_button: SelectorTemplate;
    edit_button: SelectorTemplate;
    delete_button: SelectorTemplate;
    download_button: SelectorTemplate;
    info_button: SelectorTemplate;
    rerun_button: SelectorTemplate;
    alltags: SelectorTemplate;
}
interface Roothistory_panelcontent_item extends Component {
    _: SelectorTemplate;
    title: SelectorTemplate;
    details: SelectorTemplate;
    summary: SelectorTemplate;
    hid: SelectorTemplate;
    name: SelectorTemplate;
    blurb: SelectorTemplate;
    dbkey: SelectorTemplate;
    datatype: SelectorTemplate;
    info: SelectorTemplate;
    peek: SelectorTemplate;
    toolhelp_title: SelectorTemplate;
    display_button: SelectorTemplate;
    edit_button: SelectorTemplate;
    delete_button: SelectorTemplate;
    rerun_button: SelectorTemplate;
    visualize_button: SelectorTemplate;
    collection_job_details_button: SelectorTemplate;
    download_button: SelectorTemplate;
    info_button: SelectorTemplate;
    alltags: SelectorTemplate;
    metadata_file_download: SelectorTemplate;
    dataset_operations_dropdown: SelectorTemplate;
}
interface Roothistory_paneleditor extends Component {
    _: SelectorTemplate;
    name: SelectorTemplate;
    toggle: SelectorTemplate;
    form: SelectorTemplate;
    name_input: SelectorTemplate;
    annotation_input: SelectorTemplate;
    tags_input: SelectorTemplate;
    save_button: SelectorTemplate;
}
interface Roothistory_paneltag_editor extends Component {
    _: SelectorTemplate;
    toggle: SelectorTemplate;
    display: SelectorTemplate;
    input: SelectorTemplate;
    tag_area: SelectorTemplate;
    tag_close_btn: SelectorTemplate;
}
interface Roothistory_panelmulti_operations extends Component {
    show_button: SelectorTemplate;
    action_button: SelectorTemplate;
    action_menu: SelectorTemplate;
}
interface Roothistory_panelcollection_view extends Component {
    _: SelectorTemplate;
    nav_menu: SelectorTemplate;
    back_button: SelectorTemplate;
    back: SelectorTemplate;
    title: SelectorTemplate;
    title_input: SelectorTemplate;
    subtitle: SelectorTemplate;
    elements_warning: SelectorTemplate;
    tag_area_button: SelectorTemplate;
    tag_area_input: SelectorTemplate;
    list_items: SelectorTemplate;
}
interface Roothistory_panel extends Component {
    menu: Roothistory_panelmenu;
    item: Roothistory_panelitem;
    content_item: Roothistory_panelcontent_item;
    editor: Roothistory_paneleditor;
    tag_editor: Roothistory_paneltag_editor;
    multi_operations: Roothistory_panelmulti_operations;
    collection_view: Roothistory_panelcollection_view;
    _: SelectorTemplate;
    search: SelectorTemplate;
    refresh_button: SelectorTemplate;
    name: SelectorTemplate;
    name_edit_input: SelectorTemplate;
    contents: SelectorTemplate;
    empty_message: SelectorTemplate;
    size: SelectorTemplate;
    tag_area: SelectorTemplate;
    tag_area_button: SelectorTemplate;
    tag_area_input: SelectorTemplate;
    tag_close_btn: SelectorTemplate;
    tags: SelectorTemplate;
    annotation_icon: SelectorTemplate;
    annotation_area: SelectorTemplate;
    annotation_editable_text: SelectorTemplate;
    annotation_edit: SelectorTemplate;
    annotation_done: SelectorTemplate;
    options_button: SelectorTemplate;
    options_button_icon: SelectorTemplate;
    options_menu: SelectorTemplate;
    options_menu_item: SelectorTemplate;
    options_show_export_history_to_file: SelectorTemplate;
    collection_menu_button: SelectorTemplate;
    collection_menu_edit_attributes: SelectorTemplate;
    new_history_button: SelectorTemplate;
    histories_operation_menu: SelectorTemplate;
    multi_view_button: SelectorTemplate;
    pagination_pages: SelectorTemplate;
    pagination_pages_options: SelectorTemplate;
    pagination_pages_selected_option: SelectorTemplate;
    pagination_next: SelectorTemplate;
    pagination_previous: SelectorTemplate;
}
interface Rootedit_dataset_attributesdbkey_dropdown_results extends Component {
    _: SelectorTemplate;
    dbkey_dropdown_option: SelectorTemplate;
}
interface Rootedit_dataset_attributes extends Component {
    database_build_dropdown: SelectorTemplate;
    save_btn: SelectorTemplate;
    dbkey_dropdown_results: Rootedit_dataset_attributesdbkey_dropdown_results;
}
interface Rootedit_collection_attributes extends Component {
    alert_info: SelectorTemplate;
    database_genome_tab: SelectorTemplate;
    datatypes_tab: SelectorTemplate;
    data_value: SelectorTemplate;
    save_dbkey_btn: SelectorTemplate;
    save_datatype_btn: SelectorTemplate;
}
interface Roottool_panel extends Component {
    tool_link: SelectorTemplate;
    outer_tool_link: SelectorTemplate;
    data_source_tool_link: SelectorTemplate;
    search: SelectorTemplate;
    workflow_names: SelectorTemplate;
    views_button: SelectorTemplate;
    views_menu_item: SelectorTemplate;
    panel_labels: SelectorTemplate;
}
interface Rootmulti_history_panelhistory_dropdown_menu extends Component {
    _: SelectorTemplate;
    delete: SelectorTemplate;
    purge: SelectorTemplate;
}
interface Rootmulti_history_panelcopy_history_modal extends Component {
    _: SelectorTemplate;
    copy_btn: SelectorTemplate;
}
interface Rootmulti_history_panel extends Component {
    _: SelectorTemplate;
    item: SelectorTemplate;
    histories: SelectorTemplate;
    current_label: SelectorTemplate;
    switch_history: SelectorTemplate;
    current_history_check: SelectorTemplate;
    empty_message_check: SelectorTemplate;
    switch_button: SelectorTemplate;
    history_dropdown_menu: Rootmulti_history_panelhistory_dropdown_menu;
    copy_history_modal: Rootmulti_history_panelcopy_history_modal;
}
interface Rootpublished_histories extends Component {
    histories: SelectorTemplate;
    search_input: SelectorTemplate;
    advanced_search_toggle: SelectorTemplate;
    advanced_search_name_input: SelectorTemplate;
    advanced_search_tag_input: SelectorTemplate;
    tag_content: SelectorTemplate;
    column_header: SelectorTemplate;
}
interface Rootshared_histories extends Component {
    _: SelectorTemplate;
    histories: SelectorTemplate;
}
interface Roothistory_copy_elements extends Component {
    dataset_checkbox: SelectorTemplate;
    collection_checkbox: SelectorTemplate;
    new_history_name: SelectorTemplate;
    copy_button: SelectorTemplate;
    done_link: SelectorTemplate;
}
interface Rootcollection_builders extends Component {
    clear_filters: SelectorTemplate;
    forward_datasets: SelectorTemplate;
    reverse_datasets: SelectorTemplate;
}
interface Roothistoriessharing extends Component {
    unshare_user_button: SelectorTemplate;
    unshare_with_user_button: SelectorTemplate;
    user_email_input: SelectorTemplate;
    submit_sharing_with: SelectorTemplate;
    share_with_collapse: SelectorTemplate;
    share_with_multiselect: SelectorTemplate;
    share_with_input: SelectorTemplate;
    make_accessible: SelectorTemplate;
    make_publishable: SelectorTemplate;
}
interface Roothistories extends Component {
    sharing: Roothistoriessharing;
}
interface Rootfiles_dialog extends Component {
    ftp_label: SelectorTemplate;
    ftp_details: SelectorTemplate;
    row: SelectorTemplate;
    back_btn: SelectorTemplate;
}
interface Roothistory_export extends Component {
    export_link: SelectorTemplate;
    running: SelectorTemplate;
    generated_export_link: SelectorTemplate;
    copy_export_link: SelectorTemplate;
    show_job_link: SelectorTemplate;
    job_table: SelectorTemplate;
    job_table_ok: SelectorTemplate;
    tab_export_to_file: SelectorTemplate;
    directory_input: SelectorTemplate;
    name_input: SelectorTemplate;
    export_button: SelectorTemplate;
    success_message: SelectorTemplate;
}
interface Roothistory_export_tasks extends Component {
    direct_download: SelectorTemplate;
    file_source_tab: SelectorTemplate;
    remote_file_name_input: SelectorTemplate;
    toggle_options_link: SelectorTemplate;
    export_format_selector: SelectorTemplate;
    select_format: SelectorTemplate;
}
interface Rootlast_export_record extends Component {
    details: SelectorTemplate;
    preparing_export: SelectorTemplate;
    export_format: SelectorTemplate;
    up_to_date_icon: SelectorTemplate;
    outdated_icon: SelectorTemplate;
    expiration_warning_icon: SelectorTemplate;
    download_btn: SelectorTemplate;
    reimport_btn: SelectorTemplate;
}
interface Roothistory_import extends Component {
    radio_button_remote_files: SelectorTemplate;
    import_button: SelectorTemplate;
    running: SelectorTemplate;
    success_message: SelectorTemplate;
}
interface Rootpageseditor extends Component {
    save: SelectorTemplate;
    embed_dataset: SelectorTemplate;
    dataset_selector: SelectorTemplate;
    embed_dialog_add_button: SelectorTemplate;
    markdown_editor: SelectorTemplate;
}
interface Rootpages extends Component {
    create: SelectorTemplate;
    submit: SelectorTemplate;
    export: SelectorTemplate;
    editor: Rootpageseditor;
}
interface Rootlogin extends Component {
    form: SelectorTemplate;
    submit: SelectorTemplate;
}
interface Rootregistration extends Component {
    toggle: SelectorTemplate;
    form: SelectorTemplate;
    submit: SelectorTemplate;
}
interface Roottool_form extends Component {
    options: SelectorTemplate;
    execute: SelectorTemplate;
    parameter_div: SelectorTemplate;
    parameter_checkbox: SelectorTemplate;
    parameter_input: SelectorTemplate;
    parameter_textarea: SelectorTemplate;
    repeat_insert: SelectorTemplate;
    reference: SelectorTemplate;
    about: SelectorTemplate;
}
interface Rootworkflowscreate extends Component {
    name: SelectorTemplate;
    annotation: SelectorTemplate;
    submit: SelectorTemplate;
}
interface Rootworkflows extends Component {
    new_button: SelectorTemplate;
    import_button: SelectorTemplate;
    save_button: SelectorTemplate;
    search_box: SelectorTemplate;
    workflow_table: SelectorTemplate;
    workflow_rows: SelectorTemplate;
    external_link: SelectorTemplate;
    trs_icon: SelectorTemplate;
    run_button: SelectorTemplate;
    bookmark_link: SelectorTemplate;
    workflow_with_name: SelectorTemplate;
    create: Rootworkflowscreate;
}
interface Rootvisualization extends Component {
    _: SelectorTemplate;
    plugin_item: SelectorTemplate;
}
interface Roottrs_search extends Component {
    search: SelectorTemplate;
    search_result: SelectorTemplate;
    import_button: SelectorTemplate;
    select_server_button: SelectorTemplate;
    import_version: SelectorTemplate;
    select_server: SelectorTemplate;
}
interface Roottrs_import extends Component {
    input: SelectorTemplate;
    import_version: SelectorTemplate;
    select_server_button: SelectorTemplate;
    select_server: SelectorTemplate;
    url_input: SelectorTemplate;
    url_import_button: SelectorTemplate;
}
interface Rootworkflow_run extends Component {
    warning: SelectorTemplate;
    input_div: SelectorTemplate;
    input_data_div: SelectorTemplate;
    subworkflow_step_icon: SelectorTemplate;
    run_workflow: SelectorTemplate;
    validation_error: SelectorTemplate;
    expand_form_link: SelectorTemplate;
    expanded_form: SelectorTemplate;
    new_history_target_link: SelectorTemplate;
    runtime_setting_button: SelectorTemplate;
    runtime_setting_target: SelectorTemplate;
    input_select_field: SelectorTemplate;
    primary_storage_indciator: SelectorTemplate;
    intermediate_storage_indciator: SelectorTemplate;
}
interface Rootworkflow_editornode extends Component {
    _: SelectorTemplate;
    title: SelectorTemplate;
    destroy: SelectorTemplate;
    clone: SelectorTemplate;
    output_data_row: SelectorTemplate;
    output_terminal: SelectorTemplate;
    input_terminal: SelectorTemplate;
    input_mapping_icon: SelectorTemplate;
    workflow_output_toggle: SelectorTemplate;
    workflow_output_toggle_active: SelectorTemplate;
}
interface Rootworkflow_editor extends Component {
    node: Rootworkflow_editornode;
    canvas_body: SelectorTemplate;
    edit_annotation: SelectorTemplate;
    edit_name: SelectorTemplate;
    tool_menu: SelectorTemplate;
    tool_menu_section_link: SelectorTemplate;
    tool_menu_item_link: SelectorTemplate;
    workflow_link: SelectorTemplate;
    insert_steps: SelectorTemplate;
    connect_icon: SelectorTemplate;
    collapse_icon: SelectorTemplate;
    edit_subworkflow: SelectorTemplate;
    node_title: SelectorTemplate;
    label_input: SelectorTemplate;
    annotation_input: SelectorTemplate;
    step_when: SelectorTemplate;
    param_type_form: SelectorTemplate;
    configure_output: SelectorTemplate;
    label_output: SelectorTemplate;
    duplicate_label_error: SelectorTemplate;
    rename_output: SelectorTemplate;
    change_datatype: SelectorTemplate;
    select_datatype_text_search: SelectorTemplate;
    select_datatype: SelectorTemplate;
    add_tags: SelectorTemplate;
    remove_tags: SelectorTemplate;
    tool_version_button: SelectorTemplate;
    connector_for: SelectorTemplate;
    connector_invalid_for: SelectorTemplate;
    connector_destroy_callout: SelectorTemplate;
    save_button: SelectorTemplate;
    state_modal_body: SelectorTemplate;
    modal_button_continue: SelectorTemplate;
}
interface Rootworkflow_show extends Component {
    title: SelectorTemplate;
    import_link: SelectorTemplate;
}
interface Rootinvocations extends Component {
    invocations_table: SelectorTemplate;
    invocations_table_rows: SelectorTemplate;
    pager: SelectorTemplate;
    pager_page: SelectorTemplate;
    pager_page_next: SelectorTemplate;
    pager_page_last: SelectorTemplate;
    pager_page_first: SelectorTemplate;
    pager_page_previous: SelectorTemplate;
    pager_page_active: SelectorTemplate;
    state_details: SelectorTemplate;
    toggle_invocation_details: SelectorTemplate;
    progress_steps_note: SelectorTemplate;
    progress_jobs_note: SelectorTemplate;
    hide_invocation_graph: SelectorTemplate;
    invocation_tab: SelectorTemplate;
    invocation_details_tab: SelectorTemplate;
    input_details_title: SelectorTemplate;
    input_details_name: SelectorTemplate;
    step_title: SelectorTemplate;
    step_details: SelectorTemplate;
    step_output_collection: SelectorTemplate;
    step_output_collection_toggle: SelectorTemplate;
    step_output_collection_element_identifier: SelectorTemplate;
    step_output_collection_element_datatype: SelectorTemplate;
    step_job_details: SelectorTemplate;
    step_job_table: SelectorTemplate;
    step_job_table_rows: SelectorTemplate;
    step_job_information: SelectorTemplate;
    step_job_information_tool_id: SelectorTemplate;
}
interface Roottourpopover extends Component {
    _: SelectorTemplate;
    title: SelectorTemplate;
    content: SelectorTemplate;
    next: SelectorTemplate;
    end: SelectorTemplate;
}
interface Roottour extends Component {
    popover: Roottourpopover;
}
interface Rootadminallowlist extends Component {
    toolshed: SelectorTemplate;
    local: SelectorTemplate;
    sanitized: SelectorTemplate;
    rendered_active: SelectorTemplate;
}
interface Rootadminmanage_dependencies extends Component {
    dependencies: SelectorTemplate;
    containers: SelectorTemplate;
    unused: SelectorTemplate;
    resolver_type: SelectorTemplate;
    container_type: SelectorTemplate;
    unused_paths: SelectorTemplate;
}
interface Rootadminmanage_jobs extends Component {
    job_lock: SelectorTemplate;
    job_lock_label: SelectorTemplate;
    cutoff: SelectorTemplate;
}
interface Rootadmintoolshed extends Component {
    repo_search: SelectorTemplate;
    search_results: SelectorTemplate;
    upgrade_notification: SelectorTemplate;
}
interface Rootadminindex extends Component {
    datatypes: SelectorTemplate;
    dependencies: SelectorTemplate;
    data_tables: SelectorTemplate;
    display_applications: SelectorTemplate;
    errors: SelectorTemplate;
    forms: SelectorTemplate;
    jobs: SelectorTemplate;
    local_data: SelectorTemplate;
    metadata: SelectorTemplate;
    tool_versions: SelectorTemplate;
    toolshed: SelectorTemplate;
    users: SelectorTemplate;
    quotas: SelectorTemplate;
    groups: SelectorTemplate;
    roles: SelectorTemplate;
    impersonate: SelectorTemplate;
    allowlist: SelectorTemplate;
}
interface Rootadmin extends Component {
    allowlist: Rootadminallowlist;
    manage_dependencies: Rootadminmanage_dependencies;
    manage_jobs: Rootadminmanage_jobs;
    toolshed: Rootadmintoolshed;
    index: Rootadminindex;
    warning: SelectorTemplate;
    jobs_title: SelectorTemplate;
    datatypes_grid: SelectorTemplate;
    data_tables_grid: SelectorTemplate;
    display_applications_grid: SelectorTemplate;
    update_jobs: SelectorTemplate;
    dm_title: SelectorTemplate;
    dm_data_managers_card: SelectorTemplate;
    dm_jobs_button: SelectorTemplate;
    dm_jobs_breadcrumb: SelectorTemplate;
    dm_jobs_table: SelectorTemplate;
    dm_job: SelectorTemplate;
    dm_job_breadcrumb: SelectorTemplate;
    dm_job_data_manager_card: SelectorTemplate;
    dm_job_data_card: SelectorTemplate;
    dm_table_button: SelectorTemplate;
    dm_table_card: SelectorTemplate;
    users_grid: SelectorTemplate;
    users_grid_create_button: SelectorTemplate;
    groups_grid_create_button: SelectorTemplate;
    registration_form: SelectorTemplate;
    groups_grid: SelectorTemplate;
    roles_grid: SelectorTemplate;
    groups_create_view: SelectorTemplate;
}
interface Rootlibrariesfolder extends Component {
    add_items_button: SelectorTemplate;
    add_items_menu: SelectorTemplate;
    add_items_options: SelectorTemplate;
    add_folder: SelectorTemplate;
    add_to_history: SelectorTemplate;
    add_to_history_datasets: SelectorTemplate;
    add_to_history_collection: SelectorTemplate;
    import_modal: SelectorTemplate;
    import_datasets_ok_button: SelectorTemplate;
    import_datasets_cancel_button: SelectorTemplate;
    export_to_history_options: SelectorTemplate;
    export_to_history_paired_option: SelectorTemplate;
    export_to_history_collection_name: SelectorTemplate;
    export_to_history_new_history: SelectorTemplate;
    clear_filters: SelectorTemplate;
    import_progress_bar: SelectorTemplate;
    import_history_content: SelectorTemplate;
    import_history_contents_items: SelectorTemplate;
    import_from_path_textarea: SelectorTemplate;
    select_all: SelectorTemplate;
    select_one: SelectorTemplate;
    select_dataset: SelectorTemplate;
    empty_folder_message: SelectorTemplate;
    btn_open_parent_folder: SelectorTemplate;
    edit_folder_btn: SelectorTemplate;
    description_field: SelectorTemplate;
    description_field_shrinked: SelectorTemplate;
    save_folder_btn: SelectorTemplate;
    input_folder_name: SelectorTemplate;
    input_folder_description: SelectorTemplate;
    download_button: SelectorTemplate;
    delete_btn: SelectorTemplate;
    toast_msg: SelectorTemplate;
    toast_warning: SelectorTemplate;
    select_import_dir_item: SelectorTemplate;
    import_dir_btn: SelectorTemplate;
    manage_dataset_permissions_btn: SelectorTemplate;
    make_private_btn: SelectorTemplate;
    access_dataset_roles: SelectorTemplate;
    private_dataset_icon: SelectorTemplate;
    open_location_details_btn: SelectorTemplate;
    location_details_ok_btn: SelectorTemplate;
    add_history_items: SelectorTemplate;
}
interface Rootlibrariesdataset extends Component {
    table: SelectorTemplate;
    table_rows: SelectorTemplate;
}
interface Rootlibraries extends Component {
    _: SelectorTemplate;
    create_new_library_btn: SelectorTemplate;
    permission_library_btn: SelectorTemplate;
    toolbtn_save_permissions: SelectorTemplate;
    save_new_library_btn: SelectorTemplate;
    search_field: SelectorTemplate;
    new_library_name_input: SelectorTemplate;
    new_library_description_input: SelectorTemplate;
    add_items_permission: SelectorTemplate;
    add_items_permission_input_field: SelectorTemplate;
    add_items_permission_field_text: SelectorTemplate;
    add_items_permission_option: SelectorTemplate;
    folder: Rootlibrariesfolder;
    dataset: Rootlibrariesdataset;
}
interface Rootgrids extends Component {
    body: SelectorTemplate;
    free_text_search: SelectorTemplate;
}
interface Rootgiesjupyter extends Component {
    body: SelectorTemplate;
    trusted_notification: SelectorTemplate;
}
interface Rootgies extends Component {
    jupyter: Rootgiesjupyter;
    spinner: SelectorTemplate;
    iframe: SelectorTemplate;
}
interface Rootuploadcomposite extends Component {
    table: SelectorTemplate;
    close: SelectorTemplate;
}
interface Rootupload extends Component {
    composite: Rootuploadcomposite;
    tab: SelectorTemplate;
    ftp_add: SelectorTemplate;
    ftp_popup: SelectorTemplate;
    ftp_items: SelectorTemplate;
    ftp_close: SelectorTemplate;
    row: SelectorTemplate;
    settings_button: SelectorTemplate;
    paste_content: SelectorTemplate;
    settings: SelectorTemplate;
    setting_deferred: SelectorTemplate;
    start: SelectorTemplate;
    start_uploading: SelectorTemplate;
    close: SelectorTemplate;
    rule_source_content: SelectorTemplate;
    rule_select_data_type: SelectorTemplate;
    rule_select_input_type: SelectorTemplate;
    rule_dataset_selector: SelectorTemplate;
    rule_dataset_selector_row: SelectorTemplate;
    build_btn: SelectorTemplate;
    file_source_selector: SelectorTemplate;
    file_dialog_ok: SelectorTemplate;
    paste_new: SelectorTemplate;
}
interface Rootrule_builder extends Component {
    _: SelectorTemplate;
    menu_button_filter: SelectorTemplate;
    menu_button_rules: SelectorTemplate;
    menu_button_column: SelectorTemplate;
    menu_item_rule_type: SelectorTemplate;
    rule_editor: SelectorTemplate;
    rule_editor_ok: SelectorTemplate;
    add_mapping_menu: SelectorTemplate;
    add_mapping_button: SelectorTemplate;
    mapping_edit: SelectorTemplate;
    mapping_remove_column: SelectorTemplate;
    mapping_add_column: SelectorTemplate;
    mapping_ok: SelectorTemplate;
    main_button_ok: SelectorTemplate;
    collection_name_input: SelectorTemplate;
    view_source: SelectorTemplate;
    source: SelectorTemplate;
    table: SelectorTemplate;
    extension_select: SelectorTemplate;
}
interface Rootcharts extends Component {
    visualize_button: SelectorTemplate;
    viewport_canvas: SelectorTemplate;
}
interface Rootjob_details extends Component {
    galaxy_tool_with_id: SelectorTemplate;
    tool_exit_code: SelectorTemplate;
}
export interface root_component {
    _: Root_;
    masthead: Rootmasthead;
    preferences: Rootpreferences;
    toolbox_filters: Roottoolbox_filters;
    change_user_email: Rootchange_user_email;
    change_user_password: Rootchange_user_password;
    change_user_address: Rootchange_user_address;
    sign_out: Rootsign_out;
    dataset_details: Rootdataset_details;
    object_store_details: Rootobject_store_details;
    history_panel: Roothistory_panel;
    edit_dataset_attributes: Rootedit_dataset_attributes;
    edit_collection_attributes: Rootedit_collection_attributes;
    tool_panel: Roottool_panel;
    multi_history_panel: Rootmulti_history_panel;
    published_histories: Rootpublished_histories;
    shared_histories: Rootshared_histories;
    history_copy_elements: Roothistory_copy_elements;
    collection_builders: Rootcollection_builders;
    histories: Roothistories;
    files_dialog: Rootfiles_dialog;
    history_export: Roothistory_export;
    history_export_tasks: Roothistory_export_tasks;
    last_export_record: Rootlast_export_record;
    history_import: Roothistory_import;
    pages: Rootpages;
    login: Rootlogin;
    registration: Rootregistration;
    tool_form: Roottool_form;
    workflows: Rootworkflows;
    visualization: Rootvisualization;
    trs_search: Roottrs_search;
    trs_import: Roottrs_import;
    workflow_run: Rootworkflow_run;
    workflow_editor: Rootworkflow_editor;
    workflow_show: Rootworkflow_show;
    invocations: Rootinvocations;
    tour: Roottour;
    admin: Rootadmin;
    libraries: Rootlibraries;
    grids: Rootgrids;
    gies: Rootgies;
    upload: Rootupload;
    rule_builder: Rootrule_builder;
    charts: Rootcharts;
    job_details: Rootjob_details;
}
export const ROOT_COMPONENT = raw_root_component as unknown as root_component;
