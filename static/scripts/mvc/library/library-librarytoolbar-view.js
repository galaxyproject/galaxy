define([
  "libs/toastr",
  "mvc/library/library-model"],
function(mod_toastr,
         mod_library_model) {
/**
 * This view represents the top part of the library page.
 * It contains the tool bar with buttons.
 */
var LibraryToolbarView = Backbone.View.extend({
  el: '#center',

  events: {
    'click #create_new_library_btn' : 'showLibraryModal',
    'click #include_deleted_chk'    : 'includeDeletedChecked',
    'click #page_size_prompt'       : 'showPageSizePrompt'
  },

  initialize: function( options ){
    this.options = _.defaults( this.options || {}, options );
    this.render();
  },

  render: function(){
    var toolbar_template = this.templateToolBar();
    var is_admin = false;
    var is_anonym = true;
    if ( Galaxy.currUser ){
      is_admin = Galaxy.currUser.isAdmin();
      is_anonym = Galaxy.currUser.isAnonymous();
    }
    this.$el.html(toolbar_template( { admin_user: is_admin, anon_user: is_anonym } ) );
    if ( is_admin ){
      this.$el.find( '#include_deleted_chk' )[0].checked = Galaxy.libraries.preferences.get( 'with_deleted' );
    }
  },

  /**
   * Called from LibraryListView when needed.
   * @param  {object} options common options
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

  showLibraryModal : function (event){
      event.preventDefault();
      event.stopPropagation();
      var self = this;
      this.modal = Galaxy.modal;
      this.modal.show({
          closing_events  : true,
          title           : 'Create New Library',
          body            : this.templateNewLibraryInModal(),
          buttons         : {
              'Create'    : function() { self.createNewLibrary(); },
              'Close'     : function() { self.modal.hide(); }
          }
      });
  },

  createNewLibrary: function(){
      var libraryDetails = this.serializeNewLibrary();
      if (this.valdiateNewLibrary(libraryDetails)){
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

  showPageSizePrompt: function(){
    var library_page_size = prompt( 'How many libraries per page do you want to see?', Galaxy.libraries.preferences.get( 'library_page_size' ) );
    if ( ( library_page_size != null ) && ( library_page_size == parseInt( library_page_size ) ) ) {
        Galaxy.libraries.preferences.set( { 'library_page_size': parseInt( library_page_size ) } );
        Galaxy.libraries.libraryListView.render( { show_page: 1 } );
    }
  },

  // clear the library modal once saved
  clearLibraryModal : function(){
      $("input[name='Name']").val('');
      $("input[name='Description']").val('');
      $("input[name='Synopsis']").val('');
  },

  serializeNewLibrary : function(){
      return {
          name: $("input[name='Name']").val(),
          description: $("input[name='Description']").val(),
          synopsis: $("input[name='Synopsis']").val()
      };
  },

  valdiateNewLibrary: function( libraryDetails ){
      return libraryDetails.name !== '';
  },

  /**
   * Include or exclude deleted libraries in the view.
   * @param  {object} event common event
   */
  includeDeletedChecked: function( event ){
    if (event.target.checked){
        Galaxy.libraries.preferences.set( { 'with_deleted': true } );
        Galaxy.libraries.libraryListView.render();
    } else{
        Galaxy.libraries.preferences.set( { 'with_deleted': false } );
        Galaxy.libraries.libraryListView.render();
    }
  },

  templateToolBar: function(){
    tmpl_array = [];


    tmpl_array.push('<div class="library_style_container">');
    tmpl_array.push('  <div id="toolbar_form">');
    tmpl_array.push('      <div id="library_toolbar">');
    tmpl_array.push('      <form class="form-inline" role="form">');
    tmpl_array.push('          <span><strong><a href="#" title="Go to first page">DATA LIBRARIES</a></strong></span>');
    tmpl_array.push('          <% if(admin_user === true) { %>');
    tmpl_array.push('              <div class="checkbox" style="height: 20px;">');
    tmpl_array.push('                  <label>');
    tmpl_array.push('                      <input id="include_deleted_chk" type="checkbox"> include deleted </input>');
    tmpl_array.push('                   </label>');
    tmpl_array.push('              </div>');
    tmpl_array.push('              <span data-toggle="tooltip" data-placement="top" title="Create New Library"><button id="create_new_library_btn" class="primary-button btn-xs" type="button"><span class="fa fa-plus"></span> New Library</button></span>');
    tmpl_array.push('          <% } %>');
    tmpl_array.push('          <span class="help-button" data-toggle="tooltip" data-placement="top" title="Visit Libraries Wiki"><a href="https://wiki.galaxyproject.org/DataLibraries/screen/ListOfLibraries" target="_blank"><button class="primary-button" type="button"><span class="fa fa-question-circle"></span> Help</button></a></span>');
    tmpl_array.push('          <span id="library_paginator" class="library-paginator">');
    // paginator will append here
    tmpl_array.push('          </span>');
    tmpl_array.push('      </form>');
    tmpl_array.push('      </div>');
    tmpl_array.push('  </div>');
    tmpl_array.push('  <div id="libraries_element">');
    // table with libraries will append here
    tmpl_array.push('  </div>');
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  },

  templatePaginator: function(){
    tmpl_array = [];

    tmpl_array.push('   <ul class="pagination pagination-sm">');
    tmpl_array.push('       <% if ( ( show_page - 1 ) > 0 ) { %>');
    tmpl_array.push('           <% if ( ( show_page - 1 ) > page_count ) { %>'); // we are on higher page than total page count
    tmpl_array.push('               <li><a href="#page/1"><span class="fa fa-angle-double-left"></span></a></li>');
    tmpl_array.push('               <li class="disabled"><a href="#page/<% print( show_page ) %>"><% print( show_page - 1 ) %></a></li>');
    tmpl_array.push('           <% } else { %>');
    tmpl_array.push('               <li><a href="#page/1"><span class="fa fa-angle-double-left"></span></a></li>');
    tmpl_array.push('               <li><a href="#page/<% print( show_page - 1 ) %>"><% print( show_page - 1 ) %></a></li>');
    tmpl_array.push('           <% } %>');
    tmpl_array.push('       <% } else { %>'); // we are on the first page
    tmpl_array.push('           <li class="disabled"><a href="#page/1"><span class="fa fa-angle-double-left"></span></a></li>');
    tmpl_array.push('           <li class="disabled"><a href="#page/<% print( show_page ) %>"><% print( show_page - 1 ) %></a></li>');
    tmpl_array.push('       <% } %>');
    tmpl_array.push('       <li class="active">');
    tmpl_array.push('       <a href="#page/<% print( show_page ) %>"><% print( show_page ) %></a>');
    tmpl_array.push('       </li>');
    tmpl_array.push('       <% if ( ( show_page ) < page_count ) { %>');
    tmpl_array.push('           <li><a href="#page/<% print( show_page + 1 ) %>"><% print( show_page + 1 ) %></a></li>');
    tmpl_array.push('           <li><a href="#page/<% print( page_count ) %>"><span class="fa fa-angle-double-right"></span></a></li>');
    tmpl_array.push('       <% } else { %>');
    tmpl_array.push('           <li class="disabled"><a href="#page/<% print( show_page  ) %>"><% print( show_page + 1 ) %></a></li>');
    tmpl_array.push('           <li class="disabled"><a href="#page/<% print( page_count ) %>"><span class="fa fa-angle-double-right"></span></a></li>');
    tmpl_array.push('       <% } %>');
    tmpl_array.push('   </ul>');
    tmpl_array.push('   <span>');
    tmpl_array.push('       showing <a data-toggle="tooltip" data-placement="top" title="Click to change the number of libraries on page" id="page_size_prompt"><%- libraries_shown %></a> of <%- total_libraries_count %> libraries');
    tmpl_array.push('   </span>');

    return _.template(tmpl_array.join(''));
  },

  templateNewLibraryInModal: function(){
      tmpl_array = [];

      tmpl_array.push('<div id="new_library_modal">');
      tmpl_array.push('   <form>');
      tmpl_array.push('       <input type="text" name="Name" value="" placeholder="Name">');
      tmpl_array.push('       <input type="text" name="Description" value="" placeholder="Description">');
      tmpl_array.push('       <input type="text" name="Synopsis" value="" placeholder="Synopsis">');
      tmpl_array.push('   </form>');
      tmpl_array.push('</div>');

      return tmpl_array.join('');
  }
});

return {
    LibraryToolbarView: LibraryToolbarView
};

});
