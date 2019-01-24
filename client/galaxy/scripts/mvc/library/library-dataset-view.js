import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import mod_toastr from "libs/toastr";
import mod_library_model from "mvc/library/library-model";
import mod_utils from "utils/utils";
import mod_select from "mvc/ui/ui-select";

var LibraryDatasetView = Backbone.View.extend({
    el: "#center",

    model: null,

    options: {},

    defaults: {
        edit_mode: false
    },

    events: {
        "click .toolbtn_modify_dataset": "enableModification",
        "click .toolbtn_cancel_modifications": "render",
        "click .toolbtn-download-dataset": "downloadDataset",
        "click .toolbtn-import-dataset": "importIntoHistory",
        "click .copy-link-to-clipboard": "copyToClipboard",
        "click .make-private": "makeDatasetPrivate",
        "click .remove-restrictions": "removeDatasetRestrictions",
        "click .toolbtn_save_permissions": "savePermissions",
        "click .toolbtn_save_modifications": "saveModifications"
    },

    // genome select
    select_genome: null,

    // extension select
    select_extension: null,

    // extension types
    list_extensions: [],

    // datatype placeholder for extension auto-detection
    auto: {
        id: "auto",
        text: "Auto-detect",
        description:
            "This system will try to detect the file type automatically." +
            " If your file is not detected properly as one of the known formats," +
            " it most likely means that it has some format problems (e.g., different" +
            " number of columns on different rows). You can still coerce the system" +
            " to set your data to the format you think it should be." +
            " You can also upload compressed files, which will automatically be decompressed."
    },

    // genomes
    list_genomes: [],

    initialize: function(options) {
        this.options = _.extend(this.options, options);
        this.fetchExtAndGenomes();
        if (this.options.id) {
            this.fetchDataset();
        }
    },

    fetchDataset: function(options) {
        let Galaxy = getGalaxyInstance();
        this.options = _.extend(this.options, options);
        this.model = new mod_library_model.Item({
            id: this.options.id
        });
        var self = this;
        this.model.fetch({
            success: function() {
                if (self.options.show_permissions) {
                    self.showPermissions();
                } else if (self.options.show_version) {
                    self.fetchVersion();
                } else {
                    self.render();
                }
            },
            error: function(model, response) {
                if (typeof response.responseJSON !== "undefined") {
                    mod_toastr.error(`${response.responseJSON.err_msg} Click this to go back.`, "", {
                        onclick: function() {
                            Galaxy.libraries.library_router.back();
                        }
                    });
                } else {
                    mod_toastr.error("An error occurred. Click this to go back.", "", {
                        onclick: function() {
                            Galaxy.libraries.library_router.back();
                        }
                    });
                }
            }
        });
    },

    render: function(options) {
        this.options = _.extend(this.options, options);
        $(".tooltip").remove();
        var template = this.templateDataset();
        this.$el.html(template({ item: this.model }));
        $(".peek").html(this.model.get("peek"));
        $('#center [data-toggle="tooltip"]').tooltip({ trigger: "hover" });
    },

    fetchVersion: function(options) {
        this.options = _.extend(this.options, options);
        var self = this;
        if (!this.options.ldda_id) {
            this.render();
            mod_toastr.error("Library dataset version requested but no id provided.");
        } else {
            this.ldda = new mod_library_model.Ldda({
                id: this.options.ldda_id
            });
            this.ldda.url = `${this.ldda.urlRoot + this.model.id}/versions/${this.ldda.id}`;
            this.ldda.fetch({
                success: function() {
                    self.renderVersion();
                },
                error: function(model, response) {
                    if (typeof response.responseJSON !== "undefined") {
                        mod_toastr.error(response.responseJSON.err_msg);
                    } else {
                        mod_toastr.error("An error occurred.");
                    }
                }
            });
        }
    },

    renderVersion: function() {
        $(".tooltip").remove();
        var template = this.templateVersion();
        this.$el.html(template({ item: this.model, ldda: this.ldda }));
        $(".peek").html(this.ldda.get("peek"));
    },

    enableModification: function() {
        $(".tooltip").remove();
        var template = this.templateModifyDataset();
        this.$el.html(template({ item: this.model }));
        this.renderSelectBoxes({
            genome_build: this.model.get("genome_build"),
            file_ext: this.model.get("file_ext")
        });
        $(".peek").html(this.model.get("peek"));
        $('#center [data-toggle="tooltip"]').tooltip({ trigger: "hover" });
    },

    downloadDataset: function() {
        var url = `${getAppRoot()}api/libraries/datasets/download/uncompressed`;
        var data = { ld_ids: this.id };
        this.processDownload(url, data);
    },

    processDownload: function(url, data, method) {
        //url and data options required
        if (url && data) {
            //data can be string of parameters or array/object
            data = typeof data == "string" ? data : $.param(data);
            //split params into form inputs
            var inputs = "";
            $.each(data.split("&"), function() {
                var pair = this.split("=");
                inputs += `<input type="hidden" name="${pair[0]}" value="${pair[1]}" />`;
            });
            //send request
            $(`<form action="${url}" method="${method || "post"}">${inputs}</form>`)
                .appendTo("body")
                .submit()
                .remove();

            mod_toastr.info("Your download will begin soon.");
        }
    },

    importIntoHistory: function() {
        this.refreshUserHistoriesList(self => {
            let Galaxy = getGalaxyInstance();
            var template = self.templateBulkImportInModal();
            self.modal = Galaxy.modal;
            self.modal.show({
                closing_events: true,
                title: _l("Import into History"),
                body: template({ histories: self.histories.models }),
                buttons: {
                    Import: function() {
                        self.importCurrentIntoHistory();
                    },
                    Close: function() {
                        Galaxy.modal.hide();
                    }
                }
            });
        });
    },

    refreshUserHistoriesList: function(callback) {
        var self = this;
        this.histories = new mod_library_model.GalaxyHistories();
        this.histories.fetch({
            success: function(histories) {
                if (histories.length === 0) {
                    mod_toastr.warning("You have to create history first. Click this to do so.", "", {
                        onclick: function() {
                            window.location = getAppRoot();
                        }
                    });
                } else {
                    callback(self);
                }
            },
            error: function(model, response) {
                if (typeof response.responseJSON !== "undefined") {
                    mod_toastr.error(response.responseJSON.err_msg);
                } else {
                    mod_toastr.error("An error occurred.");
                }
            }
        });
    },

    importCurrentIntoHistory: function() {
        this.modal.disableButton("Import");
        var new_history_name = this.modal.$("input[name=history_name]").val();
        var self = this;
        if (new_history_name !== "") {
            $.post(`${getAppRoot()}api/histories`, {
                name: new_history_name
            })
                .done(new_history => {
                    self.processImportToHistory(new_history.id);
                })
                .fail((xhr, status, error) => {
                    mod_toastr.error("An error occurred.");
                })
                .always(() => {
                    self.modal.enableButton("Import");
                });
        } else {
            var history_id = $(this.modal.$el)
                .find("select[name=dataset_import_single] option:selected")
                .val();
            this.processImportToHistory(history_id);
            this.modal.enableButton("Import");
        }
    },

    processImportToHistory: function(history_id) {
        let Galaxy = getGalaxyInstance();
        var historyItem = new mod_library_model.HistoryItem();
        historyItem.url = `${historyItem.urlRoot + history_id}/contents`;
        // set the used history as current so user will see the last one
        // that he imported into in the history panel on the 'analysis' page
        $.getJSON(`${getAppRoot()}history/set_as_current?id=${history_id}`);
        // save the dataset into selected history
        historyItem.save(
            { content: this.id, source: "library" },
            {
                success: function() {
                    Galaxy.modal.hide();
                    mod_toastr.success("Dataset imported. Click this to start analyzing it.", "", {
                        onclick: function() {
                            window.location = getAppRoot();
                        }
                    });
                },
                error: function(model, response) {
                    if (typeof response.responseJSON !== "undefined") {
                        mod_toastr.error(`Dataset not imported. ${response.responseJSON.err_msg}`);
                    } else {
                        mod_toastr.error("An error occurred. Dataset not imported. Please try again.");
                    }
                }
            }
        );
    },

    showPermissions: function(options) {
        let Galaxy = getGalaxyInstance();
        var template = this.templateDatasetPermissions();
        var self = this;
        this.options = _.extend(this.options, options);
        $(".tooltip").remove();
        if (this.options.fetched_permissions !== undefined) {
            if (this.options.fetched_permissions.access_dataset_roles.length === 0) {
                this.model.set({ is_unrestricted: true });
            } else {
                this.model.set({ is_unrestricted: false });
            }
        }
        this.$el.html(
            template({
                item: this.model,
                is_admin: Galaxy.config.is_admin_user
            })
        );
        $.get(`${getAppRoot()}api/libraries/datasets/${self.id}/permissions?scope=current`)
            .done(fetched_permissions => {
                self.prepareSelectBoxes({
                    fetched_permissions: fetched_permissions,
                    is_admin: Galaxy.config.is_admin_user
                });
            })
            .fail(() => {
                mod_toastr.error("An error occurred while attempting to fetch dataset permissions.");
            });
        $('#center [data-toggle="tooltip"]').tooltip({ trigger: "hover" });
        $("#center").css("overflow", "auto");
    },

    _serializeRoles: function(role_list) {
        var selected_roles = [];
        for (var i = 0; i < role_list.length; i++) {
            // Replace the : and , in role's name since these are select2 separators for initialData
            selected_roles.push(`${role_list[i][1]}:${role_list[i][0].replace(":", " ").replace(",", " &")}`);
        }
        return selected_roles;
    },

    prepareSelectBoxes: function(options) {
        this.options = _.extend(this.options, options);
        this.accessSelectObject = new mod_select.View(
            this._generate_select_options({
                selector: "access_perm",
                initialData: this._serializeRoles(this.options.fetched_permissions.access_dataset_roles)
            })
        );
        this.modifySelectObject = new mod_select.View(
            this._generate_select_options({
                selector: "modify_perm",
                initialData: this._serializeRoles(this.options.fetched_permissions.modify_item_roles)
            })
        );
        this.manageSelectObject = new mod_select.View(
            this._generate_select_options({
                selector: "manage_perm",
                initialData: this._serializeRoles(this.options.fetched_permissions.manage_dataset_roles)
            })
        );
    },

    _generate_select_options: function(options) {
        var select_options = {
            minimumInputLength: 0,
            multiple: true,
            placeholder: "Click to select a role",
            formatResult: function roleFormatResult(role) {
                return `${role.name} type: ${role.type}`;
            },
            formatSelection: function roleFormatSelection(role) {
                return role.name;
            },
            initSelection: function(element, callback) {
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
            dropdownCssClass: "bigdrop" // apply css that makes the dropdown taller
        };
        select_options.container = this.$el.find(`#${options.selector}`);
        select_options.css = options.selector;
        select_options.initialData = options.initialData.join(",");
        select_options.ajax = {
            url: `${getAppRoot()}api/libraries/datasets/${this.id}/permissions?scope=available`,
            dataType: "json",
            quietMillis: 100,
            data: function(term, page) {
                // page is the one-based page number tracked by Select2
                return {
                    q: term, //search term
                    page_limit: 10, // page size, should be same as used in 'more' variable below
                    page: page // page number
                };
            },
            results: function(data, page) {
                var more = page * 10 < data.total; // whether or not there are more results available
                // notice we return the value of more so Select2 knows if more results can be loaded
                return { results: data.roles, more: more };
            }
        };
        return select_options;
    },

    /**
     * Save the changes made to the library dataset.
     */
    saveModifications: function(options) {
        var is_changed = false;
        var ld = this.model;
        var new_name = this.$el.find(".input_dataset_name").val();
        if (typeof new_name !== "undefined" && new_name !== ld.get("name")) {
            if (new_name.length > 0) {
                ld.set("name", new_name);
                is_changed = true;
            } else {
                mod_toastr.warning("Library dataset name has to be at least 1 character long.");
                return;
            }
        }
        var new_info = this.$el.find(".input_dataset_misc_info").val();
        if (typeof new_info !== "undefined" && new_info !== ld.get("misc_info")) {
            ld.set("misc_info", new_info);
            is_changed = true;
        }
        var new_message = this.$el.find(".input_dataset_message").val();
        if (typeof new_message !== "undefined" && new_message !== ld.get("message")) {
            ld.set("message", new_message);
            is_changed = true;
        }
        var new_genome_build = this.select_genome.$el.select2("data").id;
        if (typeof new_genome_build !== "undefined" && new_genome_build !== ld.get("genome_build")) {
            ld.set("genome_build", new_genome_build);
            is_changed = true;
        }
        var new_ext = this.select_extension.$el.select2("data").id;
        if (typeof new_ext !== "undefined" && new_ext !== ld.get("file_ext")) {
            ld.set("file_ext", new_ext);
            is_changed = true;
        }
        var dataset_view = this;
        if (is_changed) {
            ld.save(null, {
                patch: true,
                success: function(ld) {
                    dataset_view.render();
                    mod_toastr.success("Changes to library dataset saved.");
                },
                error: function(model, response) {
                    if (typeof response.responseJSON !== "undefined") {
                        mod_toastr.error(response.responseJSON.err_msg);
                    } else {
                        mod_toastr.error("An error occurred while attempting to update the library dataset.");
                    }
                }
            });
        } else {
            dataset_view.render();
            mod_toastr.info("Nothing has changed.");
        }
    },

    copyToClipboard: function(e) {
        e.preventDefault();
        var href = Backbone.history.location.href;
        if (href.lastIndexOf("/permissions") !== -1) {
            href = href.substr(0, href.lastIndexOf("/permissions"));
        }
        window.prompt("Copy to clipboard: Ctrl+C, Enter", href);
    },

    makeDatasetPrivate: function() {
        var self = this;
        $.post(`${getAppRoot()}api/libraries/datasets/${self.id}/permissions?action=make_private`)
            .done(fetched_permissions => {
                self.model.set({ is_unrestricted: false });
                self.showPermissions({
                    fetched_permissions: fetched_permissions
                });
                mod_toastr.success("The dataset is now private to you.");
            })
            .fail(() => {
                mod_toastr.error("An error occurred while attempting to make dataset private.");
            });
    },

    removeDatasetRestrictions: function() {
        var self = this;
        $.post(`${getAppRoot()}api/libraries/datasets/${self.id}/permissions?action=remove_restrictions`)
            .done(fetched_permissions => {
                self.model.set({ is_unrestricted: true });
                self.showPermissions({
                    fetched_permissions: fetched_permissions
                });
                mod_toastr.success("Access to this dataset is now unrestricted.");
            })
            .fail(() => {
                mod_toastr.error("An error occurred while attempting to make dataset unrestricted.");
            });
    },

    /**
     * Extract the role ids from Select2 elements's 'data'
     */
    _extractIds: function(roles_list) {
        var ids_list = [];
        for (var i = roles_list.length - 1; i >= 0; i--) {
            ids_list.push(roles_list[i].id);
        }
        return ids_list;
    },

    /**
     * Save the permissions for roles entered in the select boxes.
     */
    savePermissions: function(event) {
        var self = this;
        var access_ids = this._extractIds(this.accessSelectObject.$el.select2("data"));
        var manage_ids = this._extractIds(this.manageSelectObject.$el.select2("data"));
        var modify_ids = this._extractIds(this.modifySelectObject.$el.select2("data"));
        $.post(`${getAppRoot()}api/libraries/datasets/${self.id}/permissions?action=set_permissions`, {
            "access_ids[]": access_ids,
            "manage_ids[]": manage_ids,
            "modify_ids[]": modify_ids
        })
            .done(fetched_permissions => {
                self.showPermissions({
                    fetched_permissions: fetched_permissions
                });
                mod_toastr.success("Permissions saved.");
            })
            .fail(() => {
                mod_toastr.error("An error occurred while attempting to set dataset permissions.");
            });
    },

    /**
     * If needed request all extensions and/or genomes from Galaxy
     * and save them in sorted arrays.
     */
    fetchExtAndGenomes: function() {
        var self = this;
        if (this.list_genomes.length == 0) {
            mod_utils.get({
                url: `${getAppRoot()}api/datatypes?extension_only=False`,
                success: function(datatypes) {
                    for (var key in datatypes) {
                        self.list_extensions.push({
                            id: datatypes[key].extension,
                            text: datatypes[key].extension,
                            description: datatypes[key].description,
                            description_url: datatypes[key].description_url
                        });
                    }
                    self.list_extensions.sort((a, b) => (a.id > b.id ? 1 : a.id < b.id ? -1 : 0));
                    self.list_extensions.unshift(self.auto);
                }
            });
        }
        if (this.list_extensions.length == 0) {
            mod_utils.get({
                url: `${getAppRoot()}api/genomes`,
                success: function(genomes) {
                    for (var key in genomes) {
                        self.list_genomes.push({
                            id: genomes[key][1],
                            text: genomes[key][0]
                        });
                    }
                    self.list_genomes.sort((a, b) => (a.id > b.id ? 1 : a.id < b.id ? -1 : 0));
                }
            });
        }
    },

    renderSelectBoxes: function(options) {
        // This won't work properly unlesss we already have the data fetched.
        // See this.fetchExtAndGenomes()
        // TODO switch to common resources:
        // https://trello.com/c/dIUE9YPl/1933-ui-common-resources-and-data-into-galaxy-object
        var self = this;
        var current_genome = "?";
        var current_ext = "auto";
        if (typeof options !== "undefined") {
            if (typeof options.genome_build !== "undefined") {
                current_genome = options.genome_build;
            }
            if (typeof options.file_ext !== "undefined") {
                current_ext = options.file_ext;
            }
        }
        this.select_genome = new mod_select.View({
            css: "dataset-genome-select",
            data: self.list_genomes,
            container: self.$el.find("#dataset_genome_select"),
            value: current_genome
        });
        this.select_extension = new mod_select.View({
            css: "dataset-extension-select",
            data: self.list_extensions,
            container: self.$el.find("#dataset_extension_select"),
            value: current_ext
        });
    },

    templateDataset: function() {
        return _.template(
            [
                // CONTAINER START
                '<div class="library_style_container">',
                '<div class="d-flex mb-2">',
                '<button data-toggle="tooltip" data-placement="top" title="Download dataset" class="btn btn-secondary toolbtn-download-dataset toolbar-item mr-1" type="button">',
                '<span class="fa fa-download"></span>',
                "&nbsp;Download",
                "</button>",
                '<button data-toggle="tooltip" data-placement="top" title="Import dataset into history" class="btn btn-secondary toolbtn-import-dataset toolbar-item mr-1" type="button">',
                '<span class="fa fa-book"></span>',
                "&nbsp;to History",
                "</button>",
                '<% if (item.get("can_user_modify")) { %>',
                '<button data-toggle="tooltip" data-placement="top" title="Modify library item" class="btn btn-secondary toolbtn_modify_dataset toolbar-item mr-1" type="button">',
                '<span class="fa fa-pencil"></span>',
                "&nbsp;Modify",
                "</button>",
                "<% } %>",
                '<% if (item.get("can_user_manage")) { %>',
                '<a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>/permissions">',
                '<button data-toggle="tooltip" data-placement="top" title="Manage permissions" class="btn btn-secondary toolbtn_change_permissions toolbar-item mr-1" type="button">',
                '<span class="fa fa-group"></span>',
                "&nbsp;Permissions",
                "</button>",
                "</a>",
                "<% } %>",
                "</div>",

                // BREADCRUMBS
                '<ol class="breadcrumb">',
                '<li class="breadcrumb-item"><a title="Return to the list of libraries" href="#">Libraries</a></li>',
                '<% _.each(item.get("full_path"), function(path_item) { %>',
                "<% if (path_item[0] != item.id) { %>",
                '<li class="breadcrumb-item"><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',
                "<% } else { %>",
                '<li class="breadcrumb-item active"><span title="You are here"><%- path_item[1] %></span></li>',
                "<% } %>",
                "<% }); %>",
                "</ol>",

                '<% if (item.get("is_unrestricted")) { %>',
                "<div>",
                'This dataset is unrestricted so everybody with the link can access it. Just share <span class="copy-link-to-clipboard"><a href=""a>this page</a></span>.',
                "</div>",
                "<% } %>",

                // TABLE START
                '<div class="dataset_table">',
                '<table class="grid table table-striped table-sm">',
                "<tr>",
                '<th class="dataset-first-column" scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>',
                '<td><%= _.escape(item.get("name")) %></td>',
                "</tr>",
                '<% if (item.get("file_ext")) { %>',
                "<tr>",
                '<th scope="row">Data type</th>',
                '<td><%= _.escape(item.get("file_ext")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("genome_build")) { %>',
                "<tr>",
                '<th scope="row">Genome build</th>',
                '<td><%= _.escape(item.get("genome_build")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("file_size")) { %>',
                "<tr>",
                '<th scope="row">Size</th>',
                '<td><%= _.escape(item.get("file_size")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("date_uploaded")) { %>',
                "<tr>",
                '<th scope="row">Date uploaded (UTC)</th>',
                '<td><%= _.escape(item.get("date_uploaded")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("uploaded_by")) { %>',
                "<tr>",
                '<th scope="row">Uploaded by</th>',
                '<td><%= _.escape(item.get("uploaded_by")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("metadata_data_lines")) { %>',
                "<tr>",
                '<th scope="row">Data Lines</th>',
                '<td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("metadata_comment_lines")) { %>',
                "<tr>",
                '<th scope="row">Comment Lines</th>',
                '<td scope="row"><%= _.escape(item.get("metadata_comment_lines")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("metadata_columns")) { %>',
                "<tr>",
                '<th scope="row">Number of Columns</th>',
                '<td scope="row"><%= _.escape(item.get("metadata_columns")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("metadata_column_types")) { %>',
                "<tr>",
                '<th scope="row">Column Types</th>',
                '<td scope="row"><%= _.escape(item.get("metadata_column_types")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("message")) { %>',
                "<tr>",
                '<th scope="row">Message</th>',
                '<td scope="row"><%= _.escape(item.get("message")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("misc_blurb")) { %>',
                "<tr>",
                '<th scope="row">Misc. blurb</th>',
                '<td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("misc_info")) { %>',
                "<tr>",
                '<th scope="row">Misc. info</th>',
                '<td scope="row"><%= _.escape(item.get("misc_info")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("tags")) { %>',
                "<tr>",
                '<th scope="row">Tags</th>',
                '<td scope="row"><%= _.escape(item.get("tags")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if ( item.get("uuid") !== "ok" ) { %>',
                "<tr>",
                '<th scope="row">UUID</th>',
                '<td scope="row"><%= _.escape(item.get("uuid")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if ( item.get("state") !== "ok" ) { %>',
                "<tr>",
                '<th scope="row">State</th>',
                '<td scope="row"><%= _.escape(item.get("state")) %></td>',
                "</tr>",
                "<% } %>",
                "</table>",

                '<% if (item.get("job_stderr")) { %>',
                "<h4>Job Standard Error</h4>",
                '<pre class="code">',
                '<%= _.escape(item.get("job_stderr")) %>',
                "</pre>",
                "<% } %>",

                '<% if (item.get("job_stdout")) { %>',
                "<h4>Job Standard Output</h4>",
                '<pre class="code">',
                '<%= _.escape(item.get("job_stdout")) %>',
                "</pre>",
                "<% } %>",

                "<div>",
                '<pre class="peek">',
                "</pre>",
                "</div>",

                '<% if (item.get("has_versions")) { %>',
                "<div>",
                "<h3>Expired versions:</h3>",
                "<ul>",
                '<% _.each(item.get("expired_versions"), function(version) { %>',
                '<li><a title="See details of this version" href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>/versions/<%- version[0] %>"><%- version[1] %></a></li>',
                "<% }) %>",
                "<ul>",
                "</div>",
                "<% } %>",
                // TABLE END
                "</div>",
                // CONTAINER END
                "</div>"
            ].join("")
        );
    },

    templateVersion: function() {
        return _.template(
            [
                // CONTAINER START
                '<div class="library_style_container">',
                '<div class="d-flex mb-2">',
                '<a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>">',
                '<button data-toggle="tooltip" data-placement="top" title="Go to latest dataset" class="btn btn-secondary toolbar-item mr-1" type="button">',
                '<span class="fa fa-caret-left fa-lg"></span>',
                "&nbsp;Latest dataset",
                "</button>",
                "<a>",
                "</div>",

                // BREADCRUMBS
                '<ol class="breadcrumb">',
                '<li class="breadcrumb-item"><a title="Return to the list of libraries" href="#">Libraries</a></li>',
                '<% _.each(item.get("full_path"), function(path_item) { %>',
                "<% if (path_item[0] != item.id) { %>",
                '<li class="breadcrumb-item"><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',
                "<% } else { %>",
                '<li class="breadcrumb-item active"><span title="You are here"><%- path_item[1] %></span></li>',
                "<% } %>",
                "<% }); %>",
                "</ol>",

                '<div class="alert alert-warning">This is an expired version of the library dataset: <%= _.escape(item.get("name")) %></div>',
                // DATASET START
                '<div class="dataset_table">',
                '<table class="grid table table-striped table-sm">',
                "<tr>",
                '<th scope="row" id="id_row" data-id="<%= _.escape(ldda.id) %>">Name</th>',
                '<td><%= _.escape(ldda.get("name")) %></td>',
                "</tr>",
                '<% if (ldda.get("file_ext")) { %>',
                "<tr>",
                '<th scope="row">Data type</th>',
                '<td><%= _.escape(ldda.get("file_ext")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("genome_build")) { %>',
                "<tr>",
                '<th scope="row">Genome build</th>',
                '<td><%= _.escape(ldda.get("genome_build")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("file_size")) { %>',
                "<tr>",
                '<th scope="row">Size</th>',
                '<td><%= _.escape(ldda.get("file_size")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("date_uploaded")) { %>',
                "<tr>",
                '<th scope="row">Date uploaded (UTC)</th>',
                '<td><%= _.escape(ldda.get("date_uploaded")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("uploaded_by")) { %>',
                "<tr>",
                '<th scope="row">Uploaded by</th>',
                '<td><%= _.escape(ldda.get("uploaded_by")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("metadata_data_lines")) { %>',
                "<tr>",
                '<th scope="row">Data Lines</th>',
                '<td scope="row"><%= _.escape(ldda.get("metadata_data_lines")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("metadata_comment_lines")) { %>',
                "<tr>",
                '<th scope="row">Comment Lines</th>',
                '<td scope="row"><%= _.escape(ldda.get("metadata_comment_lines")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("metadata_columns")) { %>',
                "<tr>",
                '<th scope="row">Number of Columns</th>',
                '<td scope="row"><%= _.escape(ldda.get("metadata_columns")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("metadata_column_types")) { %>',
                "<tr>",
                '<th scope="row">Column Types</th>',
                '<td scope="row"><%= _.escape(ldda.get("metadata_column_types")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("message")) { %>',
                "<tr>",
                '<th scope="row">Message</th>',
                '<td scope="row"><%= _.escape(ldda.get("message")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("misc_blurb")) { %>',
                "<tr>",
                '<th scope="row">Miscellaneous blurb</th>',
                '<td scope="row"><%= _.escape(ldda.get("misc_blurb")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (ldda.get("misc_info")) { %>',
                "<tr>",
                '<th scope="row">Miscellaneous information</th>',
                '<td scope="row"><%= _.escape(ldda.get("misc_info")) %></td>',
                "</tr>",
                "<% } %>",
                '<% if (item.get("tags")) { %>',
                "<tr>",
                '<th scope="row">Tags</th>',
                '<td scope="row"><%= _.escape(item.get("tags")) %></td>',
                "</tr>",
                "<% } %>",
                "</table>",
                "<div>",
                '<pre class="peek">',
                "</pre>",
                "</div>",
                // DATASET END
                "</div>",
                // CONTAINER END
                "</div>"
            ].join("")
        );
    },

    templateModifyDataset: function() {
        return _.template(
            [
                // CONTAINER START
                '<div class="library_style_container">',

                // BREADCRUMBS
                '<ol class="breadcrumb">',
                '<li class="breadcrumb-item"><a title="Return to the list of libraries" href="#">Libraries</a></li>',
                '<% _.each(item.get("full_path"), function(path_item) { %>',
                "<% if (path_item[0] != item.id) { %>",
                '<li class="breadcrumb-item"><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',
                "<% } else { %>",
                '<li class="breadcrumb-item active"><span title="You are here"><%- path_item[1] %></span></li>',
                "<% } %>",
                "<% }); %>",
                "</ol>",

                '<div class="dataset_table">',
                '<table class="grid table table-striped table-sm">',
                "<tr>",
                '<th class="dataset-first-column" scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>',
                '<td><input class="input_dataset_name form-control" type="text" placeholder="name" value="<%= _.escape(item.get("name")) %>"></td>',
                "</tr>",
                "<tr>",
                '<th scope="row">Data type</th>',
                "<td>",
                '<span id="dataset_extension_select" class="dataset-extension-select" />',
                "</td>",
                "</tr>",
                "<tr>",
                '<th scope="row">Genome build</th>',
                "<td>",
                '<span id="dataset_genome_select" class="dataset-genome-select" />',
                "</td>",
                "</tr>",
                "<tr>",
                '<th scope="row">Size</th>',
                '<td><%= _.escape(item.get("file_size")) %></td>',
                "</tr>",
                "<tr>",
                '<th scope="row">Date uploaded (UTC)</th>',
                '<td><%= _.escape(item.get("date_uploaded")) %></td>',
                "</tr>",
                "<tr>",
                '<th scope="row">Uploaded by</th>',
                '<td><%= _.escape(item.get("uploaded_by")) %></td>',
                "</tr>",
                '<tr scope="row">',
                '<th scope="row">Data Lines</th>',
                '<td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>',
                "</tr>",
                '<th scope="row">Comment Lines</th>',
                '<% if (item.get("metadata_comment_lines") === "") { %>',
                '<td scope="row"><%= _.escape(item.get("metadata_comment_lines")) %></td>',
                "<% } else { %>",
                '<td scope="row">unknown</td>',
                "<% } %>",
                "</tr>",
                "<tr>",
                '<th scope="row">Number of Columns</th>',
                '<td scope="row"><%= _.escape(item.get("metadata_columns")) %></td>',
                "</tr>",
                "<tr>",
                '<th scope="row">Column Types</th>',
                '<td scope="row"><%= _.escape(item.get("metadata_column_types")) %></td>',
                "</tr>",
                "<tr>",
                '<th scope="row">Message</th>',
                '<td scope="row"><input class="input_dataset_message form-control" type="text" placeholder="message" value="<%= _.escape(item.get("message")) %>"></td>',
                "</tr>",
                "<tr>",
                '<th scope="row">Misc. blurb</th>',
                '<td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>',
                "</tr>",
                "<tr>",
                '<th scope="row">Misc. information</th>',
                '<td><input class="input_dataset_misc_info form-control" type="text" placeholder="info" value="<%= _.escape(item.get("misc_info")) %>"></td>',
                "</tr>",
                //TODO: add functionality to modify tags here
                '<% if (item.get("tags")) { %>',
                "<tr>",
                '<th scope="row">Tags</th>',
                '<td scope="row"><%= _.escape(item.get("tags")) %></td>',
                "</tr>",
                "<% } %>",
                "</table>",
                "<div>",
                '<pre class="peek">',
                "</pre>",
                "</div>",
                "</div>",

                '<div class="d-flex">',
                '<button data-toggle="tooltip" data-placement="top" title="Cancel modifications" class="btn btn-secondary toolbtn_cancel_modifications toolbar-item mr-1" type="button">',
                '<span class="fa fa-times"></span>',
                "&nbsp;Cancel",
                "</button>",
                '<button data-toggle="tooltip" data-placement="top" title="Save modifications" class="btn btn-secondary toolbtn_save_modifications toolbar-item mr-1" type="button">',
                '<span class="fa fa-floppy-o"></span>',
                "&nbsp;Save",
                "</button>",
                "</div>",

                // CONTAINER END
                "</div>"
            ].join("")
        );
    },

    templateDatasetPermissions: function() {
        return _.template(
            [
                // CONTAINER START
                '<div class="library_style_container">',
                '<div class="d-flex mb-2">',
                '<a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>">',
                '<button data-toggle="tooltip" data-placement="top" title="Go back to dataset" class="btn btn-secondary toolbar-item mr-1" type="button">',
                '<span class="fa fa-file-o"></span>',
                "&nbsp;Dataset Details",
                "</button>",
                "<a>",
                "</div>",

                // BREADCRUMBS
                '<ol class="breadcrumb">',
                '<li class="breadcrumb-item"><a title="Return to the list of libraries" href="#">Libraries</a></li>',
                '<% _.each(item.get("full_path"), function(path_item) { %>',
                "<% if (path_item[0] != item.id) { %>",
                '<li class="breadcrumb-item"><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',
                "<% } else { %>",
                '<li class="breadcrumb-item active"><span title="You are here"><%- path_item[1] %></span></li>',
                "<% } %>",
                "<% }); %>",
                "</ol>",

                '<h1>Dataset: <%= _.escape(item.get("name")) %></h1>',
                '<div class="alert alert-warning">',
                "<% if (is_admin) { %>",
                "You are logged in as an <strong>administrator</strong> therefore you can manage any dataset on this Galaxy instance. Please make sure you understand the consequences.",
                "<% } else { %>",
                "You can assign any number of roles to any of the following permission types. However please read carefully the implications of such actions.",
                "<% } %>",
                "</div>",
                '<div class="dataset_table">',
                "<h2>Library-related permissions</h2>",
                "<h4>Roles that can modify the library item</h4>",
                '<div id="modify_perm" class="modify_perm roles-selection"></div>',
                '<div class="alert alert-info roles-selection">User with <strong>any</strong> of these roles can modify name, metadata, and other information about this library item.</div>',
                "<hr/>",
                "<h2>Dataset-related permissions</h2>",
                '<div class="alert alert-warning">Changes made below will affect <strong>every</strong> library item that was created from this dataset and also every history this dataset is part of.</div>',
                '<% if (!item.get("is_unrestricted")) { %>',
                '<p>You can <span class="remove-restrictions"><a href="">remove all access restrictions</a></span> on this dataset.</p>',
                "<% } else { %>",
                '<p>You can <span class="make-private"><a href="">make this dataset private</a></span> to you.</p>',
                "<% } %>",
                "<h4>Roles that can access the dataset</h4>",
                '<div id="access_perm" class="access_perm roles-selection"></div>',
                '<div class="alert alert-info roles-selection">',
                "User has to have <strong>all these roles</strong> in order to access this dataset.",
                " Users without access permission <strong>cannot</strong> have other permissions on this dataset.",
                " If there are no access roles set on the dataset it is considered <strong>unrestricted</strong>.",
                "</div>",
                "<h4>Roles that can manage permissions on the dataset</h4>",
                '<div id="manage_perm" class="manage_perm roles-selection"></div>',
                '<div class="alert alert-info roles-selection">',
                "User with <strong>any</strong> of these roles can manage permissions of this dataset. If you remove yourself you will lose the ability manage this dataset unless you are an admin.",
                "</div>",
                '<button data-toggle="tooltip" data-placement="top" title="Save modifications made on this page" class="btn btn-secondary toolbtn_save_permissions  type="button">',
                '<span class="fa fa-floppy-o"></span>',
                "&nbsp;Save",
                "</button>",
                "</div>",
                // CONTAINER END
                "</div>"
            ].join("")
        );
    },

    templateBulkImportInModal: function() {
        return _.template(
            [
                "<div>",
                '<div class="library-modal-item">',
                "Select history: ",
                '<select id="dataset_import_single" name="dataset_import_single" style="width:50%; margin-bottom: 1em; " autofocus>',
                "<% _.each(histories, function(history) { %>",
                '<option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>',
                "<% }); %>",
                "</select>",
                "</div>",
                '<div class="library-modal-item">',
                "or create new: ",
                '<input type="text" name="history_name" value="" placeholder="name of the new history" style="width:50%;">',
                "</input>",
                "</div>",
                "</div>"
            ].join("")
        );
    }
});

export default {
    LibraryDatasetView: LibraryDatasetView
};
