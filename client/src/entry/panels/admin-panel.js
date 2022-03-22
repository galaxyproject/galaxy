import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import _l from "utils/localization";
import { getGalaxyInstance } from "app";

const AdminPanel = Backbone.View.extend({
    initialize: function (page, options) {
        this.page = page;
        this.root = options.root;
        this.config = options.config;
        this.settings = options.settings;
        this.model = new Backbone.Model({
            title: `Galaxy version ${getGalaxyInstance().config.version_major}`,
        });
        this.categories = new Backbone.Collection([
            {
                title: _l("Server"),
                items: [
                    {
                        title: _l("Data Types"),
                        url: "admin/data_types",
                        target: "__use_router__",
                        id: "admin-link-datatypes",
                    },
                    {
                        title: _l("Data Tables"),
                        url: "admin/data_tables",
                        target: "__use_router__",
                        id: "admin-link-data-tables",
                    },
                    {
                        title: _l("Display Applications"),
                        url: "admin/display_applications",
                        target: "__use_router__",
                        id: "admin-link-display-applications",
                    },
                    {
                        title: _l("Jobs"),
                        url: "admin/jobs",
                        target: "__use_router__",
                        id: "admin-link-jobs",
                    },
                    {
                        title: _l("Workflow Invocations"),
                        url: "admin/invocations",
                        target: "__use_router__",
                        id: "admin-link-invocations",
                    },
                    {
                        title: _l("Local Data"),
                        url: "admin/data_manager",
                        target: "__use_router__",
                        id: "admin-link-local-data",
                    },
                ],
            },
            {
                title: _l("User Management"),
                items: [
                    {
                        title: _l("Users"),
                        url: "admin/users",
                        target: "__use_router__",
                        id: "admin-link-users",
                    },
                    {
                        title: _l("Quotas"),
                        url: "admin/quotas",
                        target: "__use_router__",
                        enabled: this.config.enable_quotas,
                        id: "admin-link-quotas",
                    },
                    {
                        title: _l("Groups"),
                        url: "admin/groups",
                        target: "__use_router__",
                        id: "admin-link-groups",
                    },
                    {
                        title: _l("Roles"),
                        url: "admin/roles",
                        target: "__use_router__",
                        id: "admin-link-roles",
                    },
                    {
                        title: _l("Forms"),
                        url: "admin/forms",
                        target: "__use_router__",
                        id: "admin-link-forms",
                    },
                ],
            },
            {
                title: _l("Tool Management"),
                items: [
                    {
                        title: _l("Install and Uninstall"),
                        url: "admin/toolshed",
                        target: "__use_router__",
                        id: "admin-link-toolshed",
                        enabled: this.settings.is_tool_shed_installed,
                    },
                    {
                        title: _l("Manage Metadata"),
                        url: "admin/reset_metadata",
                        id: "admin-link-metadata",
                        enabled: this.settings.is_repo_installed,
                        target: "__use_router__",
                    },
                    {
                        title: _l("Manage Allowlist"),
                        url: "admin/sanitize_allow",
                        id: "admin-link-allowlist",
                        target: "__use_router__",
                    },
                    {
                        title: _l("Manage Dependencies"),
                        url: "admin/toolbox_dependencies",
                        target: "__use_router__",
                        id: "admin-link-manage-dependencies",
                    },
                    {
                        title: _l("Manage Dependencies (legacy)"),
                        url: "admin/manage_tool_dependencies",
                    },
                    {
                        title: _l("View Lineage"),
                        url: "admin/tool_versions",
                        target: "__use_router__",
                        id: "admin-link-tool-versions",
                    },
                    {
                        title: _l("View Error Logs"),
                        url: "admin/error_stack",
                        id: "admin-link-error-stack",
                        target: "__use_router__",
                    },
                ],
            },
        ]);
        this.setElement(this._template());
    },

    render: function () {
        this.$el.empty();
        this.categories.each((category) => {
            const $section = $(this._templateSection(category.attributes));
            const $entries = $section.find(".toolSectionBody");
            _.each(category.get("items"), (item) => {
                if (item.enabled === undefined || item.enabled) {
                    const $link = $("<a/>")
                        .addClass("title-link")
                        .attr({ href: this.root + item.url })
                        .text(_l(item.title));
                    if (item.id) {
                        $link.attr("id", item.id);
                    }
                    if (item.target == "__use_router__") {
                        $link.on("click", (e) => {
                            e.preventDefault();
                            this.page.router.push(item.url);
                        });
                    } else {
                        $link.attr("target", "galaxy_main");
                    }
                    $entries.append($("<div/>").addClass("toolTitle").append($link));
                }
            });
            this.$el.append($section);
        });
    },

    _templateSection: function (options) {
        return `<div class="toolSectionWrapper">
                    <div class="toolSectionTitle pt-1 px-3">${_l(options.title)}</div>
                    <div class="toolSectionBody"/>
                </div>`;
    },

    _template: function () {
        return '<div class="toolMenuContainer"/>';
    },

    toString: function () {
        return "adminPanel";
    },
});

export default AdminPanel;
