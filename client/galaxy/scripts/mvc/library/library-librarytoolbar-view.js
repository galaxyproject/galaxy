import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import _l from "utils/localization";
import mod_toastr from "libs/toastr";
import mod_library_model from "mvc/library/library-model";
import { getGalaxyInstance } from "app";

/**
 * This view represents the top part of the library page.
 * It contains the tool bar with controls.
 */
var LibraryToolbarView = Backbone.View.extend({
    el: "#center",

    defaults: {
        search_term: ""
    },

    events: {
        "click #create_new_library_btn": "createLibraryFromModal",
        "click #include_deleted_chk": "includeDeletedChecked",
        "click #exclude_restricted_chk": "excludeRestrictedChecked",
        "click .page_size_prompt": "showPageSizePrompt",
        "keyup .library-search-input": "searchLibraries"
    },

    initialize: function(options) {
        this.options = _.defaults(this.options || {}, options, this.defaults);
        this.render();
    },

    render: function() {
        let Galaxy = getGalaxyInstance();
        var toolbar_template = this.templateToolBar();
        var is_admin = false;
        var is_anonym = true;
        if (Galaxy.user) {
            is_admin = Galaxy.user.isAdmin();
            is_anonym = Galaxy.user.isAnonymous();
        }
        this.$el.html(toolbar_template({ admin_user: is_admin, anon_user: is_anonym }));
        if (is_admin) {
            this.$el.find("#include_deleted_chk")[0].checked = Galaxy.libraries.preferences.get("with_deleted");
            this.$el.find("#exclude_restricted_chk")[0].checked = Galaxy.libraries.preferences.get(
                "without_restricted"
            );
        }
    },

    /**
     * Renders the element that shows pages into its div within the toolbar.
     */
    renderPaginator: function(options) {
        let Galaxy = getGalaxyInstance();
        this.options = _.extend(this.options, options);
        var paginator_template = this.templatePaginator();
        this.$el.find(".library-paginator").html(
            paginator_template({
                show_page: parseInt(this.options.show_page),
                page_count: parseInt(this.options.page_count),
                total_libraries_count: this.options.total_libraries_count,
                libraries_shown: this.options.libraries_shown,
                library_page_size: Galaxy.libraries.preferences.get("library_page_size")
            })
        );
    },

    /**
     * User clicked on 'New library' button. Show modal to
     * satisfy the wish.
     */
    createLibraryFromModal: function(event) {
        event.preventDefault();
        event.stopPropagation();
        let Galaxy = getGalaxyInstance();
        var self = this;
        this.modal = Galaxy.modal;
        this.modal.show({
            closing_events: true,
            title: _l("Create New Library"),
            body: this.templateNewLibraryInModal(),
            buttons: {
                Create: function() {
                    self.createNewLibrary();
                },
                Close: function() {
                    self.modal.hide();
                }
            }
        });
    },

    /**
     * Create the new library using the API asynchronously.
     */
    createNewLibrary: function() {
        let Galaxy = getGalaxyInstance();
        var libraryDetails = this.serializeNewLibrary();
        if (this.validateNewLibrary(libraryDetails)) {
            var library = new mod_library_model.Library();
            var self = this;
            library.save(libraryDetails, {
                success: function(library) {
                    Galaxy.libraries.libraryListView.collection.add(library);
                    self.modal.hide();
                    self.clearLibraryModal();
                    Galaxy.libraries.libraryListView.render();
                    mod_toastr.success("Library created.");
                },
                error: function(model, response) {
                    if (typeof response.responseJSON !== "undefined") {
                        mod_toastr.error(response.responseJSON.err_msg);
                    } else {
                        mod_toastr.error("An error occurred.");
                    }
                }
            });
        } else {
            mod_toastr.error("Library's name is missing.");
        }
        return false;
    },

    /**
     * Show user the propmpt to change the number of libs shown on page.
     */
    showPageSizePrompt: function(e) {
        e.preventDefault();
        let Galaxy = getGalaxyInstance();
        var library_page_size = prompt(
            "How many libraries per page do you want to see?",
            Galaxy.libraries.preferences.get("library_page_size")
        );
        if (library_page_size != null && library_page_size == parseInt(library_page_size)) {
            Galaxy.libraries.preferences.set({
                library_page_size: parseInt(library_page_size)
            });
            Galaxy.libraries.libraryListView.render({ show_page: 1 });
        }
    },

    /**
     * Clear the library modal once it is saved.
     */
    clearLibraryModal: function() {
        $("input[name='Name']").val("");
        $("input[name='Description']").val("");
        $("input[name='Synopsis']").val("");
    },

    /**
     * Prepare new library variables to be submitted to API.
     */
    serializeNewLibrary: function() {
        return {
            name: $("input[name='Name']").val(),
            description: $("input[name='Description']").val(),
            synopsis: $("input[name='Synopsis']").val()
        };
    },

    /**
     * Check whether entered values are valid.
     */
    validateNewLibrary: function(libraryDetails) {
        return libraryDetails.name !== "";
    },

    /**
     * Include or exclude deleted libraries in the view.
     */
    includeDeletedChecked: function(event) {
        let Galaxy = getGalaxyInstance();
        if (event.target.checked) {
            Galaxy.libraries.preferences.set({ with_deleted: true });
            Galaxy.libraries.libraryListView.fetchDeleted();
        } else {
            Galaxy.libraries.preferences.set({ with_deleted: false });
            Galaxy.libraries.libraryListView.render();
        }
    },

    /**
     * Include or exclude restricted libraries in the view.
     */
    excludeRestrictedChecked: function(event) {
        let Galaxy = getGalaxyInstance();
        if (event.target.checked) {
            Galaxy.libraries.preferences.set({ without_restricted: true });
        } else {
            Galaxy.libraries.preferences.set({ without_restricted: false });
        }
        Galaxy.libraries.libraryListView.render();
    },

    /**
     * Take the contents of the search field and send it to the list view
     * to query the collection of libraries.
     */
    searchLibraries: function(event) {
        let Galaxy = getGalaxyInstance();
        var search_term = $(".library-search-input").val();
        this.options.search_term = search_term;
        Galaxy.libraries.libraryListView.searchLibraries(search_term);
    },

    templateToolBar: function() {
        return _.template(
            `<div class="library_style_container">
                <div class="d-flex align-items-center mb-2">
                    <a class="btn btn-secondary mr-1" data-toggle="tooltip" data-placement="top" title="Go to first page" href="#">
                        <span class="fa fa-home"/>
                    </a>
                    <a class="library-help-button btn btn-secondary mr-1" data-toggle="tooltip" title="See this screen annotated" href="https://galaxyproject.org/data-libraries/screen/list-of-libraries/" target="_blank">
                        <span class="fa fa-question"/>
                    </a>
                    <% if(admin_user === true) { %>
                        <button data-toggle="tooltip" data-placement="top" title="Create new library" id="create_new_library_btn" class="mr-1 btn btn-secondary" type="button">
                            <span class="fa fa-plus"/>
                        </button>
                    <% } %>
                    <div class="d-flex align-items-center library-paginator mr-1" />
                        <form class="form-inline mr-1">
                            <input type="text" class="form-control library-search-input mr-1" placeholder="Great Library" size="15">
                            <% if(admin_user === true) { %>
                                <div class="form-check mr-1">
                                    <input class="form-check-input" id="include_deleted_chk" type="checkbox"/>
                                    <label class="form-check-label" for="include_deleted_chk">include deleted</label>
                                </div>
                                <div class="form-check mr-1">
                                    <input class="form-check-input" id="exclude_restricted_chk" type="checkbox"/>
                                    <label class="form-check-label" for="exclude_restricted_chk">exclude restricted</label>
                                </div>
                            <% } %>
                        </form>
                    </div>
                    <div id="libraries_element" />
                </div>
            </div>`
        );
    },

    templatePaginator: function() {
        return _.template(
            [
                '<ul class="pagination mr-1">',
                "<% if ( ( show_page - 1 ) > 0 ) { %>",
                "<% if ( ( show_page - 1 ) > page_count ) { %>", // we are on higher page than total page count
                '<li class="page-item"><a class="page-link" href="#page/1"><span class="fa fa-angle-double-left"></span></a></li>',
                '<li class="page-item disabled"><a class="page-link" href="#page/<% print( show_page ) %>"><% print( show_page - 1 ) %></a></li>',
                "<% } else { %>",
                '<li class="page-item"><a class="page-link" href="#page/1"><span class="fa fa-angle-double-left"></span></a></li>',
                '<li class="page-item"><a class="page-link" href="#page/<% print( show_page - 1 ) %>"><% print( show_page - 1 ) %></a></li>',
                "<% } %>",
                "<% } else { %>", // we are on the first page
                '<li class="page-item disabled"><a class="page-link" href="#page/1"><span class="fa fa-angle-double-left"></span></a></li>',
                '<li class="page-item disabled"><a class="page-link" href="#page/<% print( show_page ) %>"><% print( show_page - 1 ) %></a></li>',
                "<% } %>",
                '<li class="page-item active">',
                '<a class="page-link" href="#page/<% print( show_page ) %>"><% print( show_page ) %></a>',
                "</li>",
                "<% if ( ( show_page ) < page_count ) { %>",
                '<li class="page-item"><a class="page-link" href="#page/<% print( show_page + 1 ) %>"><% print( show_page + 1 ) %></a></li>',
                '<li class="page-item"><a class="page-link" href="#page/<% print( page_count ) %>"><span class="fa fa-angle-double-right"></span></a></li>',
                "<% } else { %>",
                '<li class="page-item disabled"><a class="page-link" href="#page/<% print( show_page  ) %>"><% print( show_page + 1 ) %></a></li>',
                '<li class="page-item disabled"><a class="page-link" href="#page/<% print( page_count ) %>"><span class="fa fa-angle-double-right"></span></a></li>',
                "<% } %>",
                "</ul>",
                '<span class="mr-1">',
                ' <%- libraries_shown %> libraries shown <a href="" data-toggle="tooltip" data-placement="top" title="currently <%- library_page_size %> per page" class="page_size_prompt">(change)</a>',
                "</span>",
                '<span class="mr-1">',
                " <%- total_libraries_count %> total",
                "</span>"
            ].join("")
        );
    },

    templateNewLibraryInModal: function() {
        return _.template(
            [
                '<div id="new_library_modal">',
                "<form>",
                '<input type="text" name="Name" value="" placeholder="Name" autofocus>',
                '<input type="text" name="Description" value="" placeholder="Description">',
                '<input type="text" name="Synopsis" value="" placeholder="Synopsis">',
                "</form>",
                "</div>"
            ].join("")
        );
    }
});

export default {
    LibraryToolbarView: LibraryToolbarView
};
