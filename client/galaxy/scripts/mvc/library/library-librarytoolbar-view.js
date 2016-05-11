define([
  "libs/toastr",
  "mvc/library/library-model"],
function(mod_toastr,
         mod_library_model) {
/**
 * This view represents the top part of the library page.
 * It contains the tool bar with controls.
 */
var LibraryToolbarView = Backbone.View.extend({
  el: '#center',

  defaults: {
    search_term: ''
  },

  events: {
    'click #create_new_library_btn' : 'createLibraryFromModal',
    'click #include_deleted_chk'    : 'includeDeletedChecked',
    'click #lib_page_size_prompt'   : 'showPageSizePrompt',
    'keyup .library-search-input'   : 'searchLibraries'
  },

  initialize: function( options ){
    this.options = _.defaults( this.options || {}, options, this.defaults );
    this.render();
  },

  render: function(){
    var toolbar_template = this.templateToolBar();
    var is_admin = false;
    var is_anonym = true;
    if ( Galaxy.user ){
      is_admin = Galaxy.user.isAdmin();
      is_anonym = Galaxy.user.isAnonymous();
    }
    this.$el.html(toolbar_template( { admin_user: is_admin, anon_user: is_anonym } ) );
    if ( is_admin ){
      this.$el.find( '#include_deleted_chk' )[0].checked = Galaxy.libraries.preferences.get( 'with_deleted' );
    }
  },

  /**
   * Renders the element that shows pages into its div within the toolbar.
   */
  renderPaginator: function( options ){
    this.options = _.extend( this.options, options );
    var paginator_template = this.templatePaginator();
    this.$el.find( '#library_paginator' ).html( paginator_template({
      show_page: parseInt( this.options.show_page ),
      page_count: parseInt( this.options.page_count ),
      total_libraries_count: this.options.total_libraries_count,
      libraries_shown: this.options.libraries_shown
    }));
  },

  /**
   * User clicked on 'New library' button. Show modal to
   * satisfy the wish.
   */
  createLibraryFromModal : function (event){
    event.preventDefault();
    event.stopPropagation();
    var self = this;
    this.modal = Galaxy.modal;
    this.modal.show({
      closing_events  : true,
      title           : 'Create New Library',
      body            : this.templateNewLibraryInModal(),
      buttons         : {
        'Create'      : function() { self.createNewLibrary(); },
        'Close'       : function() { self.modal.hide(); }
      }
    });
  },

  /**
   * Create the new library using the API asynchronously.
   */
  createNewLibrary: function(){
    var libraryDetails = this.serializeNewLibrary();
    if (this.validateNewLibrary(libraryDetails)){
      var library = new mod_library_model.Library();
      var self = this;
      library.save(libraryDetails, {
        success: function (library) {
          Galaxy.libraries.libraryListView.collection.add(library);
          self.modal.hide();
          self.clearLibraryModal();
          Galaxy.libraries.libraryListView.render();
          mod_toastr.success('Library created.');
        },
        error: function(model, response){
          if (typeof response.responseJSON !== "undefined"){
            mod_toastr.error(response.responseJSON.err_msg);
          } else {
            mod_toastr.error('An error occured.');
          }
        }
      });
    } else {
      mod_toastr.error('Library\'s name is missing.');
    }
    return false;
  },

  /**
   * Show user the propmpt to change the number of libs shown on page.
   */
  showPageSizePrompt: function(){
    var library_page_size = prompt( 'How many libraries per page do you want to see?', Galaxy.libraries.preferences.get( 'library_page_size' ) );
    if ( ( library_page_size != null ) && ( library_page_size == parseInt( library_page_size ) ) ) {
      Galaxy.libraries.preferences.set( { 'library_page_size': parseInt( library_page_size ) } );
      Galaxy.libraries.libraryListView.render( { show_page: 1 } );
    }
  },

  /**
   * Clear the library modal once it is saved.
   */
  clearLibraryModal : function(){
    $("input[name='Name']").val('');
    $("input[name='Description']").val('');
    $("input[name='Synopsis']").val('');
  },

  /**
   * Prepare new library variables to be submitted to API.
   */
  serializeNewLibrary : function(){
    return {
      name: $("input[name='Name']").val(),
      description: $("input[name='Description']").val(),
      synopsis: $("input[name='Synopsis']").val()
    };
  },

  /**
   * Check whether entered values are valid.
   */
  validateNewLibrary: function( libraryDetails ){
      return libraryDetails.name !== '';
  },

  /**
   * Include or exclude deleted libraries in the view.
   */
  includeDeletedChecked: function( event ){
    if (event.target.checked){
        Galaxy.libraries.preferences.set( { 'with_deleted': true } );
        Galaxy.libraries.libraryListView.fetchDeleted();
    } else{
        Galaxy.libraries.preferences.set( { 'with_deleted': false } );
        Galaxy.libraries.libraryListView.render();
    }
  },

  /**
   * Take the contents of the search field and send it to the list view
   * to query the collection of libraries.
   */
  searchLibraries: function(event){
    var search_term = $(".library-search-input").val();
    this.options.search_term = search_term;
    Galaxy.libraries.libraryListView.searchLibraries(search_term);
  },

  templateToolBar: function(){
    return _.template([
      '<div class="library_style_container">',
        '<div id="toolbar_form">',
          '<div id="library_toolbar">',
            '<form class="form-inline" role="form">',
              '<span><strong><a href="#" title="Go to first page">DATA LIBRARIES</a></strong></span>',
              '<span id="library_paginator" class="library-paginator">',
              // paginator will append here
              '</span>',
              '<div class="form-group toolbar-item">',
                '<input type="text" class="form-control library-search-input" placeholder="Search" size="30">',
              '</div>',
              // only admins see the following
              '<% if(admin_user === true) { %>',
                  '<div class="checkbox toolbar-item" style="height: 20px;">',
                    '<label>',
                      '<input id="include_deleted_chk" type="checkbox">',
                        '&nbsp;include deleted ',
                      '</input>',
                    '</label>',
                  '</div>',
                  '<span class="toolbar-item" data-toggle="tooltip" data-placement="top" title="Create New Library">',
                    '<button id="create_new_library_btn" class="primary-button btn-xs" type="button"><span class="fa fa-plus"></span> New Library</button>',
                '</span>',
              '<% } %>',
              '<span class="help-button" data-toggle="tooltip" data-placement="top" title="Visit Libraries Wiki">',
                '<a href="https://wiki.galaxyproject.org/DataLibraries/screen/ListOfLibraries" target="_blank">',
                  '<button class="primary-button" type="button"><span class="fa fa-question-circle"></span> Help</button>',
                '</a>',
              '</span>',
            '</form>',
          '</div>',
        '</div>',
        '<div id="libraries_element">',
        // table with libraries will append here
        '</div>',
      '</div>'
    ].join(''));
  },

  templatePaginator: function(){
    return _.template([
    '<ul class="pagination pagination-sm">',
      '<% if ( ( show_page - 1 ) > 0 ) { %>',
      '<% if ( ( show_page - 1 ) > page_count ) { %>', // we are on higher page than total page count
        '<li><a href="#page/1"><span class="fa fa-angle-double-left"></span></a></li>',
        '<li class="disabled"><a href="#page/<% print( show_page ) %>"><% print( show_page - 1 ) %></a></li>',
      '<% } else { %>',
        '<li><a href="#page/1"><span class="fa fa-angle-double-left"></span></a></li>',
        '<li><a href="#page/<% print( show_page - 1 ) %>"><% print( show_page - 1 ) %></a></li>',
      '<% } %>',
      '<% } else { %>', // we are on the first page
        '<li class="disabled"><a href="#page/1"><span class="fa fa-angle-double-left"></span></a></li>',
        '<li class="disabled"><a href="#page/<% print( show_page ) %>"><% print( show_page - 1 ) %></a></li>',
      '<% } %>',
        '<li class="active">',
          '<a href="#page/<% print( show_page ) %>"><% print( show_page ) %></a>',
        '</li>',
      '<% if ( ( show_page ) < page_count ) { %>',
        '<li><a href="#page/<% print( show_page + 1 ) %>"><% print( show_page + 1 ) %></a></li>',
        '<li><a href="#page/<% print( page_count ) %>"><span class="fa fa-angle-double-right"></span></a></li>',
      '<% } else { %>',
        '<li class="disabled"><a href="#page/<% print( show_page  ) %>"><% print( show_page + 1 ) %></a></li>',
        '<li class="disabled"><a href="#page/<% print( page_count ) %>"><span class="fa fa-angle-double-right"></span></a></li>',
      '<% } %>',
    '</ul>',
    '<span id="lib_page_size_prompt">',
      ' showing <a data-toggle="tooltip" data-placement="top" title="Click to change the number of libraries on page"><%- libraries_shown %></a> of <%- total_libraries_count %> libraries',
    '</span>'
    ].join(''));
  },

  templateNewLibraryInModal: function(){
    return _.template([
      '<div id="new_library_modal">',
        '<form>',
          '<input type="text" name="Name" value="" placeholder="Name" autofocus>',
          '<input type="text" name="Description" value="" placeholder="Description">',
          '<input type="text" name="Synopsis" value="" placeholder="Synopsis">',
        '</form>',
      '</div>'
    ].join(''));
  }
});

return {
  LibraryToolbarView: LibraryToolbarView
};

});
