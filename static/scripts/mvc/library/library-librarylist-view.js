define([
    "galaxy.masthead",
    "mvc/base-mvc",
    "utils/utils",
    "libs/toastr",
    "mvc/library/library-model",
    "mvc/library/library-libraryrow-view" 
], function(
    mod_masthead,
    mod_baseMVC,
    mod_utils,
    mod_toastr,
    mod_library_model,
    mod_library_libraryrow_view
){

var LibraryListView = Backbone.View.extend({
    el: '#libraries_element',

    events: {
        'click .sort-libraries-link'    : 'sort_clicked'
    },

    defaults: {
        page_count: null,
        show_page: null
    },

    /**
     * Initialize and fetch the libraries from server. 
     * Async render afterwards.
     * @param  {object} options an object with options
     */
    initialize : function( options ){
        this.options = _.defaults( this.options || {}, this.defaults, options );
        var that = this;
        this.modal = null;
        // map of library model ids to library views = cache
        this.rowViews = {};
        // collection of {Item}s
        this.collection = new mod_library_model.Libraries();
        this.collection.fetch({
          success: function(){
            that.render();
          },
          error: function( model, response ){
              if ( typeof response.responseJSON !== "undefined" ){
                mod_toastr.error( response.responseJSON.err_msg );
              } else {
                mod_toastr.error( 'An error ocurred.' );
              }
          }
        });
    },

    /** 
     * Render the libraries table either from the object's own collection, 
     * or from a given array of library models,
     * or render an empty list in case no data is given. 
     */
    render: function ( options ) {
        this.options = _.extend( this.options, options );
        var template = this.templateLibraryList();
        var libraries_to_render = null;
        var models = null;
        $( ".tooltip" ).hide();
        if ( typeof options !== 'undefined' ){
            models = typeof options.models !== 'undefined' ? options.models : null;
        }
        if ( this.collection !== null && models === null ){
            this.sortLibraries();
            if ( Galaxy.libraries.preferences.get( 'with_deleted' ) ){
              libraries_to_render = this.collection.models;
            } else {
              libraries_to_render = this.collection.where( { deleted: false } );
            }
        } else if ( models !== null ){
            libraries_to_render = models;
        } else {
            libraries_to_render = [];
        }
        // pagination
        if ( this.options.show_page === null || this.options.show_page < 1 ){
            this.options.show_page = 1;
        }
        this.options.total_libraries_count = libraries_to_render.length
        var page_start = ( Galaxy.libraries.preferences.get( 'library_page_size' ) * ( this.options.show_page - 1 ) );
        this.options.page_count = Math.ceil( this.options.total_libraries_count / Galaxy.libraries.preferences.get( 'library_page_size' ) );
        if ( this.options.total_libraries_count > 0 && ( page_start < this.options.total_libraries_count ) ){
            libraries_to_render = libraries_to_render.slice( page_start, page_start + Galaxy.libraries.preferences.get( 'library_page_size' ) );
            this.options.libraries_shown = libraries_to_render.length;
            // User requests page with no libraries
            if ( Galaxy.libraries.preferences.get( 'library_page_size' ) * this.options.show_page > ( this.options.total_libraries_count + Galaxy.libraries.preferences.get( 'library_page_size' ) ) ){
                libraries_to_render = [];
            }
            this.$el.html( template({
                length: 1,
                order: Galaxy.libraries.preferences.get( 'sort_order' )
            }));
            Galaxy.libraries.libraryToolbarView.renderPaginator( this.options );
            this.renderRows( libraries_to_render );
        } else {
            this.$el.html( template({
                length: 0,
                order: Galaxy.libraries.preferences.get( 'sort_order' )
            }));
            Galaxy.libraries.libraryToolbarView.renderPaginator( this.options );
        }
        $( "#center [data-toggle]" ).tooltip();
        $( "#center" ).css( 'overflow','auto' );
    },

    /** 
     * Render all given models as rows in the library list
     * @param  {array} libraries_to_render array of library models to render
     */
    renderRows: function( libraries_to_render ){
        for ( var i = 0; i < libraries_to_render.length; i++ ) {
          var library = libraries_to_render[i];
          // search whether we have the item cached
          var cachedView = _.findWhere( this.rowViews, { id: library.get( 'id' ) } );
          if ( cachedView !== undefined && this instanceof Backbone.View ){
            cachedView.delegateEvents();
            this.$el.find( '#library_list_body' ).append( cachedView.el );
          } else {
            this.renderOne( { library: library } )
          }
        }
    },

    /**
     * Create a view for the given model and add it to the libraries view.
     * @param {Library} model of the view that will be rendered
     */
    renderOne: function( options ){
        var library = options.library;
        var rowView = new mod_library_libraryrow_view.LibraryRowView( library );
        this.$el.find( '#library_list_body' ).append( rowView.el );
        // save new rowView to cache
        this.rowViews[ library.get( 'id' ) ] = rowView;
    },

    /**
     * Table heading was clicked, update sorting preferences and re-render.
     * @return {[type]} [description]
     */
    sort_clicked : function(){
        if (Galaxy.libraries.preferences.get('sort_order') === 'asc'){
            Galaxy.libraries.preferences.set({'sort_order': 'desc'});
        } else {
            Galaxy.libraries.preferences.set({'sort_order': 'asc'});
        }
        this.render();
    },

    /**
     * Sort the underlying collection according to the parameters received.
     * Currently supports only sorting by name. 
     */
    sortLibraries: function(){
        if (Galaxy.libraries.preferences.get('sort_by') === 'name'){
            if (Galaxy.libraries.preferences.get('sort_order') === 'asc'){
                this.collection.sortByNameAsc();
            } else if (Galaxy.libraries.preferences.get('sort_order') === 'desc'){
                this.collection.sortByNameDesc();
            }
        }
    },

    redirectToHome: function(){
        window.location = '../';
    },
    redirectToLogin: function(){
        window.location = '/user/login';
    },

// MMMMMMMMMMMMMMMMMM
// === TEMPLATES ====
// MMMMMMMMMMMMMMMMMM

    templateLibraryList: function(){
        tmpl_array = [];

        tmpl_array.push('<div class="library_container table-responsive">');
        tmpl_array.push('<% if(length === 0) { %>');
        tmpl_array.push('<div>There are no libraries visible to you here. If you expected some to show up please consult the <a href="https://wiki.galaxyproject.org/Admin/DataLibraries/LibrarySecurity" target="_blank">library security wikipage</a> or visit the <a href="https://biostar.usegalaxy.org/" target="_blank">Galaxy support site</a>.</div>');
        tmpl_array.push('<% } else{ %>');
        tmpl_array.push('<table class="grid table table-condensed">');
        tmpl_array.push('   <thead>');
        tmpl_array.push('     <th style="width:30%;"><a class="sort-libraries-link" title="Click to reverse order" href="#">name</a> <span title="Sorted alphabetically" class="fa fa-sort-alpha-<%- order %>"></span></th>');
        tmpl_array.push('     <th style="width:22%;">description</th>');
        tmpl_array.push('     <th style="width:22%;">synopsis</th> ');
        tmpl_array.push('     <th style="width:26%;"></th>');
        tmpl_array.push('   </thead>');
        tmpl_array.push('   <tbody id="library_list_body">');
        // library item views will attach here
        tmpl_array.push('   </tbody>');
        tmpl_array.push('</table>');
        tmpl_array.push('<% }%>');
        tmpl_array.push('</div>');

        return _.template(tmpl_array.join(''));
    },

});

return {
    LibraryListView: LibraryListView
};

});
