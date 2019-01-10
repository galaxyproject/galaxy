import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import _l from "utils/localization";
import { getGalaxyInstance } from "app";

var AdminPanel = Backbone.View.extend({
    initialize: function(page, options) {
        var self = this;
        this.page = page;
        this.root = options.root;
        this.config = options.config;
        this.settings = options.settings;
        this.model = new Backbone.Model({
            title: `Galaxy version ${getGalaxyInstance().config.version_major}`
        });
        this.categories = new Backbone.Collection([
            {
                title: _l("Server"),
                items: [
                    {
                        title: _l("Data types"),
                        url: "admin/data_types",
                        target: "__use_router__",
                        id: "admin-link-datatypes"
                    },
                    {
                        title: _l("Data tables"),
                        url: "admin/data_tables",
                        target: "__use_router__",
                        id: "admin-link-data-tables"
                    },
                    {
                        title: _l("Display applications"),
                        url: "admin/display_applications",
                        target: "__use_router__",
                        id: "admin-link-display-applications"
                    },
                    {
                        title: _l("Manage jobs"),
                        url: "admin/jobs",
                        id: "admin-link-jobs"
                    },
                    {
                        title: _l("Local data"),
                        url: "admin/data_manager",
                        target: "__use_router__",
                        id: "admin-link-local-data"
                    }
                ]
            },
            {
                title: _l("User Management"),
                items: [
                    {
                        title: _l("Users"),
                        url: "admin/users",
                        target: "__use_router__",
                        id: "admin-link-users"
                    },
                    {
                        title: _l("Quotas"),
                        url: "admin/quotas",
                        target: "__use_router__",
                        enabled: self.config.enable_quotas,
                        id: "admin-link-quotas"
                    },
                    {
                        title: _l("Groups"),
                        url: "admin/groups",
                        target: "__use_router__",
                        id: "admin-link-groups"
                    },
                    {
                        title: _l("Roles"),
                        url: "admin/roles",
                        target: "__use_router__",
                        id: "admin-link-roles"
                    },
                    {
                        title: _l("Forms"),
                        url: "admin/forms",
                        target: "__use_router__"
                    }
                ]
            },
            {
                title: _l("Tool Management"),
                items: [
                    {
                        title: _l("Install new tools"),
                        url: "admin_toolshed/browse_tool_sheds",
                        enabled: self.settings.is_tool_shed_installed
                    },
                    {
                        title: "Install new tools (Beta)",
                        url: "admin_toolshed/browse_toolsheds",
                        enabled: self.settings.is_tool_shed_installed && self.config.enable_beta_ts_api_install
                    },
                    {
                        title: _l("Monitor installation"),
                        url: "admin_toolshed/monitor_repository_installation",
                        enabled: self.settings.installing_repository_ids
                    },
                    {
                        title: _l("Manage tools"),
                        url: "admin/repositories",
                        enabled: self.settings.is_repo_installed,
                        target: "__use_router__"
                    },
                    {
                        title: _l("Manage metadata"),
                        url: "admin_toolshed/reset_metadata_on_selected_installed_repositories",
                        enabled: self.settings.is_repo_installed
                    },
                    {
                        title: _l("Manage whitelist"),
                        url: "admin/sanitize_whitelist"
                    },
                    {
                        title: _l("Manage dependencies"),
                        url: "admin/manage_tool_dependencies"
                    },
                    {
                        title: _l("View lineage"),
                        url: "admin/tool_versions",
                        target: "__use_router__"
                    },
                    {
                        title: _l("View migration stages"),
                        url: "admin/review_tool_migration_stages"
                    },
                    {
                        title: _l("View error logs"),
                        url: "admin/error_stack",
                        target: "__use_router__"
                    }
                ]
            }
        ]);
        this.setElement(this._template());
    },

    render: function() {
        var self = this;
        this.$el.empty();
        this.categories.each(category => {
            var $section = $(self._templateSection(category.attributes));
            var $entries = $section.find(".toolSectionBody");
            _.each(category.get("items"), item => {
                if (item.enabled === undefined || item.enabled) {
                    var $link = $("<a/>")
                        .attr({ href: self.root + item.url })
                        .text(_l(item.title));
                    if (item.id) {
                        $link.attr("id", item.id);
                    }
                    if (item.target == "__use_router__") {
                        $link.on("click", e => {
                            e.preventDefault();
                            self.page.router.push(item.url);
                        });
                    } else {
                        $link.attr("target", "galaxy_main");
                    }
                    $entries.append(
                        $("<div/>")
                            .addClass("toolTitle")
                            .append($link)
                    );
                }
            });
            self.$el.append($section);
        });
    },

    _templateSection: function(options) {
        return `<div class="toolSectionWrapper">
                    <div class="toolSectionTitle">${_l(options.title)}</div>
                    <div class="toolSectionBody"/>
                </div>`;
    },

    _template: function() {
        return '<div class="toolMenuContainer"/>';
    },

    toString: function() {
        return "adminPanel";
    }
});

export default AdminPanel;
