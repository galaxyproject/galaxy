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
    'click #toolbtn_create_folder'        : 'createFolderFromModal',
    'click #toolbtn_bulk_import'          : 'modalBulkImport',
    'click .toolbtn_add_files'            : 'addFilesToFolderModal',
    'click #include_deleted_datasets_chk' : 'checkIncludeDeleted',
    'click #toolbtn_bulk_delete'          : 'deleteSelectedDatasets'
  },

  defaults: {
    'can_add_library_item'  : false,
    'contains_file'         : false,
    'chain_call_control'    : {
                                'total_number'  : 0,
                                'failed_number' : 0
                              }
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
    var is_admin = false;
    var is_anonym = true;
    if (Galaxy.currUser){
      is_admin = Galaxy.currUser.isAdmin();
      is_anonym = Galaxy.currUser.isAnonymous();
    }
    var toolbar_template = this.templateToolBar();
    this.$el.html(toolbar_template({id: this.options.id, admin_user: is_admin, anonym: is_anonym}));
  },

  configureElements: function(options){
    this.options = _.extend(this.options, options);

    if (this.options.can_add_library_item === true){
      $('.add-library-items').show();
    } else{
      $('.add-library-items').hide();
    }
    if (this.options.contains_file === true){
      if (Galaxy.currUser){
        if (!Galaxy.currUser.isAnonymous()){
          $('.logged-dataset-manipulation').show();
          $('.dataset-manipulation').show();
        } else {
          $('.dataset-manipulation').show();
          $('.logged-dataset-manipulation').hide();
        }
      } else {
        $('.logged-dataset-manipulation').hide();
        $('.dataset-manipulation').hide();
      }
    } else {
      $('.logged-dataset-manipulation').hide();
      $('.dataset-manipulation').hide();
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

          folder.save(folderDetails, {
            success: function (folder) {
              Galaxy.modal.hide();
              mod_toastr.success('Folder created');
              folder.set({'type' : 'folder'});
              Galaxy.libraries.folderListView.collection.add(folder);
            },
            error: function(model, response){
              Galaxy.modal.hide();
              if (typeof response.responseJSON !== "undefined"){
                mod_toastr.error(response.responseJSON.err_msg);
              } else {
                mod_toastr.error('An error ocurred :(');
              }
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
      error: function(model, response){
        if (typeof response.responseJSON !== "undefined"){
          mod_toastr.error(response.responseJSON.err_msg);
        } else {
          mod_toastr.error('An error ocurred :(');
        }
      }
    });
  },

  /**
   * import all selected datasets into history
   */
  importAllIntoHistory : function (){
      // disable the button to prevent multiple submission
      this.modal.disableButton('Import');

      // init the control counters
      this.options.chain_call_control.total_number = 0;
      this.options.chain_call_control.failed_number = 0;

      var history_id = $("select[name=dataset_import_bulk] option:selected").val();
      // we can save last used history to pre-select it next time
      this.options.last_used_history_id = history_id;
      var history_name = $("select[name=dataset_import_bulk] option:selected").text();

      var dataset_ids = [];
      $('#folder_table').find(':checked').each(function(){
          if (this.parentElement.parentElement.id !== '') {
              dataset_ids.push(this.parentElement.parentElement.id);
          }
      });
      var progress_bar_tmpl = this.templateImportIntoHistoryProgressBar();
      this.modal.$el.find('.modal-body').html(progress_bar_tmpl({ history_name : history_name }));

      // init the progress bar
      var progressStep = 100 / dataset_ids.length;
      this.initProgress(progressStep);

      // prepare the dataset objects to be imported
      var datasets_to_import = [];
      for (var i = dataset_ids.length - 1; i >= 0; i--) {
          var library_dataset_id = dataset_ids[i];
          var historyItem = new mod_library_model.HistoryItem();
          historyItem.url = historyItem.urlRoot + history_id + '/contents';
          historyItem.content = library_dataset_id;
          historyItem.source = 'library';
          datasets_to_import.push(historyItem);
      }
      this.options.chain_call_control.total_number = datasets_to_import.length;

      // set the used history as current so user will see the last one 
      // that he imported into in the history panel on the 'analysis' page
      var set_current_url =  '/api/histories/' + history_id + '/set_as_current';
      $.ajax({
        url: set_current_url,
        type: 'PUT'
      });
      // call the recursive function to call ajax one after each other (request FIFO queue)
      this.chainCall(datasets_to_import, history_name);
  },

  chainCall: function(history_item_set, history_name){
    var self = this;
    var popped_item = history_item_set.pop();
    if (typeof popped_item === "undefined") {
      if (this.options.chain_call_control.failed_number === 0){
        mod_toastr.success('Selected datasets imported into history. Click this to start analysing it.', '', {onclick: function() {window.location='/'}});
      } else if (this.options.chain_call_control.failed_number === this.options.chain_call_control.total_number){
        mod_toastr.error('There was an error and no datasets were imported into history.');
      } else if (this.options.chain_call_control.failed_number < this.options.chain_call_control.total_number){
        mod_toastr.warning('Some of the datasets could not be imported into history. Click this to see what was imported.', '', {onclick: function() {window.location='/'}});
      }
      Galaxy.modal.hide();
      return;
    }
    var promise = $.when(popped_item.save({content: popped_item.content, source: popped_item.source}));

    promise.done(function(){
              // we are fine
              self.updateProgress();
              self.chainCall(history_item_set, history_name);
            })
            .fail(function(){
              // we have a problem
              self.options.chain_call_control.failed_number += 1;
              self.updateProgress();
              self.chainCall(history_item_set, history_name);
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
            data = typeof data === 'string' ? data : $.param(data);
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
              'Add'       : function() {self.addAllDatasetsFromHistory();},
              'Close'     : function() {Galaxy.modal.hide();}
          }
      });
      
      // user should always have a history, even anonymous user
      if (self.histories.models.length > 0){
        self.fetchAndDisplayHistoryContents(self.histories.models[0].id);
        $( "#dataset_add_bulk" ).change(function(event) {
          self.fetchAndDisplayHistoryContents(event.target.value);
        });
      } else {
        mod_toastr.error('An error ocurred :(');
      }
    });
  },

  fetchAndDisplayHistoryContents: function(history_id){
    var history_contents = new mod_library_model.HistoryContents({id:history_id});
    var self = this;
    history_contents.fetch({
      success: function(history_contents){
        var history_contents_template = self.templateHistoryContents();
        self.histories.get(history_id).set({'contents' : history_contents});
        self.modal.$el.find('#selected_history_content').html(history_contents_template({history_contents: history_contents.models.reverse()}));
      },
      error: function(){
        mod_toastr.error('An error ocurred :(');
      }
    });
  },

  // add all selected datasets from history into current folder
  addAllDatasetsFromHistory : function (){
      // disable the button to prevent multiple submission
      this.modal.disableButton('Add');
      // init the control counters
      this.options.chain_call_control.total_number = 0;
      this.options.chain_call_control.failed_number = 0;

      var history_dataset_ids = [];
      this.modal.$el.find('#selected_history_content').find(':checked').each(function(){
        var hid = $(this.parentElement).data('id');
          if (hid) {
              history_dataset_ids.push(hid);
          }
      });
      var folder_name = this.options.folder_name;
      var progress_bar_tmpl = this.templateAddingDatasetsProgressBar();
      this.modal.$el.find('.modal-body').html(progress_bar_tmpl({ folder_name : folder_name }));

      // init the progress bar
      this.progressStep = 100 / history_dataset_ids.length;
      this.progress = 0;

      // prepare the dataset items to be added
      var hdas_to_add = [];
      for (var i = history_dataset_ids.length - 1; i >= 0; i--) {
          history_dataset_id = history_dataset_ids[i];
          var folder_item = new mod_library_model.Item();
          folder_item.url = '/api/folders/' + this.options.id + '/contents';
          folder_item.set({'from_hda_id':history_dataset_id});
          hdas_to_add.push(folder_item);
      }
      this.options.chain_call_control.total_number = hdas_to_add.length;
      // call the recursive function to call ajax one after each other (request FIFO queue)
      this.chainCallAddingHdas(hdas_to_add);
  },

  chainCallAddingHdas: function(hdas_set){
    var self = this;
    this.added_hdas = new mod_library_model.Folder();
    var popped_item = hdas_set.pop();
    if (typeof popped_item === "undefined") {
      if (this.options.chain_call_control.failed_number === 0){
        mod_toastr.success('Selected datasets from history added to the folder');
      } else if (this.options.chain_call_control.failed_number === this.options.chain_call_control.total_number){
        mod_toastr.error('There was an error and no datasets were added to the folder.');
      } else if (this.options.chain_call_control.failed_number < this.options.chain_call_control.total_number){
        mod_toastr.warning('Some of the datasets could not be added to the folder');
      }
      Galaxy.modal.hide();
      return this.added_hdas;
    }
    var promise = $.when(popped_item.save({from_hda_id: popped_item.get('from_hda_id')}));

    promise.done(function(model){
              // we are fine
              Galaxy.libraries.folderListView.collection.add(model);
              self.updateProgress();
              self.chainCallAddingHdas(hdas_set);
            })
            .fail(function(){
              // we have a problem
              self.options.chain_call_control.failed_number += 1;
              self.updateProgress();
              self.chainCallAddingHdas(hdas_set);
            });
  },

  /**
   * Handles the click on 'show deleted' checkbox
   */
  checkIncludeDeleted: function(event){
    if (event.target.checked){
      Galaxy.libraries.folderListView.fetchFolder({include_deleted: true});
    } else{
      Galaxy.libraries.folderListView.fetchFolder({include_deleted: false});
    }
  },

  /**
   * Deletes the selected datasets. Atomic. One by one.
   */
  deleteSelectedDatasets: function(){
    var checkedValues = $('#folder_table').find(':checked');
    if(checkedValues.length === 0){
        mod_toastr.info('You have to select some datasets first');
    } else {
      var template = this.templateDeletingDatasetsProgressBar();
      this.modal = Galaxy.modal;
      this.modal.show({
          closing_events  : true,
          title           : 'Deleting selected datasets',
          body            : template({}),
          buttons         : {
              'Close'     : function() {Galaxy.modal.hide();}
          }
      });
      // init the control counters
      this.options.chain_call_control.total_number = 0;
      this.options.chain_call_control.failed_number = 0;

      var dataset_ids = [];
      checkedValues.each(function(){
          if (this.parentElement.parentElement.id !== '') {
              dataset_ids.push(this.parentElement.parentElement.id);
          }
      });
      // init the progress bar
      this.progressStep = 100 / dataset_ids.length;
      this.progress = 0;
      
      // prepare the dataset items to be added
      var lddas_to_delete = [];
      for (var i = dataset_ids.length - 1; i >= 0; i--) {
          var dataset = new mod_library_model.Item({id:dataset_ids[i]});
          lddas_to_delete.push(dataset);
      }

      this.options.chain_call_control.total_number = dataset_ids.length;
      // call the recursive function to call ajax one after each other (request FIFO queue)
      this.chainCallDeletingHdas(lddas_to_delete);
    }
  },

  chainCallDeletingHdas: function(lddas_set){
  var self = this;
  this.deleted_lddas = new mod_library_model.Folder();
  var popped_item = lddas_set.pop();
  if (typeof popped_item === "undefined") {
    if (this.options.chain_call_control.failed_number === 0){
      mod_toastr.success('Selected datasets deleted');
    } else if (this.options.chain_call_control.failed_number === this.options.chain_call_control.total_number){
      mod_toastr.error('There was an error and no datasets were deleted.');
    } else if (this.options.chain_call_control.failed_number < this.options.chain_call_control.total_number){
      mod_toastr.warning('Some of the datasets could not be deleted');
    }
    Galaxy.modal.hide();
    return this.deleted_lddas;
  }
  var promise = $.when(popped_item.destroy());

  promise.done(function(dataset){
            // we are fine
            // self.$el.find('#' + popped_item.id).remove();
            Galaxy.libraries.folderListView.collection.remove(popped_item.id);
            self.updateProgress();
            // add the deleted dataset to collection, triggers rendering
            if (Galaxy.libraries.folderListView.options.include_deleted){
              var updated_dataset = new mod_library_model.Item(dataset);
              Galaxy.libraries.folderListView.collection.add(updated_dataset);
            }
            // execute next request
            self.chainCallDeletingHdas(lddas_set);
          })
          .fail(function(){
            // we have a problem
            self.options.chain_call_control.failed_number += 1;
            self.updateProgress();
            // execute next request
            self.chainCallDeletingHdas(lddas_set);
          });
  },

  templateToolBar: function(){
    tmpl_array = [];

    // CONTAINER
    tmpl_array.push('<div class="library_style_container">');
    // TOOLBAR
    tmpl_array.push('<div id="library_toolbar">');
    tmpl_array.push('<span data-toggle="tooltip" data-placement="top" class="logged-dataset-manipulation" title="Include deleted datasets" style="display:none;"><input id="include_deleted_datasets_chk" style="margin: 0;" type="checkbox"> include deleted</input></span>');
    tmpl_array.push('<div class="btn-group add-library-items" style="display:none;">');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Create New Folder" id="toolbtn_create_folder" class="btn btn-default primary-button" type="button"><span class="fa fa-plus"></span> <span class="fa fa-folder"></span></button>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Add Datasets to Current Folder" id="toolbtn_add_files" class="btn btn-default toolbtn_add_files primary-button" type="button"><span class="fa fa-plus"></span> <span class="fa fa-file"></span></span></button>');
    tmpl_array.push('</div>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Import selected datasets into history" id="toolbtn_bulk_import" class="primary-button dataset-manipulation" style="margin-left: 0.5em; display:none;" type="button"><span class="fa fa-book"></span> to History</button>');
    tmpl_array.push('   <div id="toolbtn_dl" class="btn-group dataset-manipulation" style="margin-left: 0.5em; display:none; ">');
    tmpl_array.push('       <button title="Download selected datasets as archive" id="drop_toggle" type="button" class="primary-button dropdown-toggle" data-toggle="dropdown">');
    tmpl_array.push('       <span class="fa fa-download"></span> Download <span class="caret"></span>');
    tmpl_array.push('       </button>');
    tmpl_array.push('       <ul class="dropdown-menu" role="menu">');
    tmpl_array.push('          <li id="download_archive"><a href="#/folders/<%= id %>/download/tgz">.tar.gz</a></li>');
    tmpl_array.push('          <li id="download_archive"><a href="#/folders/<%= id %>/download/tbz">.tar.bz</a></li>');
    tmpl_array.push('          <li id="download_archive"><a href="#/folders/<%= id %>/download/zip">.zip</a></li>');
    tmpl_array.push('       </ul>');
    tmpl_array.push('   </div>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Mark selected datasets deleted" id="toolbtn_bulk_delete" class="primary-button logged-dataset-manipulation" style="margin-left: 0.5em; display:none; " type="button"><span class="fa fa-times"></span> Delete</button>');
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

  templateImportIntoHistoryProgressBar : function (){
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

  templateAddingDatasetsProgressBar : function (){
    var tmpl_array = [];

    tmpl_array.push('<div class="import_text">');
    tmpl_array.push('Adding selected datasets from history to library folder <b><%= _.escape(folder_name) %></b>');
    tmpl_array.push('</div>');
    tmpl_array.push('<div class="progress">');
    tmpl_array.push('   <div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 00%;">');
    tmpl_array.push('       <span class="completion_span">0% Complete</span>');
    tmpl_array.push('   </div>');
    tmpl_array.push('</div>');
    tmpl_array.push('');

    return _.template(tmpl_array.join(''));
  },

  templateDeletingDatasetsProgressBar : function (){
    var tmpl_array = [];

    tmpl_array.push('<div class="import_text">');
    tmpl_array.push('</div>');
    tmpl_array.push('<div class="progress">');
    tmpl_array.push('   <div class="progress-bar progress-bar-delete" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 00%;">');
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
