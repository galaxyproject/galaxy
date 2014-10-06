define([
    "galaxy.masthead",
    "utils/utils",
    "libs/toastr",
    "mvc/library/library-model",
    "mvc/library/library-folderrow-view",
    "mvc/library/library-dataset-view"
    ],
function(mod_masthead,
         mod_utils,
         mod_toastr,
         mod_library_model,
         mod_library_folderrow_view,
         mod_library_dataset_view
         ) {

var FolderListView = Backbone.View.extend({
  el : '#folder_items_element',
  defaults: {
    'include_deleted' : false
  },
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
    'click .sort-folder-link'       : 'sortColumnClicked'
  },

  // cache of rendered views
  rowViews: {},
  
  initialize : function(options){
    this.options = _.defaults(this.options || {}, options);
    this.fetchFolder();
  },

  fetchFolder: function(options){
    var options = options || {};
    this.options.include_deleted = options.include_deleted;
    var that = this;

    this.collection = new mod_library_model.Folder();

    // start to listen if someone modifies collection
    this.listenTo(this.collection, 'add', this.renderOne);
    this.listenTo(this.collection, 'remove', this.removeOne);

    this.folderContainer = new mod_library_model.FolderContainer({id: this.options.id});
    this.folderContainer.url = this.folderContainer.attributes.urlRoot + this.options.id + '/contents';
    if (this.options.include_deleted){
      this.folderContainer.url = this.folderContainer.url + '?include_deleted=true';
    }
    this.folderContainer.fetch({
        success: function(folder_container) {
          that.folder_container = folder_container;
          that.render();
          that.addAll(folder_container.get('folder').models);
          if (that.options.dataset_id){
            row = _.findWhere(that.rowViews, {id: that.options.dataset_id});
            if (row) {
              row.showDatasetDetails();
            } else {
              mod_toastr.error('Dataset not found. Showing folder instead.');
            }
          }
        },
        error: function(model, response){
          if (typeof response.responseJSON !== "undefined"){
            mod_toastr.error(response.responseJSON.err_msg + ' Click this to go back.', '', {onclick: function() {Galaxy.libraries.library_router.back();}});
          } else {
            mod_toastr.error('An error ocurred. Click this to go back.', '', {onclick: function() {Galaxy.libraries.library_router.back();}});
          }
        }
    });
  },

  render: function (options) {
    this.options = _.defaults(this.options, options);
    var template = this.templateFolder();
    $(".tooltip").hide();

    // TODO move to server
    // find the upper id in the full path
    var path = this.folderContainer.attributes.metadata.full_path;
    var upper_folder_id;
    if (path.length === 1){ // the library is above us
      upper_folder_id = 0;
    } else {
      upper_folder_id = path[path.length-2][0];
    }

    this.$el.html(template({ path: this.folderContainer.attributes.metadata.full_path, parent_library_id: this.folderContainer.attributes.metadata.parent_library_id, id: this.options.id, upper_folder_id: upper_folder_id, order: this.sort}));

    // initialize the library tooltips
    $("#center [data-toggle]").tooltip();
    //hack to show scrollbars
    $("#center").css('overflow','auto');
  },

  /**
   * Call this after all models are added to the collection
   * to ensure that the folder toolbar will show proper options
   * and that event will be bound on all subviews.
   */
  postRender: function(){
    var fetched_metadata = this.folderContainer.attributes.metadata;
    fetched_metadata.contains_file = typeof this.collection.findWhere({type: 'file'}) !== 'undefined';
    Galaxy.libraries.folderToolbarView.configureElements(fetched_metadata);
    $('.library-row').hover(function() {
      $(this).find('.show_on_hover').show();
    }, function () {
      $(this).find('.show_on_hover').hide();
    });
  },

  /**
   * Adds all given models to the collection.
   * @param {array of Item or FolderAsModel} array of models that should
   *  be added to the view's collection.
   */
  addAll: function(models){
    _.each(models.reverse(), function(model) {
      Galaxy.libraries.folderListView.collection.add(model);
    });

    $("#center [data-toggle]").tooltip();
    this.checkEmptiness();

    this.postRender();
  },

  /**
   * Iterates this view's collection and calls the render
   * function for each. Also binds the hover behavior.
   */
  renderAll: function(){
    var that = this;
    _.each(this.collection.models.reverse(), function(model) {
      that.renderOne(model);
    });
    this.postRender();
  },

  /**
   * Creates a view for the given model and adds it to the folder view.
   * @param {Item or FolderAsModel} model of the view that will be rendered
   */
  renderOne: function(model){
    if (model.get('type') !== 'folder'){
        this.options.contains_file = true;
        // model.set('readable_size', this.size_to_string(model.get('file_size')));
      }
    model.set('folder_id', this.id);
    var rowView = new mod_library_folderrow_view.FolderRowView(model);

    // save new rowView to cache
    this.rowViews[model.get('id')] = rowView;

    this.$el.find('#first_folder_item').after(rowView.el);

    $('.library-row').hover(function() {
      $(this).find('.show_on_hover').show();
    }, function () {
      $(this).find('.show_on_hover').hide();
    });
  },

  /**
   * removes the view of the given model from the DOM
   * @param {Item or FolderAsModel} model of the view that will be removed
   */
  removeOne: function(model){
    this.$el.find('#' + model.id).remove();
  },

  /** Checks whether the list is empty and adds/removes the message */
  checkEmptiness : function(){
    if ((this.$el.find('.dataset_row').length === 0) && (this.$el.find('.folder_row').length === 0)){
      this.$el.find('.empty-folder-message').show();
    } else {
      this.$el.find('.empty-folder-message').hide();
    }
  },

  /** User clicked the table heading = he wants to sort stuff */
  sortColumnClicked : function(event){
    event.preventDefault();
    if (this.sort === 'asc'){
        this.sortFolder('name','desc');
        this.sort = 'desc';
    } else {
        this.sortFolder('name','asc');
        this.sort = 'asc';
    }
    this.render();
    this.renderAll();
    this.checkEmptiness();
  },

  /**
   *  Sorts the underlying collection according to the parameters received. 
   *  Currently supports only sorting by name. 
   */
  sortFolder: function(sort_by, order){
      if (sort_by === 'name'){
          if (order === 'asc'){
              return this.collection.sortByNameAsc();
          } else if (order === 'desc'){
              return this.collection.sortByNameDesc();
          }
      }
  },

  /**
   * User clicked the checkbox in the table heading
   * @param  {context} event
   */
  selectAll : function (event) {
       var selected = event.target.checked;
       that = this;
       // Iterate each checkbox
       $(':checkbox', '#folder_list_body').each(function() {
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

  /** 
   * Check checkbox if user clicks on the whole row or 
   *  on the checkbox itself 
   */
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
    $row.removeClass('light').addClass('dark');
    $row.find('a').removeClass('light').addClass('dark');
    $row.find('.fa-file-o').removeClass('fa-file-o').addClass('fa-file');
  },

  makeWhiteRow: function($row){
    $row.removeClass('dark').addClass('light');
    $row.find('a').removeClass('dark').addClass('light');
    $row.find('.fa-file').removeClass('fa-file').addClass('fa-file-o');
  },

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
      tmpl_array.push('<table data-library-id="<%- parent_library_id  %>" id="folder_table" class="grid table table-condensed">');
      tmpl_array.push('   <thead>');
      tmpl_array.push('       <th class="button_heading"></th>');
      tmpl_array.push('       <th style="text-align: center; width: 20px; " title="Check to select all datasets"><input id="select-all-checkboxes" style="margin: 0;" type="checkbox"></th>');
      tmpl_array.push('       <th><a class="sort-folder-link" title="Click to reverse order" href="#">name</a> <span title="Sorted alphabetically" class="fa fa-sort-alpha-<%- order %>"></span></th>');
      tmpl_array.push('       <th style="width:5%;">data type</th>');
      tmpl_array.push('       <th style="width:10%;">size</th>');
      tmpl_array.push('       <th style="width:160px;">time updated (UTC)</th>');
      tmpl_array.push('       <th style="width:10%;"></th> ');
      tmpl_array.push('   </thead>');
      tmpl_array.push('   <tbody id="folder_list_body">');
      tmpl_array.push('       <tr id="first_folder_item">');
      tmpl_array.push('           <td><a href="#<% if (upper_folder_id !== 0){ print("folders/" + upper_folder_id)} %>" title="Go to parent folder" class="btn_open_folder btn btn-default btn-xs">..<a></td>');
      tmpl_array.push('           <td></td>');
      tmpl_array.push('           <td></td>');
      tmpl_array.push('           <td></td>');
      tmpl_array.push('           <td></td>');
      tmpl_array.push('           <td></td>');
      tmpl_array.push('           <td></td>');
      tmpl_array.push('       </tr>');

      tmpl_array.push('   </tbody>');
      tmpl_array.push('</table>');
      tmpl_array.push('<div class="empty-folder-message" style="display:none;">This folder is either empty or you do not have proper access permissions to see the contents. If you expected something to show up please consult the <a href="https://wiki.galaxyproject.org/Admin/DataLibraries/LibrarySecurity" target="_blank">library security wikipage</a> or visit the <a href="https://biostar.usegalaxy.org/" target="_blank">Galaxy support site</a>.</div>');

      return _.template(tmpl_array.join(''));
  }
  
});

return {
    FolderListView: FolderListView
};

});
