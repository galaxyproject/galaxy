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

  sort: 'asc',

  events: {
    'click #select-all-checkboxes'  : 'selectAll',
    'click .dataset_row'            : 'selectClickedRow',
    'click .sort-folder-link'       : 'sort_clicked'
  },
  
  initialize : function(options){
      var that = this;
      this.options = _.defaults(this.options || {}, options);
      this.collection = new mod_library_model.Folder();

      // start to listen if someone adds a model to the collection
      this.listenTo(this.collection, 'add', this.addOne);
      
      this.folderContainer = new mod_library_model.FolderContainer({id: this.options.id});
      this.folderContainer.url = this.folderContainer.attributes.urlRoot + this.options.id + '/contents';
      this.folderContainer.fetch({
          success: function (folder_container) {
            that.render();
            var items = folder_container.get('folder').models;
            that.addAll(items);
          },
          error: function(model, response){
            if (typeof response.responseJSON !== "undefined"){
              mod_toastr.error(response.responseJSON.err_msg);
            } else {
              mod_toastr.error('An error ocurred :(');
            }
          }
      });
  },

  render: function (options) {
    this.options = _.defaults(this.options || {}, options);
    var template = this.templateFolder();

    // TODO move to server
    // find the upper id in the full path
    var path = this.folderContainer.attributes.metadata.full_path;
    var upper_folder_id;
    if (path.length === 1){ // the library is above us
      upper_folder_id = 0;
    } else {
      upper_folder_id = path[path.length-2][0];
    }

    this.$el.html(template({ path: this.folderContainer.attributes.metadata.full_path, id: this.options.id, upper_folder_id: upper_folder_id, order: this.sort}));

    var fetched_metadata = this.folderContainer.attributes.metadata;
    fetched_metadata.contains_file = this.options.contains_file;
    Galaxy.libraries.folderToolbarView.configureElements(fetched_metadata);

    // initialize the library tooltips
    $("#center [data-toggle]").tooltip();
    //hack to show scrollbars
    $("#center").css('overflow','auto');
  },

  /** Adds all given models to the collection. */
  addAll:function(items){
    _.each(items.reverse(), function(item) {
      Galaxy.libraries.folderListView.collection.add(item);
    });
    this.checkEmptiness();
  },

  /** Creates a view for the given model and adds it to the folder view. */ 
  addOne: function(model){
    if (model.get('data_type') !== 'folder'){
        this.options.contains_file = true;
        model.set('readable_size', this.size_to_string(model.get('file_size')));
      }
    var rowView = new mod_library_folderrow_view.FolderRowView(model);
    this.$el.find('#first_folder_item').after(rowView.el);
    this.checkEmptiness();
  },

  /** Checks whether the list is empty and adds/removes the message */
  // TODO needs refactor
  checkEmptiness : function(){
    if ((this.$el.find('.dataset_row').length === 0) && (this.$el.find('.folder_row').length === 0)){
      var empty_folder_tmpl = this.templateEmptyFolder();
      this.$el.find('#folder_list_body').append(empty_folder_tmpl());
    } else {
      this.$el.find('#empty_folder_message').remove();
    }
  },

  /** User clicked the table heading = he wants to sort stuff */
  sort_clicked : function(event){
    event.preventDefault();
    if (this.sort === 'asc'){
        this.sortFolder('name','desc');
        this.sort = 'desc';
    } else {
        this.sortFolder('name','asc');
        this.sort = 'asc';
    }
    this.render();
  },

  /** Sorts the underlying collection according to the parameters received. 
   *  Currently supports only sorting by name. */
  sortFolder: function(sort_by, order){
      if (sort_by === 'name'){
          if (order === 'asc'){
              this.collection.sortByNameAsc();
          } else if (order === 'desc'){
              this.collection.sortByNameDesc();
          }
      }
  },

  /** convert size to nice string */
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

  /** User clicked the checkbox in the table heading */
  selectAll : function (event) {
       var selected = event.target.checked;
       that = this;
       // Iterate each checkbox
       $(':checkbox').each(function() {
          this.checked = selected;
          $row = $(this.parentElement.parentElement);
          // Change color of selected/unselected
          if (selected) {
            that.makeDarkRow($row);
          } else {
            that.makeWhiteRow($row);
          } 
      });
   },

  /** Check checkbox if user clicks on the whole row or 
   *  on the checkbox itself */
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
      tmpl_array.push('       <th style="text-align: center; width: 20px; " title="Check to select all datasets"><input id="select-all-checkboxes" style="margin: 0;" type="checkbox"></th>');
      tmpl_array.push('       <th><a class="sort-folder-link" title="Click to reverse order" href="#">name</a> <span title="Sorted alphabetically" class="fa fa-sort-alpha-<%- order %>"></span></th>');
      tmpl_array.push('       <th>data type</th>');
      tmpl_array.push('       <th>size</th>');
      tmpl_array.push('       <th>time updated (UTC)</th>');
      tmpl_array.push('   </thead>');
      tmpl_array.push('   <tbody id="folder_list_body">');
      tmpl_array.push('       <tr id="first_folder_item">');
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
  },

  templateEmptyFolder: function(){
    var tmpl_array = [];

    tmpl_array.push('<tr id="empty_folder_message">');
    tmpl_array.push('<td colspan="6" style="text-align:center">');
    tmpl_array.push('This folder is either empty or you do not have proper access permissions to see the contents.');
    tmpl_array.push('</td>');
    tmpl_array.push('</tr>');

    return _.template(tmpl_array.join(''));
  }

  });

return {
    FolderListView: FolderListView
};

});
