import _l from "utils/localization";

var AdminPanel = Backbone.View.extend({
    initialize: function(page, options) {
        var self = this;
        this.page = page;
        this.root = options.root;
        this.config = options.config;
        this.settings = options.settings;
        this.message = options.message;
        this.status = options.status;
        this.model = new Backbone.Model({
            title: _l("Administration")
        });
        this.categories = new Backbone.Collection([
            {
                title: "Server",
                items: [
                    {
                        title: "Data types",
                        url: "admin/view_datatypes_registry"
                    },
                    {
                        title: "Data tables",
                        url: "admin/view_tool_data_tables"
                    },
                    {
                        title: "Data libraries",
                        url: "library_admin/browse_libraries"
                    },
                    {
                        title: "Display applications",
                        url: "admin/display_applications"
                    },
                    {
                        title: "Manage jobs",
                        url: "admin/jobs"
                    },
                    {
                        title: "Local data",
                        url: "data_manager"
                    }
                ]
            },
            {
                title: "User Management",
                items: [
                    {
                        title: "Users",
                        url: "admin/users",
                        target: "__use_router__"
                    },
                    {
                        title: "Quotas",
                        url: "admin/quotas",
                        target: "__use_router__",
                        enabled: self.config.enable_quotas
                    },
                    {
                        title: "Groups",
                        url: "admin/groups",
                        target: "__use_router__"
                    },
                    {
                        title: "Roles",
                        url: "admin/roles",
                        target: "__use_router__"
                    },
                    {
                        title: "Forms",
                        url: "admin/forms",
                        target: "__use_router__"
                    },
                    {
                        title: "API keys",
                        url: "userskeys/all_users"
                    },
                    {
                        title: "Impersonate a user",
                        url: "admin/impersonate",
                        enabled: self.config.allow_user_impersonation
                    }
                ]
            },
            {
                title: "Tool Management",
                items: [
                    {
                        title: "Install new tools",
                        url: "admin_toolshed/browse_tool_sheds",
                        enabled: self.settings.is_tool_shed_installed
                    },
                    {
                        title: "Install new tools (Beta)",
                        url: "admin_toolshed/browse_toolsheds",
                        enabled: self.settings.is_tool_shed_installed && self.config.enable_beta_ts_api_install
                    },
                    {
                        title: "Monitor installation",
                        url: "admin_toolshed/monitor_repository_installation",
                        enabled: self.settings.installing_repository_ids
                    },
                    {
                        title: "Manage tools",
                        url: "admin/repositories",
                        enabled: self.settings.is_repo_installed,
                        target: "__use_router__"
                    },
                    {
                        title: "Manage metadata",
                        url: "admin_toolshed/reset_metadata_on_selected_installed_repositories",
                        enabled: self.settings.is_repo_installed
                    },
                    {
                        title: "Manage whitelist",
                        url: "admin/sanitize_whitelist"
                    },
                    {
                        title: "Manage dependencies",
                        url: "admin/manage_tool_dependencies"
                    },
                    {
                        title: "View lineage",
                        url: "admin/tool_versions",
                        target: "__use_router__"
                    },
                    {
                        title: "View migration stages",
                        url: "admin/review_tool_migration_stages"
                    },
                    {
                        title: "View error logs",
                        url: "admin/tool_errors"
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
            var $entries = $section.find(".ui-side-section-body");
            _.each(category.get("items"), item => {
                if (item.enabled === undefined || item.enabled) {
                    var $link = $("<a/>")
                        .attr({ href: self.root + item.url })
                        .text(_l(item.title));
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
                            .addClass("ui-side-section-body-title")
                            .append($link)
                    );
                }
            });
            self.$el.append($section);
        });
        this.page
            .$("#galaxy_main")
            .prop("src", `${this.root}admin/center?message=${this.message}&status=${this.status}`);
    },

    _templateSection: function(options) {
        return [
            "<div>",
            `<div class="ui-side-section-title">${_l(options.title)}</div>`,
            '<div class="ui-side-section-body"/>',
            "</div>"
        ].join("");
    },

    _template: function() {
        return '<div class="ui-side-panel"/>';
    },

    toString: function() {
        return "adminPanel";
    }
});

export default AdminPanel;
