import $ from "jquery";
import _ from "libs/underscore";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";
import { Toast } from "ui/toast";
import mod_library_model from "mvc/library/library-model";
import mod_library_libraryrow_view from "mvc/library/library-libraryrow-view";

var LibraryListView = Backbone.View.extend({
    el: "#libraries_element",

    events: {
        "click .sort-libraries-link": "sort_clicked",
    },

    defaults: {
        page_count: null,
        show_page: null,
        all_fetched: false,
    },

    /**
     * Initialize and fetch the libraries from server.
     * Async render afterwards.
     * @param  {object} options an object with options
     */
    initialize: function (options) {
        this.options = _.defaults(this.options || {}, options, this.defaults);
        var that = this;
        this.modal = null;
        // collection of {Item}s
        this.collection = new mod_library_model.Libraries();
        this.collection.url = `${this.collection.urlRoot}?deleted=false`;
        this.collection.fetch({
            success: function () {
                that.render();
            },
            error: function (model, response) {
                if (typeof response.responseJSON !== "undefined") {
                    Toast.error(response.responseJSON.err_msg);
                } else {
                    Toast.error("An error occurred.");
                }
            },
        });
    },

    /**
     * Render the libraries table either from the object's own collection,
     * or from a given array of library models,
     * or render an empty list in case no data is given.
     */
    render: function (options) {
        const Galaxy = getGalaxyInstance();
        this.options = _.extend(this.options, options);
        this.setElement("#libraries_element");
        var template = this.templateLibraryList();
        var libraries_to_render = null;
        var models = null;
        var is_public = (model) => model.get("public") === true;
        $(".tooltip").hide();
        if (typeof options !== "undefined") {
            models = typeof options.models !== "undefined" ? options.models : null;
        }
        if (this.collection !== null && models === null) {
            this.sortLibraries();
            if (Galaxy.libraries.preferences.get("with_deleted")) {
                libraries_to_render = this.collection.models;
            } else {
                libraries_to_render = this.collection.where({
                    deleted: false,
                });
            }
            if (Galaxy.libraries.preferences.get("without_restricted")) {
                libraries_to_render = _.filter(libraries_to_render, is_public);
            }
        } else if (models !== null) {
            if (Galaxy.libraries.preferences.get("with_deleted")) {
                libraries_to_render = models;
            } else {
                var is_deleted = (model) => model.get("deleted") === false;
                libraries_to_render = _.filter(models, is_deleted);
            }
            if (Galaxy.libraries.preferences.get("without_restricted")) {
                libraries_to_render = _.filter(libraries_to_render, is_public);
            }
        } else {
            libraries_to_render = [];
        }

        // pagination
        if (this.options.show_page === null || this.options.show_page < 1) {
            this.options.show_page = 1;
        }
        this.options.total_libraries_count = libraries_to_render.length;
        var page_start = Galaxy.libraries.preferences.get("library_page_size") * (this.options.show_page - 1);
        this.options.page_count = Math.ceil(
            this.options.total_libraries_count / Galaxy.libraries.preferences.get("library_page_size")
        );
        if (this.options.total_libraries_count > 0 && page_start < this.options.total_libraries_count) {
            libraries_to_render = libraries_to_render.slice(
                page_start,
                page_start + Galaxy.libraries.preferences.get("library_page_size")
            );
            this.options.libraries_shown = libraries_to_render.length;
            // User requests page with no libraries
            if (
                Galaxy.libraries.preferences.get("library_page_size") * this.options.show_page >
                this.options.total_libraries_count + Galaxy.libraries.preferences.get("library_page_size")
            ) {
                libraries_to_render = [];
            }
            this.$el.html(
                template({
                    length: 1,
                    order: Galaxy.libraries.preferences.get("sort_order"),
                    search_term: Galaxy.libraries.libraryToolbarView.options.search_term,
                })
            );
            Galaxy.libraries.libraryToolbarView.renderPaginator(this.options);
            this.renderRows(libraries_to_render);
        } else {
            this.$el.html(
                template({
                    length: 0,
                    order: Galaxy.libraries.preferences.get("sort_order"),
                    search_term: Galaxy.libraries.libraryToolbarView.options.search_term,
                })
            );
            Galaxy.libraries.libraryToolbarView.renderPaginator(this.options);
        }
        $('#center [data-toggle="tooltip"]').tooltip({ trigger: "hover" });
        $("#center").css("overflow", "auto");
    },

    fetchDeleted: function () {
        if (this.options.all_fetched) {
            this.render();
        } else {
            var that = this;
            this.collection.url = `${this.collection.urlRoot}?deleted=true`;
            this.collection.fetch({
                remove: false,
                success: function () {
                    that.options.all_fetched = true;
                    that.render();
                },
                error: function (model, response) {
                    if (typeof response.responseJSON !== "undefined") {
                        Toast.error(response.responseJSON.err_msg);
                    } else {
                        Toast.error("An error occurred.");
                    }
                },
            });
        }
    },

    /**
     * Render all given models as rows in the library list
     * @param  {array} libraries_to_render array of library models to render
     */
    renderRows: function (libraries_to_render) {
        for (var i = 0; i < libraries_to_render.length; i++) {
            var library = libraries_to_render[i];
            this.renderOne({ library: library });
        }
    },

    /**
     * Create a view for the given model and add it to the libraries view.
     * @param {Library} model of the view that will be rendered
     */
    renderOne: function (options) {
        var library = options.library;
        var rowView = new mod_library_libraryrow_view.LibraryRowView(library);
        this.$el.find("#library_list_body").append(rowView.el);
    },

    /**
     * Table heading was clicked, update sorting preferences and re-render.
     * @return {[type]} [description]
     */
    sort_clicked: function () {
        const Galaxy = getGalaxyInstance();
        if (Galaxy.libraries.preferences.get("sort_order") === "asc") {
            Galaxy.libraries.preferences.set({ sort_order: "desc" });
        } else {
            Galaxy.libraries.preferences.set({ sort_order: "asc" });
        }
        this.render();
    },

    /**
     * Sort the underlying collection according to the parameters received.
     * Currently supports only sorting by name.
     */
    sortLibraries: function () {
        const Galaxy = getGalaxyInstance();
        if (Galaxy.libraries.preferences.get("sort_by") === "name") {
            if (Galaxy.libraries.preferences.get("sort_order") === "asc") {
                this.collection.sortLibraries("name", "asc");
            } else if (Galaxy.libraries.preferences.get("sort_order") === "desc") {
                this.collection.sortLibraries("name", "desc");
            }
        }
    },

    /**
     * In case the search_term is not empty perform the search and render
     * the result. Render all visible libraries otherwise.
     * @param  {string} search_term string to search for
     */
    searchLibraries: function (search_term) {
        var trimmed_term = $.trim(search_term);
        if (trimmed_term !== "") {
            var results = null;
            results = this.collection.search(search_term);
            this.options.searching = true;
            this.render({ models: results, show_page: 1 });
        } else {
            this.options.searching = false;
            this.render();
        }
    },

    /**
     * Create the new library inline
     */
    createLibraryInline: function () {
        if (this.$el.find("tr.new-row").length) {
            this.$el.find("tr.new-row textarea")[0].focus();
        } else {
            const template = this.templateNewRow();
            this.$el.find("#library_list_body").closest("table").show();
            this.$el.find("#library_list_body").prepend(template);

            this.$el.find("tr.new-row textarea")[0].focus();

            this.$el.find("tr.new-row .save_library_btn").click(() => {
                this.createNewLibrary(
                    this.$el.find("tr.new-row textarea")[0].value,
                    this.$el.find("tr.new-row textarea")[1].value,
                    this.$el.find("tr.new-row textarea")[2].value
                );
            });

            this.$el.find("tr.new-row .cancel_library_btn").click(() => {
                this.$el.find("tr.new-row").remove();
            });
        }
    },

    /**
     * Create the new library using the API asynchronously.
     */
    createNewLibrary: function (name, description, synopsis) {
        const Galaxy = getGalaxyInstance();
        const libraryDetails = {
            name,
            description,
            synopsis,
        };
        if (libraryDetails.name !== "") {
            var library = new mod_library_model.Library();
            library.save(libraryDetails, {
                success: (library) => {
                    Galaxy.libraries.libraryListView.collection.add(library);
                    this.$el.find("tr.new-row").remove();
                    Galaxy.libraries.libraryListView.render();

                    $(`tr[data-id="${library.attributes.id}"`)
                        .addClass("table-success")
                        .on("mouseover click", function () {
                            $(this).removeClass("table-success");
                        });

                    Toast.success("Library created.");
                },
                error: (model, response) => {
                    if (typeof response.responseJSON !== "undefined") {
                        Toast.error(response.responseJSON.err_msg);
                    } else {
                        Toast.error("An error occurred.");
                    }
                },
            });
        } else {
            Toast.error("Library's name is missing.");
        }
        return false;
    },

    // MMMMMMMMMMMMMMMMMM
    // === TEMPLATES ====
    // MMMMMMMMMMMMMMMMMM

    templateNewRow: function () {
        return _.template(
            `<tr class="new-row">
                    <td>
                        <textarea name="input_library_name" rows="4" class="form-control input_library_name" placeholder="name" ></textarea>
                    </td>
                    <td>
                        <textarea rows="4" class="form-control input_library_description" placeholder="description"></textarea>
                    </td>
                    <td>
                        <textarea rows="4" class="form-control input_library_synopsis" placeholder="synopsis"></textarea>
                    </td>
                    <td class="right-center">
                        <button data-toggle="tooltip" data-placement="left" title="Save changes"
                            class="btn btn-secondary btn-sm save_library_btn" type="button">
                            <span class="fa fa-floppy-o"></span> Save
                        </button>
                        <button data-toggle="tooltip" data-placement="left" title="Discard changes"
                            class="btn btn-secondary btn-sm cancel_library_btn" type="button">
                            <span class="fa fa-times"></span> Cancel
                        </button>
                    </td>     
            </tr>`
        );
    },

    templateLibraryList: function () {
        return _.template(
            `<div class="library_container table-responsive">
                <table class="grid table table-sm"
                    <% if(length === 0) { %> style="display:none;" <% }%> >
                    <thead>
                        <th style="width:30%;">
                            <a class="sort-libraries-link" title="Click to reverse order" href="javascript:void(0)" role="button">
                                Name
                            </a>
                            <span title="Sorted alphabetically" class="fa fa-sort-alpha-<%- order %>"></span>
                        </th>
                        <th style="width:22%;">Description</th>
                        <th style="width:22%;">Synopsis</th> 
                        <th style="width:26%;"></th>
                    </thead>
                    <tbody id="library_list_body">
                    <!-- library item views will attach here -->
                   </tbody>
                </table>
                    
                <% if(length === 0) { %>
                    <% if(search_term.length > 0) { %>
                        <div>
                            There are no libraries matching your search. Try different keyword.
                        </div>
                    <% } else{ %>
                        <div>
                            There are no libraries visible to you here. If you expected some to show up please consult the
                            <a href="https://galaxyproject.org/data-libraries/#permissions" target="_blank">library security wikipage</a>.
                        </div>
                    <% }%>
                <% }%>
            </div>`
        );
    },
});

export default {
    LibraryListView: LibraryListView,
};
