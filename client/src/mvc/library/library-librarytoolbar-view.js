import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";

/**
 * This view represents the top part of the library page.
 * It contains the tool bar with controls.
 */
var LibraryToolbarView = Backbone.View.extend({
    el: "#center",

    defaults: {
        search_term: "",
    },

    events: {
        "click #create_new_library_btn": "createLibraryInline",
        "click #include_deleted_chk": "includeDeletedChecked",
        "click #exclude_restricted_chk": "excludeRestrictedChecked",
        "keydown .page_size": "changePageSize",
        "blur .page_size": "changePageSize",
        "keyup .library-search-input": "searchLibraries",
    },

    initialize: function (options) {
        this.options = _.defaults(this.options || {}, options, this.defaults);
        this.render();
    },

    render: function () {
        const Galaxy = getGalaxyInstance();
        var toolbar_template = this.templateToolBar();
        var is_admin = false;
        var is_anonym = true;
        if (Galaxy.user) {
            is_admin = Galaxy.user.isAdmin();
            is_anonym = Galaxy.user.isAnonymous();
        }
        this.$el.html(
            toolbar_template({
                admin_user: is_admin,
                anon_user: is_anonym,
                library_page_size: Galaxy.libraries.preferences.get("library_page_size"),
            })
        );
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
    renderPaginator: function (options) {
        const Galaxy = getGalaxyInstance();
        this.options = _.extend(this.options, options);
        var paginator_template = this.templatePaginator();
        var paginator_text_template = this.templatePaginatorText();
        this.$el.find(".library-paginator > .paginator").html(
            paginator_template({
                show_page: parseInt(this.options.show_page),
                page_count: parseInt(this.options.page_count),
                total_libraries_count: this.options.total_libraries_count,
                libraries_shown: this.options.libraries_shown,
                library_page_size: Galaxy.libraries.preferences.get("library_page_size"),
            })
        );
        this.$el.find(".library-paginator > .paginator-text").html(
            paginator_text_template({
                show_page: parseInt(this.options.show_page),
                page_count: parseInt(this.options.page_count),
                total_libraries_count: this.options.total_libraries_count,
                libraries_shown: this.options.libraries_shown,
                library_page_size: Galaxy.libraries.preferences.get("library_page_size"),
            })
        );
    },

    /**
     * Crreate the new library inline
     */
    createLibraryInline: function () {
        const Galaxy = getGalaxyInstance();
        Galaxy.libraries.libraryListView.createLibraryInline();
    },

    /**
     * Change the number of libs shown on page.
     */
    changePageSize: function (e) {
        if (e.type === "focusout" || (e.type === "keydown" && e.keyCode === 13)) {
            e.preventDefault();
            const Galaxy = getGalaxyInstance();
            Galaxy.libraries.preferences.set({
                library_page_size: parseInt(e.target.value),
            });
            Galaxy.libraries.libraryListView.render({ show_page: 1 });
        }
    },

    /**
     * Include or exclude deleted libraries in the view.
     */
    includeDeletedChecked: function (event) {
        const Galaxy = getGalaxyInstance();
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
    excludeRestrictedChecked: function (event) {
        const Galaxy = getGalaxyInstance();
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
    searchLibraries: function (event) {
        const Galaxy = getGalaxyInstance();
        var search_term = $(".library-search-input").val();
        this.options.search_term = search_term;
        Galaxy.libraries.libraryListView.searchLibraries(search_term);
    },

    templateToolBar: function () {
        return _.template(
            `<div class="library_style_container">
                <div class="d-flex align-items-center mb-2 library-toolbar">
                    <a class="btn btn-secondary mr-1" data-toggle="tooltip" data-placement="top" title="Go to first page" href="#" role="button">
                        <span class="fa fa-home fa-lg"/>
                    </a>
                    <% if(admin_user === true) { %>
                        <button data-toggle="tooltip" data-placement="top" title="Create new library" id="create_new_library_btn" class="mr-1 btn btn-secondary" type="button">
                            <span class="fa fa-plus" /> Library
                        </button>
                    <% } %>
                    <div class="d-flex align-items-center mr-1" />
                        <form class="form-inline mr-1">
                            <input type="text" id="library-filter" class="form-control library-search-input mr-1" placeholder="Search" size="15">
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
                    <div class="d-flex justify-content-center align-items-center library-paginator mt-2 mb-2">
                        <ul class="pagination paginator mr-1" />
                        <input style="width: initial;" min="0" max="999" class="page_size form-control" type="number" value="<%- library_page_size %>" />
                        <span class="text-muted ml-1 paginator-text" />
                    </div>
                </div>
            </div>`
        );
    },

    templatePaginator: function () {
        return _.template(
            `
                        <% if ( ( show_page - 1 ) > 0 ) { %>
                            <% if ( ( show_page - 1 ) > page_count ) { %> <!-- we are on higher page than total page count -->
                               <li class="page-item">
                                    <a class="page-link" href="#page/1">
                                        <span class="fa fa-angle-double-left"></span>
                                    </a>
                                </li>
                                <li class="page-item disabled">
                                    <a class="page-link" href="#page/<% print( show_page ) %>">
                                        <% print( show_page - 1 ) %>
                                    </a>
                                </li>
                            <% } else { %>
                                <li class="page-item">
                                    <a class="page-link" href="#page/1">
                                        <span class="fa fa-angle-double-left"></span>
                                    </a>
                                </li>
                                <li class="page-item">
                                    <a class="page-link" href="#page/<% print( show_page - 1 ) %>">
                                        <% print( show_page - 1 ) %>
                                    </a>
                                </li>
                            <% } %>
                        <% } else { %> <!-- we are on the first page -->
                           <li class="page-item disabled">
                                <a class="page-link" href="#page/1">
                                    <span class="fa fa-angle-double-left"></span>
                                </a>
                            </li>
                            <li class="page-item disabled">
                                <a class="page-link" href="#page/<% print( show_page ) %>">
                                    <% print( show_page - 1 ) %>
                                </a>
                            </li>
                        <% } %>
                            <li class="page-item active">
                                <a class="page-link" href="#page/<% print( show_page ) %>">
                                    <% print( show_page ) %>
                                </a>
                            </li>
                        <% if ( ( show_page ) < page_count ) { %>
                            <li class="page-item">
                                <a class="page-link" href="#page/<% print( show_page + 1 ) %>">
                                    <% print( show_page + 1 ) %>
                                </a>
                            </li>
                            <li class="page-item">
                                <a class="page-link" href="#page/<% print( page_count ) %>">
                                    <span class="fa fa-angle-double-right"></span>
                                </a>
                            </li>
                        <% } else { %>
                            <li class="page-item disabled">
                                <a class="page-link" href="#page/<% print( show_page  ) %>">
                                    <% print( show_page + 1 ) %>
                                </a>
                            </li>
                            <li class="page-item disabled">
                                <a class="page-link" href="#page/<% print( page_count ) %>">
                                    <span class="fa fa-angle-double-right"></span>
                                </a>
                            </li>
                        <% } %>
                `
        );
    },
    templatePaginatorText: function () {
        return _.template(`per page, <%- total_libraries_count %> total`);
    },
});

export default {
    LibraryToolbarView: LibraryToolbarView,
};
