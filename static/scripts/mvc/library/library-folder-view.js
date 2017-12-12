define("mvc/library/library-folder-view", ["exports", "libs/toastr", "mvc/library/library-model", "mvc/ui/ui-select"], function(exports, _toastr, _libraryModel, _uiSelect) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _toastr2 = _interopRequireDefault(_toastr);

    var _libraryModel2 = _interopRequireDefault(_libraryModel);

    var _uiSelect2 = _interopRequireDefault(_uiSelect);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var FolderView = Backbone.View.extend({
        el: "#center",

        model: null,

        options: {},

        events: {
            "click .toolbtn_save_permissions": "savePermissions"
        },

        initialize: function initialize(options) {
            this.options = _.extend(this.options, options);
            if (this.options.id) {
                this.fetchFolder();
            }
        },

        fetchFolder: function fetchFolder(options) {
            this.options = _.extend(this.options, options);
            this.model = new _libraryModel2.default.FolderAsModel({
                id: this.options.id
            });
            var that = this;
            this.model.fetch({
                success: function success() {
                    if (that.options.show_permissions) {
                        that.showPermissions();
                    }
                },
                error: function error(model, response) {
                    if (typeof response.responseJSON !== "undefined") {
                        _toastr2.default.error(response.responseJSON.err_msg + " Click this to go back.", "", {
                            onclick: function onclick() {
                                Galaxy.libraries.library_router.back();
                            }
                        });
                    } else {
                        _toastr2.default.error("An error occurred. Click this to go back.", "", {
                            onclick: function onclick() {
                                Galaxy.libraries.library_router.back();
                            }
                        });
                    }
                }
            });
        },

        showPermissions: function showPermissions(options) {
            this.options = _.extend(this.options, options);
            $(".tooltip").remove();

            var is_admin = false;
            if (Galaxy.user) {
                is_admin = Galaxy.user.isAdmin();
            }
            var template = this.templateFolderPermissions();
            this.$el.html(template({
                folder: this.model,
                is_admin: is_admin
            }));

            var self = this;
            $.get(Galaxy.root + "api/folders/" + self.id + "/permissions?scope=current").done(function(fetched_permissions) {
                self.prepareSelectBoxes({
                    fetched_permissions: fetched_permissions
                });
            }).fail(function() {
                _toastr2.default.error("An error occurred while attempting to fetch folder permissions.");
            });

            $("#center [data-toggle]").tooltip();
            //hack to show scrollbars
            $("#center").css("overflow", "auto");
        },

        _serializeRoles: function _serializeRoles(role_list) {
            var selected_roles = [];
            for (var i = 0; i < role_list.length; i++) {
                selected_roles.push(role_list[i][1] + ":" + role_list[i][0]);
            }
            return selected_roles;
        },

        prepareSelectBoxes: function prepareSelectBoxes(options) {
            this.options = _.extend(this.options, options);
            var fetched_permissions = this.options.fetched_permissions;
            var self = this;

            var selected_add_item_roles = this._serializeRoles(fetched_permissions.add_library_item_role_list);
            var selected_manage_folder_roles = this._serializeRoles(fetched_permissions.manage_folder_role_list);
            var selected_modify_folder_roles = this._serializeRoles(fetched_permissions.modify_folder_role_list);

            self.addSelectObject = new _uiSelect2.default.View(this._createSelectOptions(this, "add_perm", selected_add_item_roles, false));
            self.manageSelectObject = new _uiSelect2.default.View(this._createSelectOptions(this, "manage_perm", selected_manage_folder_roles, false));
            self.modifySelectObject = new _uiSelect2.default.View(this._createSelectOptions(this, "modify_perm", selected_modify_folder_roles, false));
        },

        _createSelectOptions: function _createSelectOptions(self, id, init_data) {
            var select_options = {
                minimumInputLength: 0,
                css: id,
                multiple: true,
                placeholder: "Click to select a role",
                container: self.$el.find("#" + id),
                ajax: {
                    url: Galaxy.root + "api/folders/" + self.id + "/permissions?scope=available",
                    dataType: "json",
                    quietMillis: 100,
                    data: function data(term, page) {
                        // page is the one-based page number tracked by Select2
                        return {
                            q: term, //search term
                            page_limit: 10, // page size
                            page: page // page number
                        };
                    },
                    results: function results(data, page) {
                        var more = page * 10 < data.total; // whether or not there are more results available
                        // notice we return the value of more so Select2 knows if more results can be loaded
                        return {
                            results: data.roles,
                            more: more
                        };
                    }
                },
                formatResult: function roleFormatResult(role) {
                    return role.name + " type: " + role.type;
                },

                formatSelection: function roleFormatSelection(role) {
                    return role.name;
                },
                initSelection: function initSelection(element, callback) {
                    // the input tag has a value attribute preloaded that points to a preselected role's id
                    // this function resolves that id attribute to an object that select2 can render
                    // using its formatResult renderer - that way the role name is shown preselected
                    var data = [];
                    $(element.val().split(",")).each(function() {
                        var item = this.split(":");
                        data.push({
                            id: item[0],
                            name: item[1]
                        });
                    });
                    callback(data);
                },
                initialData: init_data.join(","),
                dropdownCssClass: "bigdrop" // apply css that makes the dropdown taller
            };

            return select_options;
        },

        /**
         * Extract the role ids from Select2 elements's 'data'
         */
        _extractIds: function _extractIds(roles_list) {
            var ids_list = [];
            for (var i = roles_list.length - 1; i >= 0; i--) {
                ids_list.push(roles_list[i].id);
            }
            return ids_list;
        },

        /**
         * Save the permissions for roles entered in the select boxes.
         */
        savePermissions: function savePermissions(event) {
            var self = this;
            var add_ids = this._extractIds(this.addSelectObject.$el.select2("data"));
            var manage_ids = this._extractIds(this.manageSelectObject.$el.select2("data"));
            var modify_ids = this._extractIds(this.modifySelectObject.$el.select2("data"));
            $.post(Galaxy.root + "api/folders/" + self.id + "/permissions?action=set_permissions", {
                "add_ids[]": add_ids,
                "manage_ids[]": manage_ids,
                "modify_ids[]": modify_ids
            }).done(function(fetched_permissions) {
                self.showPermissions({
                    fetched_permissions: fetched_permissions
                });
                _toastr2.default.success("Permissions saved.");
            }).fail(function() {
                _toastr2.default.error("An error occurred while attempting to set folder permissions.");
            });
        },

        templateFolderPermissions: function templateFolderPermissions() {
            return _.template(['<div class="library_style_container">', '<div id="library_toolbar">', '<a href="#/folders/<%= folder.get("parent_id") %>">', '<button data-toggle="tooltip" data-placement="top" title="Go back to the parent folder" class="btn btn-default primary-button" type="button">', '<span class="fa fa-caret-left fa-lg"/>', "&nbsp;Parent folder", "</button>", "</a>", "</div>", "<h1>", 'Folder: <%= _.escape(folder.get("name")) %>', "</h1>", '<div class="alert alert-warning">', "<% if (is_admin) { %>", "You are logged in as an <strong>administrator</strong> therefore you can manage any folder on this Galaxy instance. Please make sure you understand the consequences.", "<% } else { %>", "You can assign any number of roles to any of the following permission types. However please read carefully the implications of such actions.", "<% }%>", "</div>", '<div class="dataset_table">', "<h2>Folder permissions</h2>", "<h4>", "Roles that can manage permissions on this folder", "</h4>", '<div id="manage_perm" class="manage_perm roles-selection"/>', '<div class="alert alert-info roles-selection">', "User with <strong>any</strong> of these roles can manage permissions on this folder.", "</div>", "<h4>", "Roles that can add items to this folder", "</h4>", '<div id="add_perm" class="add_perm roles-selection"/>', '<div class="alert alert-info roles-selection">', "User with <strong>any</strong> of these roles can add items to this folder (folders and datasets).", "</div>", "<h4>", "Roles that can modify this folder", "</h4>", '<div id="modify_perm" class="modify_perm roles-selection"/>', '<div class="alert alert-info roles-selection">', "User with <strong>any</strong> of these roles can modify this folder (name, etc.).", "</div>", '<button data-toggle="tooltip" data-placement="top" title="Save modifications" class="btn btn-default toolbtn_save_permissions primary-button" type="button">', '<span class="fa fa-floppy-o"/>', "&nbsp;Save", "</button>", "</div>", "</div>"].join(""));
        }
    });

    exports.default = {
        FolderView: FolderView
    };
});
//# sourceMappingURL=../../../maps/mvc/library/library-folder-view.js.map
