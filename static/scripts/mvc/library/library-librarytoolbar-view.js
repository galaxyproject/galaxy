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
    'click #create_new_library_btn' : 'show_library_modal',
    'click #include_deleted_chk'    : 'check_include_deleted'
  },

  initialize: function(){
    this.render();
  },

  render: function(){
    var toolbar_template = this.templateToolBar();
    var is_admin = false;
    var is_anonym = true;
    if (Galaxy.currUser){
      is_admin = Galaxy.currUser.isAdmin();
      is_anonym = Galaxy.currUser.isAnonymous();
    }
    this.$el.html(toolbar_template({admin_user: is_admin, anon_user: is_anonym}));
    if (is_admin){
      this.$el.find('#include_deleted_chk')[0].checked = Galaxy.libraries.preferences.get('with_deleted');
    }
  },

  show_library_modal : function (event){
      event.preventDefault();
      event.stopPropagation();

      // create modal
      var self = this;
      this.modal = Galaxy.modal;
      this.modal.show({
          closing_events  : true,
          title           : 'Create New Library',
          body            : this.templateNewLibraryInModal(),
          buttons         : {
              'Create'    : function() {self.create_new_library_event();},
              'Close'     : function() {self.modal.hide();}
          }
      });
  },

  create_new_library_event: function(){
      var libraryDetails = this.serialize_new_library();
      if (this.validate_new_library(libraryDetails)){
          var library = new mod_library_model.Library();
          var self = this;
          library.save(libraryDetails, {
            success: function (library) {
              Galaxy.libraries.libraryListView.collection.add(library);
              self.modal.hide();
              self.clear_library_modal();
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

  // clear the library modal once saved
  clear_library_modal : function(){
      $("input[name='Name']").val('');
      $("input[name='Description']").val('');
      $("input[name='Synopsis']").val('');
  },

  // serialize data from the new library form
  serialize_new_library : function(){
      return {
          name: $("input[name='Name']").val(),
          description: $("input[name='Description']").val(),
          synopsis: $("input[name='Synopsis']").val()
      };
  },

  // validate new library info
  validate_new_library: function(libraryDetails){
      return libraryDetails.name !== '';
  },

  // include or exclude deleted libraries from the view
  check_include_deleted: function(event){
    if (event.target.checked){
        Galaxy.libraries.preferences.set({'with_deleted': true});
        Galaxy.libraries.libraryListView.render();
    } else{
        Galaxy.libraries.preferences.set({'with_deleted': false});
        Galaxy.libraries.libraryListView.render();
    }
  },

  templateToolBar: function(){
    tmpl_array = [];

    tmpl_array.push('<div class="library_style_container">');
    // TOOLBAR
    tmpl_array.push('  <div id="toolbar_form">');
    tmpl_array.push('      <div id="library_toolbar">');
    tmpl_array.push('       <span><strong>DATA LIBRARIES</strong></span>');
    tmpl_array.push('           <% if(admin_user === true) { %>');
    tmpl_array.push('               <span data-toggle="tooltip" data-placement="top" title="Include deleted libraries"> | <input id="include_deleted_chk" style="margin: 0;" type="checkbox"> include deleted |</input></span>');
    tmpl_array.push('               <span data-toggle="tooltip" data-placement="top" title="Create New Library"><button id="create_new_library_btn" class="primary-button btn-xs" type="button"><span class="fa fa-plus"></span> New Library</button></span>');
    tmpl_array.push('           <% } %>');
    tmpl_array.push('           <span class="help-button" data-toggle="tooltip" data-placement="top" title="Visit Libraries Wiki"><a href="https://wiki.galaxyproject.org/DataLibraries/screen/ListOfLibraries" target="_blank"><button class="primary-button btn-xs" type="button"><span class="fa fa-question-circle"></span> Help</button></a></span>');
    tmpl_array.push('       </div>');

    tmpl_array.push('  <div>');
    tmpl_array.push('  ');
    tmpl_array.push('  </div>');

    tmpl_array.push('  </div>');
    tmpl_array.push('  <div id="libraries_element">');
    // table with libraries will append here
    tmpl_array.push('  </div>');
    tmpl_array.push('</div>');

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
