import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import mod_toastr from "libs/toastr";
import mod_library_model from "mvc/library/library-model";
import mod_library_folderrow_view from "mvc/library/library-folderrow-view";
import { getGalaxyInstance } from "app";

var FolderListView = Backbone.View.extend({
    el: "#folder_items_element",
    // progress percentage
    progress: 0,
    // progress rate per one item
    progressStep: 1,

    folderContainer: null,

    current_sort_order: "asc",

    current_sort_key: "name",

    events: {
        "click #select-all-checkboxes": "selectAll",
        "click .dataset_row": "selectClickedRow",
        "click .folder_row": "selectClickedRow",
        "click .sort-folder-name": "sortColumnClicked",
        "click .sort-folder-file_ext": "sortColumnClicked",
        "click .sort-folder-description": "sortColumnClicked",
        "click .sort-folder-state": "sortColumnClicked"
    },

    collection: null,

    defaults: {
        include_deleted: false,
        page_count: null,
        show_page: null
    },

    /**
     * Initialize and fetch the folder from the server.
     * @param  {object} options an object with options
     */
    initialize: function(options) {
        this.options = _.defaults(this.options || {}, this.defaults, options);
        this.modal = null;
        // map of folder item ids to item views = cache
        this.rowViews = {};

        // create a collection of folder items for this view
        this.collection = new mod_library_model.Folder();

        // start to listen if someone modifies the collection
        this.listenTo(this.collection, "add", this.renderOne);
        this.listenTo(this.collection, "remove", this.removeOne);
        this.listenTo(this.collection, "sort", this.rePaint);
        this.listenTo(this.collection, "reset", this.rePaint);

        this.fetchFolder();
    },

    fetchFolder: function(options = {}) {
        this.options.include_deleted = options.include_deleted;
        var self = this;

        this.folderContainer = new mod_library_model.FolderContainer({
            id: this.options.id
        });
        this.folderContainer.url = `${this.folderContainer.attributes.urlRoot + this.options.id}/contents`;

        if (this.options.include_deleted) {
            this.folderContainer.url = `${this.folderContainer.url}?include_deleted=true`;
        }
        this.folderContainer.fetch({
            success: function(folder_container) {
                self.folder_container = folder_container;
                self.render();
            },
            error: function(model, response) {
                let Galaxy = getGalaxyInstance();
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
        var template = this.templateFolder();
        $(".tooltip").hide();

        // find the upper id in the full path
        var path = this.folderContainer.attributes.metadata.full_path;
        var upper_folder_id;
        if (path.length === 1) {
            // the library is above us
            upper_folder_id = 0;
        } else {
            upper_folder_id = path[path.length - 2][0];
        }

        this.$el.html(
            template({
                path: this.folderContainer.attributes.metadata.full_path,
                parent_library_id: this.folderContainer.attributes.metadata.parent_library_id,
                id: this.options.id,
                upper_folder_id: upper_folder_id,
                order: this.current_sort_order
            })
        );

        // when dataset_id is present render its details too
        if (this.options.dataset_id) {
            var row = _.findWhere(self.rowViews, {
                id: this.options.dataset_id
            });
            if (row) {
                row.showDatasetDetails();
            } else {
                mod_toastr.error("Requested dataset not found. Showing folder instead.");
            }
        } else {
            if (this.options.show_page === null || this.options.show_page < 1) {
                this.options.show_page = 1;
            }
            this.paginate();
        }
        $('#center [data-toggle="tooltip"]').tooltip({ trigger: "hover" });
        $("#center").css("overflow", "auto");
    },

    paginate: function(options) {
        let Galaxy = getGalaxyInstance();
        this.options = _.extend(this.options, options);

        if (this.options.show_page === null || this.options.show_page < 1) {
            this.options.show_page = 1;
        }
        this.options.total_items_count = this.folder_container.get("folder").models.length;
        this.options.page_count = Math.ceil(
            this.options.total_items_count / Galaxy.libraries.preferences.get("folder_page_size")
        );
        var page_start = Galaxy.libraries.preferences.get("folder_page_size") * (this.options.show_page - 1);
        var items_to_render = null;
        items_to_render = this.folder_container
            .get("folder")
            .models.slice(page_start, page_start + Galaxy.libraries.preferences.get("folder_page_size"));
        this.options.items_shown = items_to_render.length;
        // User requests page with no items
        if (
            Galaxy.libraries.preferences.get("folder_page_size") * this.options.show_page >
            this.options.total_items_count + Galaxy.libraries.preferences.get("folder_page_size")
        ) {
            items_to_render = [];
        }
        Galaxy.libraries.folderToolbarView.renderPaginator(this.options);
        this.collection.reset(items_to_render);
    },

    rePaint: function(options) {
        this.options = _.extend(this.options, options);
        this.removeAllRows();
        this.renderAll();
        this.checkEmptiness();
    },

    /**
     * Adds all given models to the collection.
     * @param {array of Item or FolderAsModel} array of models that should
     *  be added to the view's collection.
     */
    addAll: function(models) {
        let Galaxy = getGalaxyInstance();
        _.each(models, model => {
            Galaxy.libraries.folderListView.collection.add(model, {
                current_sort_order: false
            });
        });
        $('#center [data-toggle="tooltip"]').tooltip({ trigger: "hover" });
        this.checkEmptiness();
        this.postRender();
    },

    /**
     * Call this after all models are added to the collection
     * to ensure that the folder toolbar will show proper options
     * and that event will be bound on all subviews.
     */
    postRender: function() {
        let Galaxy = getGalaxyInstance();
        var fetched_metadata = this.folderContainer.attributes.metadata;
        fetched_metadata.contains_file_or_folder =
            typeof this.collection.findWhere({ type: "file" }) !== "undefined" ||
            typeof this.collection.findWhere({ type: "folder" }) !== "undefined";
        Galaxy.libraries.folderToolbarView.configureElements(fetched_metadata);
    },

    /**
     * Iterates this view's collection and calls the render
     * function for each. Also binds the hover behavior.
     */
    renderAll: function() {
        var self = this;
        _.each(this.collection.models.reverse(), model => {
            self.renderOne(model);
        });
        this.postRender();
    },

    /**
     * Creates a view for the given model and adds it to the folder view.
     * @param {Item or FolderAsModel} model of the view that will be rendered
     */
    renderOne: function(model) {
        this.options.contains_file_or_folder = true;
        //if (model.get('type') !== 'folder'){
        // model.set('readable_size', this.size_to_string(model.get('file_size')));
        //}
        model.set("folder_id", this.id);
        var rowView = new mod_library_folderrow_view.FolderRowView({
            model: model
        });

        // save new rowView to cache
        this.rowViews[model.get("id")] = rowView;

        this.$el.find("#first_folder_item").after(rowView.el);
    },

    /**
     * Remove the view of the given model from the DOM.
     * @param {Item or FolderAsModel} model of the view that will be removed
     */
    removeOne: function(model) {
        this.$el
            .find("tr")
            .filter(function() {
                return $(this).data("id") && $(this).data("id") === model.id;
            })
            .remove();
    },

    /**
     * Remove all dataset and folder row elements from the DOM.
     */
    removeAllRows: function() {
        $(".library-row").remove();
    },

    /** Checks whether the list is empty and adds/removes the message */
    checkEmptiness: function() {
        if (this.$el.find(".dataset_row").length === 0 && this.$el.find(".folder_row").length === 0) {
            this.$el.find(".empty-folder-message").show();
        } else {
            this.$el.find(".empty-folder-message").hide();
        }
    },

    sortColumnClicked: function(event) {
        event.preventDefault();
        this.current_sort_order = this.current_sort_order === "asc" ? "desc" : "asc";
        this.current_sort_key = event.currentTarget.className.replace("sort-folder-", "");
        this.collection.sortFolder(this.current_sort_key, this.current_sort_order);
        this.renderSortIcon();
    },

    /**
     * User clicked the checkbox in the table heading
     * @param  {context} event
     */
    selectAll: function(event) {
        var selected = event.target.checked;
        var self = this;
        // Iterate each checkbox
        $(":checkbox", "#folder_list_body").each(function() {
            this.checked = selected;
            var $row = $(this).closest("tr");
            // Change color of selected/unselected
            if (selected) {
                self.makeDarkRow($row);
            } else {
                self.makeWhiteRow($row);
            }
        });
    },

    /**
     * Check checkbox if user clicks on the whole row or
     *  on the checkbox itself
     */
    selectClickedRow: function(event) {
        var checkbox = "";
        var $row;
        var source;
        $row = $(event.target).closest("tr");
        if (event.target.localName === "input") {
            checkbox = event.target;
            source = "input";
        } else if (event.target.localName === "td") {
            checkbox = $row.find(":checkbox")[0];
            source = "td";
        }
        if (checkbox.checked) {
            if (source === "td") {
                checkbox.checked = "";
                this.makeWhiteRow($row);
            } else if (source === "input") {
                this.makeDarkRow($row);
            }
        } else {
            if (source === "td") {
                checkbox.checked = "selected";
                this.makeDarkRow($row);
            } else if (source === "input") {
                this.makeWhiteRow($row);
            }
        }
    },

    makeDarkRow: function($row) {
        $row.removeClass("light").addClass("dark");
        $row.find("a")
            .removeClass("light")
            .addClass("dark");
        $row.find(".fa-file-o")
            .removeClass("fa-file-o")
            .addClass("fa-file");
        $row.find(".fa-folder-o")
            .removeClass("fa-folder-o")
            .addClass("fa-folder");
    },

    makeWhiteRow: function($row) {
        $row.removeClass("dark").addClass("light");
        $row.find("a")
            .removeClass("dark")
            .addClass("light");
        $row.find(".fa-file")
            .removeClass("fa-file")
            .addClass("fa-file-o");
        $row.find(".fa-folder")
            .removeClass("fa-folder")
            .addClass("fa-folder-o");
    },

    renderSortIcon: function() {
        if (this.current_sort_order === "asc") {
            $('[class*="sort-icon"]')
                .removeClass("fa-sort-alpha-desc")
                .removeClass("fa-sort-alpha-asc");
            $(`.sort-icon-${this.current_sort_key}`).addClass("fa-sort-alpha-asc");
        } else {
            $(`.sort-icon-${this.current_sort_key}`).addClass("fa-sort-alpha-desc");
        }
    },

    templateFolder: function() {
        return _.template(
            [
                '<ol class="breadcrumb">',
                '<li class="breadcrumb-item"><a title="Return to the list of libraries" href="#">Libraries</a></li>',
                "<% _.each(path, function(path_item) { %>",
                "<% if (path_item[0] != id) { %>",
                '<li class="breadcrumb-item"><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',
                "<% } else { %>",
                '<li class="breadcrumb-item active"><span title="You are in this folder"><%- path_item[1] %></span></li>',
                "<% } %>",
                "<% }); %>",
                "</ol>",

                // FOLDER CONTENT
                '<table data-library-id="<%- parent_library_id  %>" class="grid table table-sm">',
                "<thead>",
                '<th class="button_heading"></th>',
                '<th class="mid" style="width: 20px; " title="Check to select all datasets"><input id="select-all-checkboxes" style="margin: 0;" type="checkbox"></th>',
                '<th><a class="sort-folder-name" title="Click to reverse order" href="#">name</a> <span title="Sorted alphabetically" class="sort-icon-name fa fa-sort-alpha-<%- order %>"></span></th>',
                '<th style="width:20%;"><a class="sort-folder-description" title="Click to reverse order" href="#">description</a> <span title="Sorted alphabetically" class="sort-icon-description fa"></span></th>',
                '<th style="width:5%;"><a class="sort-folder-file_ext" title="Click to reverse order" href="#">data type</a> <span title="Sorted alphabetically" class="sort-icon-file_ext fa"></span></th>',
                '<th style="width:10%;">size</th>',
                '<th style="width:160px;">time updated (UTC)</th>',
                '<th style="width:5%;"><a class="sort-folder-state" title="Click to reverse order" href="#">state</a> <span title="Sorted alphabetically" class="sort-icon-state fa"></span></th>',
                '<th style="width:150px;"></th> ',
                "</thead>",
                '<tbody id="folder_list_body">',
                '<tr id="first_folder_item">',
                "<td>",
                '<a href="#<% if (upper_folder_id !== 0){ print("folders/" + upper_folder_id)} %>" title="Go to parent folder" class="btn_open_folder btn btn-secondary btn-sm">..<a>',
                "</td>",
                "<td></td>",
                "<td></td>",
                "<td></td>",
                "<td></td>",
                "<td></td>",
                "<td></td>",
                "<td></td>",
                "<td></td>",
                "</tr>",
                "</tbody>",
                "</table>",
                '<div class="empty-folder-message" style="display:none;">',
                "This folder is either empty or you do not have proper access permissions to see the contents. If you expected something to show up",
                ' please consult the <a href="https://galaxyproject.org/data-libraries/#permissions" target="_blank">library security wikipage</a>',
                ' or visit the <a href="https://biostar.usegalaxy.org/" target="_blank">Galaxy support site</a>.',
                "</div>"
            ].join("")
        );
    }
});

export default {
    FolderListView: FolderListView
};
