/** define the 'Analyze Data'/analysis/main/home page for Galaxy
 *  * has a masthead
 *  * a left tool menu to allow the user to load tools in the center panel
 *  * a right history menu that shows the user's current data
 *  * a center panel
 *  Both panels (generally) persist while the center panel shows any
 *  UI needed for the current step of an analysis, like:
 *      * tool forms to set tool parameters,
 *      * tables showing the contents of datasets
 *      * etc.
 */

import _ from "underscore";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import decodeUriComponent from "decode-uri-component";
import Router from "layout/router";
import ToolForm from "mvc/tool/tool-form";
import FormWrapper from "mvc/form/form-wrapper";
import Sharing from "components/Sharing.vue";
import UserPreferences from "mvc/user/user-preferences";
import CustomBuilds from "mvc/user/user-custom-builds";
import Tours from "mvc/tours";
import GridView from "mvc/grid/grid-view";
import GridShared from "mvc/grid/grid-shared";
import Workflows from "mvc/workflow/workflow";
import WorkflowImport from "components/WorkflowImport.vue";
import HistoryImport from "components/HistoryImport.vue";
import HistoryView from "components/HistoryView.vue";
import HistoryList from "mvc/history/history-list";
import PluginList from "components/PluginList.vue";
import ToolFormComposite from "mvc/tool/tool-form-composite";
import QueryStringParsing from "utils/query-string-parsing";
import Utils from "utils/utils";
import Ui from "mvc/ui/ui-misc";
import DatasetError from "mvc/dataset/dataset-error";
import DatasetEditAttributes from "mvc/dataset/dataset-edit-attributes";
import Citations from "components/Citations.vue";
import DisplayStructure from "components/DisplayStructured.vue";
import Vue from "vue";

/** Routes */
export const getAnalysisRouter = Galaxy =>
    Router.extend({
        routes: {
            "(/)(#)(_=_)": "home",
            "(/)root*": "home",
            "(/)tours(/)(:tour_id)": "show_tours",
            "(/)user(/)": "show_user",
            "(/)user(/)(:form_id)": "show_user_form",
            "(/)pages(/)create(/)": "show_pages_create",
            "(/)pages(/)edit(/)": "show_pages_edit",
            "(/)pages(/)sharing(/)": "show_pages_sharing",
            "(/)pages(/)(:action_id)": "show_pages",
            "(/)visualizations(/)": "show_plugins",
            "(/)visualizations(/)edit(/)": "show_visualizations_edit",
            "(/)visualizations(/)sharing(/)": "show_visualizations_sharing",
            "(/)visualizations/(:action_id)": "show_visualizations",
            "(/)workflows/import": "show_workflows_import",
            "(/)workflows/run(/)": "show_workflows_run",
            "(/)workflows(/)list": "show_workflows",
            "(/)workflows/list_published(/)": "show_workflows_published",
            "(/)workflows/create(/)": "show_workflows_create",
            "(/)histories(/)citations(/)": "show_history_citations",
            "(/)histories(/)rename(/)": "show_histories_rename",
            "(/)histories(/)sharing(/)": "show_histories_sharing",
            "(/)histories(/)import(/)": "show_histories_import",
            "(/)histories(/)permissions(/)": "show_histories_permissions",
            "(/)histories/view": "show_history_view",
            "(/)histories/show_structure": "show_history_structure",
            "(/)histories(/)(:action_id)": "show_histories",
            "(/)datasets(/)list(/)": "show_datasets",
            "(/)custom_builds": "show_custom_builds",
            "(/)datasets/edit": "show_dataset_edit_attributes",
            "(/)datasets/error": "show_dataset_error"
        },

        require_login: ["show_user", "show_user_form", "show_workflows"],

        authenticate: function(args, name) {
            let Galaxy = getGalaxyInstance();
            return (Galaxy.user && Galaxy.user.id) || this.require_login.indexOf(name) == -1;
        },

        _display_vue_helper: function(component, props) {
            let instance = Vue.extend(component);
            let vm = document.createElement("div");
            this.page.display(vm);
            new instance(props).$mount(vm);
        },

        show_tours: function(tour_id) {
            if (tour_id) {
                Tours.giveTourById(tour_id);
            } else {
                this.page.display(new Tours.ToursView());
            }
        },

        show_user: function() {
            this.page.display(new UserPreferences.View());
        },

        show_user_form: function(form_id) {
            let Galaxy = getGalaxyInstance();
            var model = new UserPreferences.Model({
                user_id: Galaxy.params.id
            });
            this.page.display(new FormWrapper.View(_.extend(model.get(form_id), { active_tab: "user" })));
        },

        show_visualizations: function(action_id) {
            var activeTab = action_id == "list_published" ? "shared" : "user";
            this.page.display(
                new GridShared.View({
                    action_id: action_id,
                    plural: "Visualizations",
                    item: "visualization",
                    active_tab: activeTab
                })
            );
        },

        show_visualizations_edit: function() {
            this.page.display(
                new FormWrapper.View({
                    url: `visualization/edit?id=${QueryStringParsing.get("id")}`,
                    redirect: "visualizations/list",
                    active_tab: "visualization"
                })
            );
        },

        show_visualizations_sharing: function() {
            var sharingInstance = Vue.extend(Sharing);
            var vm = document.createElement("div");
            this.page.display(vm);
            new sharingInstance({
                propsData: {
                    id: QueryStringParsing.get("id"),
                    plural_name: "Visualizations",
                    model_class: "Visualization"
                }
            }).$mount(vm);
        },

        show_workflows_published: function() {
            var userFilter = QueryStringParsing.get("f-username");
            this.page.display(
                new GridView({
                    url_base: `${getAppRoot()}workflow/list_published`,
                    active_tab: "shared",
                    url_data: {
                        "f-username": userFilter == null ? "" : userFilter
                    }
                })
            );
        },

        show_history_view: function() {
            var historyInstance = Vue.extend(HistoryView);
            var vm = document.createElement("div");
            this.page.display(vm);
            new historyInstance({ propsData: { id: QueryStringParsing.get("id") } }).$mount(vm);
        },

        show_history_structure: function() {
            let displayStructureInstance = Vue.extend(DisplayStructure);
            let vm = document.createElement("div");
            this.page.display(vm);
            new displayStructureInstance({ propsData: { id: QueryStringParsing.get(" id: ") } }).$mount(vm);
        },

        show_histories: function(action_id) {
            this.page.display(new HistoryList.View({ action_id: action_id }));
        },

        show_history_citations: function() {
            var citationInstance = Vue.extend(Citations);
            var vm = document.createElement("div");
            this.page.display(vm);
            new citationInstance({ propsData: { id: QueryStringParsing.get("id"), source: "histories" } }).$mount(vm);
        },

        show_histories_rename: function() {
            this.page.display(
                new FormWrapper.View({
                    url: `history/rename?id=${QueryStringParsing.get("id")}`,
                    redirect: "histories/list"
                })
            );
        },

        show_histories_sharing: function() {
            var sharingInstance = Vue.extend(Sharing);
            var vm = document.createElement("div");
            this.page.display(vm);
            new sharingInstance({
                propsData: {
                    id: QueryStringParsing.get("id"),
                    plural_name: "Histories",
                    model_class: "History"
                }
            }).$mount(vm);
        },

        show_histories_import: function() {
            this._display_vue_helper(HistoryImport);
        },

        show_histories_permissions: function() {
            this.page.display(
                new FormWrapper.View({
                    url: `history/permissions?id=${QueryStringParsing.get("id")}`,
                    redirect: "histories/list"
                })
            );
        },

        show_datasets: function() {
            this.page.display(
                new GridView({
                    url_base: `${getAppRoot()}dataset/list`,
                    active_tab: "user"
                })
            );
        },

        show_pages: function(action_id) {
            var activeTab = action_id == "list_published" ? "shared" : "user";
            this.page.display(
                new GridShared.View({
                    action_id: action_id,
                    plural: "Pages",
                    item: "page",
                    active_tab: activeTab
                })
            );
        },

        show_pages_create: function() {
            this.page.display(
                new FormWrapper.View({
                    url: "page/create",
                    redirect: "pages/list",
                    active_tab: "user"
                })
            );
        },

        show_pages_edit: function() {
            this.page.display(
                new FormWrapper.View({
                    url: `page/edit?id=${QueryStringParsing.get("id")}`,
                    redirect: "pages/list",
                    active_tab: "user"
                })
            );
        },

        show_pages_sharing: function() {
            var sharingInstance = Vue.extend(Sharing);
            var vm = document.createElement("div");
            this.page.display(vm);
            new sharingInstance({
                propsData: {
                    id: QueryStringParsing.get("id"),
                    plural_name: "Pages",
                    model_class: "Page"
                }
            }).$mount(vm);
        },

        show_plugins: function() {
            var pluginListInstance = Vue.extend(PluginList);
            var vm = document.createElement("div");
            this.page.display(vm);
            new pluginListInstance().$mount(vm);
        },

        show_workflows: function() {
            this.page.display(new Workflows.View());
        },

        show_workflows_create: function() {
            this.page.display(
                new FormWrapper.View({
                    url: "workflow/create",
                    redirect: "workflow/editor",
                    active_tab: "workflow"
                })
            );
        },

        show_workflows_run: function() {
            this._loadWorkflow();
        },

        show_workflows_import: function() {
            var workflowImportInstance = Vue.extend(WorkflowImport);
            var vm = document.createElement("div");
            this.page.display(vm);
            new workflowImportInstance().$mount(vm);
        },

        show_custom_builds: function() {
            var historyPanel = this.page.historyPanel.historyView;
            if (!historyPanel || !historyPanel.model || !historyPanel.model.id) {
                window.setTimeout(() => {
                    this.show_custom_builds();
                }, 500);
                return;
            }
            this.page.display(new CustomBuilds.View());
        },

        show_dataset_edit_attributes: function() {
            this.page.display(new DatasetEditAttributes.View());
        },

        show_dataset_error: function() {
            this.page.display(new DatasetError.View());
        },

        /**  */
        home: function(params) {
            // TODO: to router, remove Globals
            // load a tool by id (tool_id) or rerun a previous tool execution (job_id)
            if (params.tool_id || params.job_id) {
                if (params.tool_id === "upload1") {
                    this.page.toolPanel.upload.show();
                    this._loadCenterIframe("welcome");
                } else {
                    this._loadToolForm(params);
                }
            } else {
                // show the workflow run form
                if (params.workflow_id) {
                    this._loadWorkflow();
                    // load the center iframe with controller.action: galaxy.org/?m_c=history&m_a=list -> history/list
                } else if (params.m_c) {
                    this._loadCenterIframe(`${params.m_c}/${params.m_a}`);
                    // show the workflow run form
                } else {
                    this._loadCenterIframe("welcome");
                }
            }
        },

        /** load the center panel with a tool form described by the given params obj */
        _loadToolForm: function(params) {
            //TODO: load tool form code async
            if (params.tool_id) {
                params.id = decodeUriComponent(params.tool_id);
            }
            if (params.version) {
                params.version = decodeUriComponent(params.version);
            }
            this.page.display(new ToolForm.View(params));
        },

        /** load the center panel iframe using the given url */
        _loadCenterIframe: function(url, root) {
            root = root || getAppRoot();
            url = root + url;
            this.page.$("#galaxy_main").prop("src", url);
        },

        /** load workflow by its url in run mode */
        _loadWorkflow: function() {
            Utils.get({
                url: `${getAppRoot()}api/workflows/${Utils.getQueryString("id")}/download?style=run`,
                success: response => {
                    this.page.display(new ToolFormComposite.View(_.extend(response, { active_tab: "workflow" })));
                },
                error: response => {
                    var error_msg = response.err_msg || "Error occurred while loading the resource.";
                    var options = {
                        message: error_msg,
                        status: "danger",
                        persistent: true,
                        active_tab: "workflow"
                    };
                    this.page.display(new Ui.Message(options));
                }
            });
        }
    });
