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

var FolderToolbarView = Backbone.View.extend({
  el: '#center',

  events: {
    'click #toolbtn_create_folder'  : 'createFolderFromModal',
    'click #toolbtn_bulk_import'    : 'modalBulkImport',
    'click .toolbtn_add_files'      : 'addFilesToFolderModal'
  },

  defaults: {
    'can_add_library_item'  : false,
    'contains_file'         : false
  },

  modal : null,

  // user's histories
  histories : null,

  initialize: function(options){
    this.options = _.defaults(options || {}, this.defaults);
    this.render();
  },

  render: function(options){
    this.options = _.extend(this.options, options);
    var toolbar_template = this.templateToolBar();
    var is_admin = Galaxy.currUser.isAdmin();
    this.$el.html(toolbar_template({id: this.options.id, admin_user: is_admin}));
  },

  configureElements: function(options){
    this.options = _.extend(this.options, options);
    if (this.options.can_add_library_item === true){
      $('#toolbtn_create_folder').show();
      $('.toolbtn_add_files').show();
    }
    if (this.options.contains_file === true){
      $('#toolbtn_bulk_import').show();
      $('#toolbtn_dl').show();
    }
    this.$el.find('[data-toggle]').tooltip();
  },

  // shows modal for creating folder
  createFolderFromModal: function(){
    event.preventDefault();
    event.stopPropagation();

    // create modal
    var self = this;
    var template = this.templateNewFolderInModal();
    this.modal = Galaxy.modal;
    this.modal.show({
        closing_events  : true,
        title           : 'Create New Folder',
        body            : template(),
        buttons         : {
            'Create'    : function() {self.create_new_folder_event();},
            'Close'     : function() {Galaxy.modal.hide();}
        }
    });
  },

  // create the new folder from modal
  create_new_folder_event: function(){
      var folderDetails = this.serialize_new_folder();
      if (this.validate_new_folder(folderDetails)){
          var folder = new mod_library_model.FolderAsModel();
          url_items = Backbone.history.fragment.split('/');
          current_folder_id = url_items[url_items.length-1];
          folder.url = folder.urlRoot + '/' + current_folder_id ;

          var self = this;
          folder.save(folderDetails, {
            success: function (folder) {
              self.modal.hide();
              mod_toastr.success('Folder created');
              folder.set({'type' : 'folder'})
              Galaxy.libraries.folderListView.folderContainer.attributes.folder.add(folder);
              Galaxy.libraries.folderListView.render({id: current_folder_id});
            },
            error: function(){
              mod_toastr.error('An error occured :(');
            }
          });
      } else {
          mod_toastr.error('Folder\'s name is missing');
      }
      return false;
  },

  // serialize data from the modal
  serialize_new_folder : function(){
      return {
          name: $("input[name='Name']").val(),
          description: $("input[name='Description']").val()
      };
  },

  // validate new folder info
  validate_new_folder: function(folderDetails){
      return folderDetails.name !== '';
  },


  // show bulk import modal
  modalBulkImport : function(){
      var checkedValues = $('#folder_table').find(':checked');
      if(checkedValues.length === 0){
          mod_toastr.info('You have to select some datasets first');
      } else {
          this.refreshUserHistoriesList(function(self){
            var template = self.templateBulkImportInModal();
            self.modal = Galaxy.modal;
            self.modal.show({
                closing_events  : true,
                title           : 'Import into History',
                body            : template({histories : self.histories.models}),
                buttons         : {
                    'Import'    : function() {self.importAllIntoHistory();},
                    'Close'     : function() {Galaxy.modal.hide();}
                }
            });
          });
      }
  },

  refreshUserHistoriesList: function(callback){
    var self = this;
    this.histories = new mod_library_model.GalaxyHistories();
    this.histories.fetch({
      success: function (){
        callback(self);
      },
      error: function(){
      }
    });
  },

  // import all selected datasets into history
  importAllIntoHistory : function (){
      //disable the button to prevent multiple submission
      this.modal.disableButton('Import');

      var history_id = $("select[name=dataset_import_bulk] option:selected").val();
      var history_name = $("select[name=dataset_import_bulk] option:selected").text();

      var dataset_ids = [];
      $('#folder_table').find(':checked').each(function(){
          if (this.parentElement.parentElement.id !== '') {
              dataset_ids.push(this.parentElement.parentElement.id);
          }
      });
      var progress_bar_tmpl = this.templateProgressBar();
      $(this.modal.elMain).find('.modal-body').html(progress_bar_tmpl({ history_name : history_name }));

      // init the progress bar
      var progressStep = 100 / dataset_ids.length;
      this.initProgress(progressStep);

      // prepare the dataset objects to be imported
      var datasets_to_import = [];
      for (var i = dataset_ids.length - 1; i >= 0; i--) {
          library_dataset_id = dataset_ids[i];
          var historyItem = new mod_library_model.HistoryItem();
          var self = this;
          historyItem.url = historyItem.urlRoot + history_id + '/contents';
          historyItem.content = library_dataset_id;
          historyItem.source = 'library';
          datasets_to_import.push(historyItem);
      }
      // call the recursive function to call ajax one after each other (request FIFO queue)
      this.chainCall(datasets_to_import);
  },

  chainCall: function(history_item_set){
    var self = this;
    var popped_item = history_item_set.pop();
    if (typeof popped_item === "undefined") {
        mod_toastr.success('All datasets imported');
        this.modal.hide();
        return;
    }
        var promise = $.when(popped_item.save({content: popped_item.content, source: popped_item.source})).done(function(a1){
                self.updateProgress();
                self.chainCall(history_item_set);
            });
  },

  initProgress: function(progressStep){
      this.progress = 0;
      this.progressStep = progressStep;
  },

  updateProgress: function(){
      this.progress += this.progressStep;
      $('.progress-bar-import').width(Math.round(this.progress) + '%');
      txt_representation = Math.round(this.progress) + '% Complete';
      $('.completion_span').text(txt_representation);
  },

  // download selected datasets
  download : function(folder_id, format){
    var dataset_ids = [];
        $('#folder_table').find(':checked').each(function(){
            if (this.parentElement.parentElement.id !== '') {
                dataset_ids.push(this.parentElement.parentElement.id);
            }
        });

    var url = '/api/libraries/datasets/download/' + format;
    var data = {'ldda_ids' : dataset_ids};
    this.processDownload(url, data, 'get');
  },

  // create hidden form and submit through POST to initialize download
  processDownload: function(url, data, method){
    //url and data options required
    if( url && data ){
            //data can be string of parameters or array/object
            data = typeof data == 'string' ? data : $.param(data);
            //split params into form inputs
            var inputs = '';
            $.each(data.split('&'), function(){
                    var pair = this.split('=');
                    inputs+='<input type="hidden" name="'+ pair[0] +'" value="'+ pair[1] +'" />';
            });
            //send request
            $('<form action="'+ url +'" method="'+ (method||'post') +'">'+inputs+'</form>')
            .appendTo('body').submit().remove();
            
            mod_toastr.info('Your download will begin soon');
    }
  },

  addFilesToFolderModal: function(){
    this.refreshUserHistoriesList(function(self){
      self.modal = Galaxy.modal;
      var template_modal = self.templateAddFilesInModal();
      self.modal.show({
          closing_events  : true,
          title           : 'Add datasets from history to ' + self.options.folder_name,
          body            : template_modal({histories: self.histories.models}),
          buttons         : {
              'Add'       : function() {self.addFiles();},
              'Close'     : function() {Galaxy.modal.hide();}
          }
      });
      self.fetchAndDisplayHistoryContents(self.histories.models[0].id);
      $( "#dataset_add_bulk" ).change(function(event) {
        self.fetchAndDisplayHistoryContents(event.target.value);
      });

    });
  },

  fetchAndDisplayHistoryContents: function(history_id){
    var history_contents = new mod_library_model.HistoryContents({id:history_id});
    var self = this;
    history_contents.fetch({
      success: function(history_contents){
        var history_contents_template = self.templateHistoryContents();
        mod_toastr.success('history contents fetched');
        self.histories.get(history_id).set({'contents' : history_contents});
        self.modal.$el.find('#selected_history_content').html(history_contents_template({history_contents: history_contents.models.reverse()}));
      },
      error: function(){
        mod_toastr.error('history contents fetch failed');
      }
    });
  },

  addFiles: function(){
    alert('adding files');
  },

  templateToolBar: function(){
    tmpl_array = [];

    // CONTAINER
    tmpl_array.push('<div class="library_style_container">');
    tmpl_array.push('<h3>Data Libraries Beta Test. This is work in progress. Please report problems & ideas via <a href="mailto:galaxy-bugs@bx.psu.edu?Subject=DataLibrariesBeta_Feedback" target="_blank">email</a> and <a href="https://trello.com/c/nwYQNFPK/56-data-library-ui-progressive-display-of-folders" target="_blank">Trello</a>.</h3>');
    // TOOLBAR
    tmpl_array.push('<div id="library_folder_toolbar" >');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Create New Folder" id="toolbtn_create_folder" class="primary-button" type="button" style="display:none;"><span class="fa fa-plus"></span> <span class="fa fa-folder"></span></button>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Add Datasets to Current Folder" id="toolbtn_add_files" class="toolbtn_add_files primary-button" type="button" style="display:none;"><span class="fa fa-plus"></span> <span class="fa fa-file"></span></span></button>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Import selected datasets into history" id="toolbtn_bulk_import" class="primary-button" style="margin-left: 0.5em; display:none;" type="button"><span class="fa fa-book"></span> to history</button>');
    tmpl_array.push('   <div id="toolbtn_dl" class="btn-group" style="margin-left: 0.5em; display:none; ">');
    tmpl_array.push('       <button title="Download selected datasets" id="drop_toggle" type="button" class="primary-button dropdown-toggle" data-toggle="dropdown">');
    tmpl_array.push('       <span class="fa fa-download"></span> download <span class="caret"></span>');
    tmpl_array.push('       </button>');
    tmpl_array.push('       <ul class="dropdown-menu" role="menu">');
    tmpl_array.push('          <li id="download_archive"><a href="#/folders/<%= id %>/download/tgz">.tar.gz</a></li>');
    tmpl_array.push('          <li id="download_archive"><a href="#/folders/<%= id %>/download/tbz">.tar.bz</a></li>');
    tmpl_array.push('          <li id="download_archive"><a href="#/folders/<%= id %>/download/zip">.zip</a></li>');
    tmpl_array.push('       </ul>');
    tmpl_array.push('   </div>');
    tmpl_array.push('   </div>');
    tmpl_array.push('   <div id="folder_items_element">');
    // library items will append here
    tmpl_array.push('   </div>');
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  },

  templateNewFolderInModal: function(){
    tmpl_array = [];

    tmpl_array.push('<div id="new_folder_modal">');
    tmpl_array.push('<form>');
    tmpl_array.push('<input type="text" name="Name" value="" placeholder="Name">');
    tmpl_array.push('<input type="text" name="Description" value="" placeholder="Description">');
    tmpl_array.push('</form>');
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  },


  templateBulkImportInModal : function(){
    var tmpl_array = [];

    tmpl_array.push('<span id="history_modal_combo_bulk" style="width:90%; margin-left: 1em; margin-right: 1em; ">');
    tmpl_array.push('Select history: ');
    tmpl_array.push('<select id="dataset_import_bulk" name="dataset_import_bulk" style="width:50%; margin-bottom: 1em; "> ');
    tmpl_array.push('   <% _.each(histories, function(history) { %>'); //history select box
    tmpl_array.push('       <option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>');
    tmpl_array.push('   <% }); %>');
    tmpl_array.push('</select>');
    tmpl_array.push('</span>');

    return _.template(tmpl_array.join(''));
  },

  templateProgressBar : function (){
    var tmpl_array = [];

    tmpl_array.push('<div class="import_text">');
    tmpl_array.push('Importing selected datasets to history <b><%= _.escape(history_name) %></b>');
    tmpl_array.push('</div>');
    tmpl_array.push('<div class="progress">');
    tmpl_array.push('   <div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 00%;">');
    tmpl_array.push('       <span class="completion_span">0% Complete</span>');
    tmpl_array.push('   </div>');
    tmpl_array.push('</div>');
    tmpl_array.push('');

    return _.template(tmpl_array.join(''));
  },

  templateAddFilesInModal : function (){
    var tmpl_array = [];

    tmpl_array.push('<div id="add_files_modal">');
    tmpl_array.push('<div id="history_modal_combo_bulk">');
    tmpl_array.push('Select history:  ');
    tmpl_array.push('<select id="dataset_add_bulk" name="dataset_add_bulk" style="width:66%; "> ');
    tmpl_array.push('   <% _.each(histories, function(history) { %>'); //history select box
    tmpl_array.push('       <option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>');
    tmpl_array.push('   <% }); %>');
    tmpl_array.push('</select>');
    tmpl_array.push('</div>');
    tmpl_array.push('<div id="selected_history_content">');

    tmpl_array.push('</div>');
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  },

  templateHistoryContents : function (){
    var tmpl_array = [];

    tmpl_array.push('Choose the datasets to import:');
    tmpl_array.push('<ul>');
    tmpl_array.push(' <% _.each(history_contents, function(history_item) { %>');
    tmpl_array.push(' <li data-id="<%= _.escape(history_item.get("id")) %>">');
    tmpl_array.push('   <input style="margin: 0;" type="checkbox"> <%= _.escape(history_item.get("hid")) %>: <%= _.escape(history_item.get("name")) %>');
    tmpl_array.push(' </li>');
    tmpl_array.push(' <% }); %>');
    tmpl_array.push('</ul>');

    return _.template(tmpl_array.join(''));
  }

});

return {
    FolderToolbarView: FolderToolbarView
};

});
