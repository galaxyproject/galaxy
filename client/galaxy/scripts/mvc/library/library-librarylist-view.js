define([
    "layout/masthead",
    "mvc/base-mvc",
    "utils/utils",
    "libs/toastr",
    "mvc/library/library-model",
    "mvc/library/library-libraryrow-view",
    "libs/underscore"
], function(
    mod_masthead,
    mod_baseMVC,
    mod_utils,
    mod_toastr,
    mod_library_model,
    mod_library_libraryrow_view,
    _
){

var LibraryListView = Backbone.View.extend({
    el: '#libraries_element',

    events: {
        'click .sort-libraries-link'    : 'sort_clicked'
    },

    defaults: {
        page_count: null,
        show_page: null,
        all_fetched: false
    },

    /**
     * Initialize and fetch the libraries from server.
     * Async render afterwards.
     * @param  {object} options an object with options
     */
    initialize : function( options ){
        this.options = _.defaults( this.options || {}, options, this.defaults );
        var that = this;
        this.modal = null;
        // collection of {Item}s
        this.collection = new mod_library_model.Libraries();
        this.collection.url = this.collection.urlRoot + '?deleted=false';
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
        this.setElement('#libraries_element');
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
            if ( Galaxy.libraries.preferences.get( 'with_deleted' ) ){
                libraries_to_render = models;
            } else {
                var is_deleted = function(model){ return model.get('deleted') === false; }
                libraries_to_render = _.filter(models, is_deleted );
            }
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
                order: Galaxy.libraries.preferences.get( 'sort_order' ),
                search_term: Galaxy.libraries.libraryToolbarView.options.search_term
            }));
            Galaxy.libraries.libraryToolbarView.renderPaginator( this.options );
            this.renderRows( libraries_to_render );
        } else {
            this.$el.html( template({
                length: 0,
                order: Galaxy.libraries.preferences.get( 'sort_order' ),
                search_term: Galaxy.libraries.libraryToolbarView.options.search_term
            }));
            Galaxy.libraries.libraryToolbarView.renderPaginator( this.options );
        }
        $( "#center [data-toggle]" ).tooltip();
        $( "#center" ).css( 'overflow','auto' );
    },

    fetchDeleted: function(){
      if (this.options.all_fetched){
        this.render();
      } else{
        var that = this;
        this.collection.url = this.collection.urlRoot + '?deleted=true';
        this.collection.fetch({
          remove: false,
          success: function(){
            that.options.all_fetched = true;
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
      }
    },

    /**
     * Render all given models as rows in the library list
     * @param  {array} libraries_to_render array of library models to render
     */
    renderRows: function( libraries_to_render ){
        for ( var i = 0; i < libraries_to_render.length; i++ ) {
          var library = libraries_to_render[i];
            this.renderOne( { library: library } );
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

    /**
     * In case the search_term is not empty perform the search and render
     * the result. Render all visible libraries otherwise.
     * @param  {string} search_term string to search for
     */
    searchLibraries: function(search_term){
      var trimmed_term = $.trim(search_term);
      if (trimmed_term !== ''){
        var results = null
        results = this.collection.search( search_term );
        this.options.searching = true;
        this.render({'models': results});
      } else {
        this.options.searching = false;
        this.render();
      }
    },

// MMMMMMMMMMMMMMMMMM
// === TEMPLATES ====
// MMMMMMMMMMMMMMMMMM

    templateLibraryList: function(){
      return _.template([
      '<div class="library_container table-responsive">',
        '<% if(length === 0) { %>',
          '<% if(search_term.length > 0) { %>',
            '<div>',
              'There are no libraries matching your search. Try different keyword.',
            '</div>',
          '<% } else{ %>',
            '<div>',
              'There are no libraries visible to you here. If you expected some to show up please consult the',
              ' <a href="https://wiki.galaxyproject.org/Admin/DataLibraries/LibrarySecurity" target="_blank">library security wikipage</a>',
              ' or visit the <a href="https://biostar.usegalaxy.org/" target="_blank">Galaxy support site</a>.',
            '</div>',
          '<% }%>',
        '<% } else{ %>',
          '<table class="grid table table-condensed">',
            '<thead>',
              '<th style="width:30%;">',
                '<a class="sort-libraries-link" title="Click to reverse order" href="#">',
                  'name',
                '</a>',
                '<span title="Sorted alphabetically" class="fa fa-sort-alpha-<%- order %>"/>',
              '</th>',
              '<th style="width:22%;">description</th>',
              '<th style="width:22%;">synopsis</th> ',
              '<th style="width:26%;"></th>',
            '</thead>',
            '<tbody id="library_list_body">',
            // library item views will attach here
            '</tbody>',
          '</table>',
        '<% }%>',
      '</div>'
      ].join(''));
    }

});

return {
    LibraryListView: LibraryListView
};

});
