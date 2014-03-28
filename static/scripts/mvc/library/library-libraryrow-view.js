// dependencies
define([
    "galaxy.masthead", 
    "utils/utils",
    "libs/toastr",
    "mvc/library/library-model"], 
function(mod_masthead, 
         mod_utils, 
         mod_toastr,
         mod_library_model) {

// galaxy library row view
var LibraryRowView = Backbone.View.extend({
  
  initialize : function(library){
    this.render(library);
  },

  render: function(library){
    var tmpl = this.templateRow();
    this.setElement(tmpl({library:library}));
    this.set_up_visual_features(library);
  },

  set_up_visual_features: function(library){
    if (library.get('deleted') === true){
      this.$el.addClass('active');
    }
    this.$el.show();
  },

  templateRow: function() {
    tmpl_array = [];

    tmpl_array.push('           <tr style="display:none;" data-id="<%- library.get("id") %>">');
    tmpl_array.push('               <td><a href="#folders/<%- library.get("root_folder_id") %>"><%- library.get("name") %></a></td>');
    tmpl_array.push('               <td><%= _.escape(library.get("description")) %></td>');
    tmpl_array.push('               <td><%= _.escape(library.get("synopsis")) %></td>');
    tmpl_array.push('               <td class="right-center">');
    tmpl_array.push('                   <% if(library.get("deleted") === true) { %>');
    tmpl_array.push('                       <span data-toggle="tooltip" data-placement="top" title="Marked deleted" style="color:grey;" class="fa fa-ban fa-lg deleted_lib_ico"> </span>');
    tmpl_array.push('                   <% } else if(library.get("public") === true) { %>');
    tmpl_array.push('                     <span data-toggle="tooltip" data-placement="top" title="Public" style="color:grey;" class="fa fa-globe fa-lg public_lib_ico"> </span>');
    tmpl_array.push('                   <% }%>');
    tmpl_array.push('                   <button data-toggle="tooltip" data-placement="top" title="Upload to library" class="primary-button btn-xs upload_library_btn" type="button"><span class="fa fa-upload"></span></button>');
    tmpl_array.push('                   <button data-toggle="tooltip" data-placement="top" title="Modify library" class="primary-button btn-xs edit_library_btn" type="button"><span class="fa fa-pencil"></span></button>');
    tmpl_array.push('                   <button data-toggle="tooltip" data-placement="top" title="Modify permissions" class="primary-button btn-xs permission_library_btn" type="button"><span class="fa fa-group"></span></button>');
    tmpl_array.push('                   <button data-toggle="tooltip" data-placement="top" title="Save changes" class="primary-button btn-xs save_library_btn" type="button" style="display:none;"><span class="fa fa-floppy-o"> Save</span></button>');
    tmpl_array.push('                   <button data-toggle="tooltip" data-placement="top" title="Discard changes" class="primary-button btn-xs cancel_library_btn" type="button" style="display:none;"><span class="fa fa-times"> Cancel</span></button>');
    tmpl_array.push('                   <button data-toggle="tooltip" data-placement="top" title="Delete library (can be undeleted later)" class="primary-button btn-xs delete_library_btn" type="button" style="display:none;"><span class="fa fa-trash-o"> Delete</span></button>');
    tmpl_array.push('                   <button data-toggle="tooltip" data-placement="top" title="Undelete library" class="primary-button btn-xs undelete_library_btn" type="button" style="display:none;"><span class="fa fa-unlock"> Undelete</span></button>');
    tmpl_array.push('               </td>');
    tmpl_array.push('           </tr>');

    return _.template(tmpl_array.join('')); 
  }
   
});

  // return
return {
    LibraryRowView: LibraryRowView
};

});
