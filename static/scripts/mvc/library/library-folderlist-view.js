// dependencies
define([
    "galaxy.masthead",
    "utils/utils",
    "libs/toastr",
    "mvc/library/library-model",
    "mvc/library/library-folderrow-view"],
function(mod_masthead,
         mod_utils,
         mod_toastr,
         mod_library_model,
         mod_library_folderrow_view) {

var FolderListView = Backbone.View.extend({
  // main element definition
  el : '#folder_items_element',
  // progress percentage
  progress: 0,
  // progress rate per one item
  progressStep: 1,
  // self modal
  modal : null,

  folderContainer: null,

  // event binding
  events: {
    'click #select-all-checkboxes' : 'selectAll',
    'click .dataset_row' : 'selectClickedRow'
  },
    // initialize
    initialize : function(options){
        var that = this;
        this.options = _.defaults(this.options || {}, options);
        this.queue = jQuery.Deferred();
        this.queue.resolve();

        this.folderContainer = new mod_library_model.FolderContainer({id: this.options.id});
        this.folderContainer.url = this.folderContainer.attributes.urlRoot + this.options.id + '/contents';
        this.folderContainer.fetch({
            success: function (folderContainer) {
                that.render();
            },
            error: function(){
              mod_toastr.error('An error occured :(');
            }
        });
    },

    render: function (options) {
      this.options = _.defaults(this.options || {}, options);
      var template = this.templateFolder();
      var contains_file = false;

      // TODO move to server
      // prepare nice size strings
      for (var i = 0; i < this.folderContainer.attributes.folder.models.length; i++) {
        var model = this.folderContainer.attributes.folder.models[i];
        if (model.get('type') === 'file'){
          contains_file = true;
          model.set('readable_size', this.size_to_string(model.get('file_size')));
        }
      }

      // TODO move to server
      // find the upper id in the full path
      var path = this.folderContainer.attributes.metadata.full_path;
      var upper_folder_id;
      if (path.length === 1){ // the library is above us
        upper_folder_id = 0;
      } else {
        upper_folder_id = path[path.length-2][0];
      }
      // TODO add template when folder is empty

      this.$el.html(template({ path: this.folderContainer.attributes.metadata.full_path, id: this.options.id, upper_folder_id: upper_folder_id }));
      // this.$el.html(template({ path: this.folderContainer.attributes.metadata.full_path, items: this.folderContainer.attributes.folder.models, id: this.options.id, upper_folder_id: upper_folder_id }));

      if (this.folderContainer.attributes.folder.models.length > 0){
        this.renderRows();
      }
      // if (this.folderContainer.attributes.metadata.can_add_library_item === true){
      var metadata = this.folderContainer.attributes.metadata;
      metadata.contains_file = contains_file;
      Galaxy.libraries.folderToolbarView.configureElements(metadata);
      // Galaxy.libraries.folderToolbarView.configureElements({ can_add_library_item: this.folderContainer.attributes.metadata.can_add_library_item, contains_file: contains_file });
      // }

      // initialize the library tooltips
      $("#center [data-toggle]").tooltip();
      //hack to show scrollbars
      $("#center").css('overflow','auto');
    },

    renderRows: function(){
      for (var i = 0; i < this.folderContainer.attributes.folder.models.length; i++) {
        var folder_item = this.folderContainer.attributes.folder.models[i];
        var rowView = new mod_library_folderrow_view.FolderRowView(folder_item);
        this.$el.find('#folder_list_body').append(rowView.el);
      }
    },

      // convert size to nice string
      size_to_string : function (size){
        // identify unit
        var unit = "";
        if (size >= 100000000000)   { size = size / 100000000000; unit = "TB"; } else
        if (size >= 100000000)      { size = size / 100000000; unit = "GB"; } else
        if (size >= 100000)         { size = size / 100000; unit = "MB"; } else
        if (size >= 100)            { size = size / 100; unit = "KB"; } else
        { size = size * 10; unit = "b"; }
        // return formatted string
        return (Math.round(size) / 10) + unit;
      },

        // select all datasets
        selectAll : function (event) {
             var selected = event.target.checked;
             that = this;
             // Iterate each checkbox
             $(':checkbox').each(function() {
                this.checked = selected;
                $row = $(this.parentElement.parentElement);
                // Change color of selected/unselected
                (selected) ? that.makeDarkRow($row) : that.makeWhiteRow($row);
            });
             // Show the tools in menu
             // this.checkTools();
         },

         // Check checkbox on row itself or row checkbox click
         selectClickedRow : function (event) {
            var checkbox = '';
            var $row;
            var source;
            if (event.target.localName === 'input'){
                checkbox = event.target;
                $row = $(event.target.parentElement.parentElement);
                source = 'input';
            } else if (event.target.localName === 'td') {
                checkbox = $("#" + event.target.parentElement.id).find(':checkbox')[0];
                $row = $(event.target.parentElement);
                source = 'td';
            }

                if (checkbox.checked){
                    if (source==='td'){
                        checkbox.checked = '';
                        this.makeWhiteRow($row);
                    } else if (source==='input') {
                        this.makeDarkRow($row);
                    }
                } else {
                    if (source==='td'){
                        checkbox.checked = 'selected';
                        this.makeDarkRow($row);
                    } else if (source==='input') {
                        this.makeWhiteRow($row);
                    }
                }
                // this.checkTools();
        },

        makeDarkRow: function($row){
            $row.removeClass('light');
            $row.find('a').removeClass('light');
            $row.addClass('dark');
            $row.find('a').addClass('dark');
            $row.find('span').removeClass('fa-file-o');
            $row.find('span').addClass('fa-file');

        },

        makeWhiteRow: function($row){
            $row.removeClass('dark');
            $row.find('a').removeClass('dark');
            $row.addClass('light');
            $row.find('a').addClass('light');
            $row.find('span').addClass('fa-file-o');
            $row.find('span').removeClass('fa-file');
        },

// MMMMMMMMMMMMMMMMMM
// === TEMPLATES ====
// MMMMMMMMMMMMMMMMMM

    // main template for folder browsing
    templateFolder : function (){
        var tmpl_array = [];

        // BREADCRUMBS
        tmpl_array.push('<ol class="breadcrumb">');
        tmpl_array.push('   <li><a title="Return to the list of libraries" href="#">Libraries</a></li>');
        tmpl_array.push('   <% _.each(path, function(path_item) { %>');
        tmpl_array.push('   <% if (path_item[0] != id) { %>');
        tmpl_array.push('   <li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ');
        tmpl_array.push(    '<% } else { %>');
        tmpl_array.push('   <li class="active"><span title="You are in this folder"><%- path_item[1] %></span></li>');
        tmpl_array.push('   <% } %>');
        tmpl_array.push('   <% }); %>');
        tmpl_array.push('</ol>');

        // FOLDER CONTENT
        tmpl_array.push('<table id="folder_table" class="grid table table-condensed">');
        tmpl_array.push('   <thead>');
        tmpl_array.push('       <th class="button_heading"></th>');
        tmpl_array.push('       <th style="text-align: center; width: 20px; "><input id="select-all-checkboxes" style="margin: 0;" type="checkbox"></th>');
        tmpl_array.push('       <th>name</th>');
        tmpl_array.push('       <th>data type</th>');
        tmpl_array.push('       <th>size</th>');
        tmpl_array.push('       <th>time updated (UTC)</th>');
        tmpl_array.push('   </thead>');
        tmpl_array.push('   <tbody id="folder_list_body">');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <td><a href="#<% if (upper_folder_id !== 0){ print("folders/" + upper_folder_id)} %>" title="Go to parent folder" class="btn_open_folder btn btn-default btn-xs">..<a></td>');
        tmpl_array.push('           <td></td>');
        tmpl_array.push('           <td></td>');
        tmpl_array.push('           <td></td>');
        tmpl_array.push('           <td></td>');
        tmpl_array.push('           <td></td>');
        tmpl_array.push('       </tr>');

        tmpl_array.push('   </tbody>');
        tmpl_array.push('</table>');

        return _.template(tmpl_array.join(''));
    }

    });

return {
    FolderListView: FolderListView
};

});
