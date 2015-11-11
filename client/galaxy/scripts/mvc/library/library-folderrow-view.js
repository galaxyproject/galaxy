define([
    "galaxy.masthead",
    "utils/utils",
    "libs/toastr",
    "mvc/library/library-model",
    "mvc/library/library-dataset-view"],
function(mod_masthead,
         mod_utils,
         mod_toastr,
         mod_library_model,
         mod_library_dataset_view) {

var FolderRowView = Backbone.View.extend({

  lastSelectedHistory: '',

  events: {
    'click .undelete_dataset_btn'    : 'undeleteDataset',
    'click .undelete_folder_btn'     : 'undeleteFolder'
  },

  options: {
    type: null
  },

  initialize : function(folder_item){
    this.model = folder_item;
    this.render(folder_item);
  },

  render: function(folder_item){
    var template = null;
    if (folder_item.get('type') === 'folder' || folder_item.get('model_class') === 'LibraryFolder'){
      this.options.type = 'folder';
      if (folder_item.get('deleted')){
        template = this.templateRowDeletedFolder();
      } else{
        template = this.templateRowFolder();
      }
    } else if (folder_item.get('type') === 'file' || folder_item.get('model_class') === 'LibraryDatasetDatasetAssociation'){
      this.options.type = 'file';
      if (folder_item.get('deleted')){
        template = this.templateRowDeletedFile();
      } else {
        template = this.templateRowFile();
      }
    } else {
      console.error('Unknown library item type found.');
      console.error(folder_item.get('type') || folder_item.get('model_class'));
    }
    this.setElement(template({content_item:folder_item}));
    this.$el.show();
    return this;
  },

  showDatasetDetails : function(){
    Galaxy.libraries.datasetView = new mod_library_dataset_view.LibraryDatasetView({id: this.id});
  },

  /**
   * Undeletes the dataset on server and renders the row again.
   */
  undeleteDataset : function(event){
    $(".tooltip").hide();
    var that = this;
    var dataset_id = $(event.target).closest('tr')[0].id;
    var dataset = Galaxy.libraries.folderListView.collection.get(dataset_id);
    dataset.url = dataset.urlRoot + dataset.id + '?undelete=true';
    dataset.destroy({ 
        success : function(model, response){
          Galaxy.libraries.folderListView.collection.remove(dataset_id);
          var updated_dataset = new mod_library_model.Item(response);
          Galaxy.libraries.folderListView.collection.add(updated_dataset);
          Galaxy.libraries.folderListView.collection.sortByNameAsc();
          mod_toastr.success('Dataset undeleted. Click this to see it.', '', {onclick: function() {
            var folder_id = that.model.get('folder_id');
            window.location='#folders/' + folder_id + '/datasets/' + that.id;
          }});
        }, 
        error : function(model, response){
          if (typeof response.responseJSON !== "undefined"){
            mod_toastr.error('Dataset was not undeleted. ' + response.responseJSON.err_msg);
          } else {
            mod_toastr.error('An error occured! Dataset was not undeleted. Please try again.');
          }
        }
  });
  },

  /**
   * Undeletes the folder on server and renders the row again.
   */
  undeleteFolder : function(event){
    $(".tooltip").hide();
    var that = this;
    var folder_id = $(event.target).closest('tr')[0].id;
    var folder = Galaxy.libraries.folderListView.collection.get(folder_id);
    folder.url = folder.urlRoot + folder.id + '?undelete=true';
    folder.destroy({
        success : function(model, response){
          Galaxy.libraries.folderListView.collection.remove(folder_id);
          var updated_folder = new mod_library_model.FolderAsModel(response);
          Galaxy.libraries.folderListView.collection.add(updated_folder);
          Galaxy.libraries.folderListView.collection.sortByNameAsc();
          mod_toastr.success('Folder undeleted.');
        }, 
        error : function(model, response){
          if (typeof response.responseJSON !== "undefined"){
            mod_toastr.error('Folder was not undeleted. ' + response.responseJSON.err_msg);
          } else {
            mod_toastr.error('An error occured! Folder was not undeleted. Please try again.');
          }
        }
  });
  },

  templateRowFolder: function() {
    tmpl_array = [];

    tmpl_array.push('<tr class="folder_row light library-row" id="<%- content_item.id %>">');
    tmpl_array.push('  <td>');
    tmpl_array.push('    <span title="Folder" class="fa fa-folder-o"></span>');
    tmpl_array.push('  </td>');
    tmpl_array.push('  <td style="text-align: center; "><input style="margin: 0;" type="checkbox"></td>');
    tmpl_array.push('  <td>');
    tmpl_array.push('    <a href="#folders/<%- content_item.id %>"><%- content_item.get("name") %></a>');
    tmpl_array.push('  </td>');
    tmpl_array.push('  <td>folder</td>');
    tmpl_array.push('  <td></td>');
    tmpl_array.push('  <td><%= _.escape(content_item.get("update_time")) %></td>'); // time updated
    tmpl_array.push('  <td>');
    tmpl_array.push('    <% if (content_item.get("can_manage")) { %><a href="#/folders/<%- content_item.id %>/permissions"><button data-toggle="tooltip" data-placement="top" class="primary-button btn-xs permissions-folder-btn show_on_hover" title="Manage permissions" style="display:none;"><span class="fa fa-group"></span></button></a><% } %>');
    tmpl_array.push('  </td>');
    tmpl_array.push('</tr>');

    return _.template(tmpl_array.join(''));
  },

  templateRowFile: function(){
    tmpl_array = [];

    tmpl_array.push('<tr class="dataset_row light library-row" id="<%- content_item.id %>">');
    tmpl_array.push('  <td>');
    tmpl_array.push('    <span title="Dataset" class="fa fa-file-o"></span>');
    tmpl_array.push('  </td>');
    tmpl_array.push('  <td style="text-align: center; "><input style="margin: 0;" type="checkbox"></td>');
    tmpl_array.push('  <td><a href="#folders/<%- content_item.get("folder_id") %>/datasets/<%- content_item.id %>" class="library-dataset"><%- content_item.get("name") %><a></td>'); // dataset
    tmpl_array.push('  <td><%= _.escape(content_item.get("file_ext")) %></td>'); // data type
    tmpl_array.push('  <td><%= _.escape(content_item.get("file_size")) %></td>'); // size
    tmpl_array.push('  <td><%= _.escape(content_item.get("update_time")) %></td>'); // time updated
    tmpl_array.push('  <td>');
    tmpl_array.push('    <% if (content_item.get("is_unrestricted")) { %><span data-toggle="tooltip" data-placement="top" title="Unrestricted dataset" style="color:grey;" class="fa fa-globe fa-lg"></span><% } %>');
    tmpl_array.push('    <% if (content_item.get("is_private")) { %><span data-toggle="tooltip" data-placement="top" title="Private dataset" style="color:grey;" class="fa fa-key fa-lg"></span><% } %>');
    tmpl_array.push('    <% if ((content_item.get("is_unrestricted") === false) && (content_item.get("is_private") === false)) { %><span data-toggle="tooltip" data-placement="top" title="Restricted dataset" style="color:grey;" class="fa fa-shield fa-lg"></span><% } %>');
    tmpl_array.push('    <% if (content_item.get("can_manage")) { %><a href="#folders/<%- content_item.get("folder_id") %>/datasets/<%- content_item.id %>/permissions"><button data-toggle="tooltip" data-placement="top" class="primary-button btn-xs permissions-dataset-btn show_on_hover" title="Manage permissions" style="display:none;"><span class="fa fa-group"></span></button></a><% } %>');
    tmpl_array.push('  </td>');
    tmpl_array.push('</tr>');

    return _.template(tmpl_array.join(''));
  },  

  templateRowDeletedFile: function(){
    tmpl_array = [];

    tmpl_array.push('<tr class="active deleted_dataset library-row" id="<%- content_item.id %>">');
    tmpl_array.push('  <td>');
    tmpl_array.push('    <span title="Dataset" class="fa fa-file-o"></span>');
    tmpl_array.push('  </td>');
    tmpl_array.push('  <td></td>');
    tmpl_array.push('  <td style="color:grey;"><%- content_item.get("name") %></td>'); // dataset
    tmpl_array.push('  <td><%= _.escape(content_item.get("file_ext")) %></td>'); // data type
    tmpl_array.push('  <td><%= _.escape(content_item.get("file_size")) %></td>'); // size
    tmpl_array.push('  <td><%= _.escape(content_item.get("update_time")) %></td>'); // time updated
    tmpl_array.push('  <td><span data-toggle="tooltip" data-placement="top" title="Marked deleted" style="color:grey;" class="fa fa-ban fa-lg"> </span><button data-toggle="tooltip" data-placement="top" title="Undelete <%- content_item.get("name") %>" class="primary-button btn-xs undelete_dataset_btn show_on_hover" type="button" style="display:none; margin-left:1em;"><span class="fa fa-unlock"> Undelete</span></button></td>');
    tmpl_array.push('</tr>');

    return _.template(tmpl_array.join(''));
  },

  templateRowDeletedFolder: function(){
    tmpl_array = [];

    tmpl_array.push('<tr class="active folder_row light library-row" id="<%- content_item.id %>">');
    tmpl_array.push('  <td>');
    tmpl_array.push('    <span title="Folder" class="fa fa-folder-o"></span>');
    tmpl_array.push('  </td>');
    tmpl_array.push('  <td></td>');
    tmpl_array.push('  <td style="color:grey;">');
    tmpl_array.push('    <%- content_item.get("name") %>');
    tmpl_array.push('  </td>');
    tmpl_array.push('  <td>folder</td>');
    tmpl_array.push('  <td></td>');
    tmpl_array.push('  <td><%= _.escape(content_item.get("update_time")) %></td>'); // time updated
    tmpl_array.push('  <td><span data-toggle="tooltip" data-placement="top" title="Marked deleted" style="color:grey;" class="fa fa-ban fa-lg"> </span><button data-toggle="tooltip" data-placement="top" title="Undelete <%- content_item.get("name") %>" class="primary-button btn-xs undelete_folder_btn show_on_hover" type="button" style="display:none; margin-left:1em;"><span class="fa fa-unlock"> Undelete</span></button></td>');
    tmpl_array.push('</tr>');

    return _.template(tmpl_array.join(''));
  }
   
});

return {
    FolderRowView: FolderRowView
};

});
