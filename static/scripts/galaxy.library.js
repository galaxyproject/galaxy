// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === GALAXY LIBRARY MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

// global variables
var view            = null;
var library_router  = null;
var responses = [];

// dependencies
define([
    "galaxy.masthead", 
    "utils/utils",
    "libs/toastr"], function(mod_masthead, mod_utils, mod_toastr) {

// MMMMMMMMMMMMMMM
// === Models ====
// MMMMMMMMMMMMMMM

    // LIBRARY
    var Library = Backbone.Model.extend({
      urlRoot: '/api/libraries'
    });

    // FOLDER AS MODEL
    var FolderAsModel = Backbone.Model.extend({
      urlRoot: '/api/folders'
    });

    // LIBRARIES
    var Libraries = Backbone.Collection.extend({
      url: '/api/libraries',

      model: Library,

      sort_key: 'name', // default

      sort_order: null, // default

    });

    // ITEM
    var Item = Backbone.Model.extend({
        urlRoot : '/api/libraries/datasets'
    });

    // FOLDER AS COLLECTION
    var Folder = Backbone.Collection.extend({
      model: Item
    });

    // CONTAINER for folder contents (folders, items and metadata).
    var FolderContainer = Backbone.Model.extend({
        defaults : {
            folder : new Folder(),
            full_path : "unknown",
            urlRoot : "/api/folders/",
            id : "unknown"
        },
    parse : function(obj) {
      this.full_path = obj[0].full_path;
          // update the inner collection
          this.get("folder").reset(obj[1].folder_contents);
          return obj;
      }
    });

    // HISTORY ITEM
    var HistoryItem = Backbone.Model.extend({
        urlRoot : '/api/histories/'
    });

    // HISTORY
    var GalaxyHistory = Backbone.Model.extend({
        url : '/api/histories/'
    });

    // HISTORIES
    var GalaxyHistories = Backbone.Collection.extend({
        url : '/api/histories',
        model : GalaxyHistory
    });

// MMMMMMMMMMMMMM
// === VIEWS ====
// MMMMMMMMMMMMMM

//main view for folder browsing
var FolderContentView = Backbone.View.extend({
    // main element definition
    el : '#center',
    // progress percentage
    progress: 0,
    // progress rate per one item
    progressStep: 1,
    // last selected history in modal for UX
    lastSelectedHistory: '',
    // self modal
    modal : null,
    // loaded folders
    folders : null,

    // initialize
    initialize : function(){
        this.folders = [];
        this.queue = jQuery.Deferred();
        this.queue.resolve();
    },

// MMMMMMMMMMMMMMMMMM
// === TEMPLATES ====
// MMMMMMMMMMMMMMMMMM

    // main template for folder browsing
    templateFolder : function (){
        var tmpl_array = [];

        // CONTAINER
        tmpl_array.push('<div class="library_container" style="width: 90%; margin: auto; margin-top: 2em; ">');
        tmpl_array.push('<h3>Data Libraries Beta Test. This is work in progress. Please report problems & ideas via <a href="mailto:galaxy-bugs@bx.psu.edu?Subject=DataLibrariesBeta_Feedback" target="_blank">email</a> and <a href="https://trello.com/c/nwYQNFPK/56-data-library-ui-progressive-display-of-folders" target="_blank">Trello</a>.</h3>');

        // TOOLBAR
        tmpl_array.push('<div id="library_folder_toolbar" >');
        tmpl_array.push('   <button title="Create New Folder" id="toolbtn_create_folder" class="btn btn-primary" type="button"><span class="fa fa-plus"></span> <span class="fa fa-folder-close"></span> folder</button>');
        tmpl_array.push('   <button title="Import selected datasets into history" id="toolbtn_bulk_import" class="btn btn-primary" style="display: none; margin-left: 0.5em;" type="button"><span class="fa fa-external-link"></span> to history</button>');
        tmpl_array.push('   <div id="toolbtn_dl" class="btn-group" style="margin-left: 0.5em; display: none; ">');
        tmpl_array.push('       <button title="Download selected datasets" id="drop_toggle" type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown">');
        tmpl_array.push('       <span class="fa fa-download"></span> download <span class="caret"></span>');
        tmpl_array.push('       </button>');
        tmpl_array.push('       <ul class="dropdown-menu" role="menu">');
        tmpl_array.push('          <li><a href="#/folders/<%= id %>/download/tgz">.tar.gz</a></li>');
        tmpl_array.push('          <li><a href="#/folders/<%= id %>/download/tbz">.tar.bz</a></li>');
        tmpl_array.push('          <li><a href="#/folders/<%= id %>/download/zip">.zip</a></li>');
        tmpl_array.push('       </ul>');
        tmpl_array.push('   </div>');

        tmpl_array.push('</div>');

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
        tmpl_array.push('<table id="folder_table" class="library_table table table-condensed">');
        tmpl_array.push('   <thead>');
        tmpl_array.push('       <th class="button_heading"></th>');
        tmpl_array.push('       <th style="text-align: center; width: 20px; "><input id="select-all-checkboxes" style="margin: 0;" type="checkbox"></th>');
        tmpl_array.push('       <th>name</th>');
        tmpl_array.push('       <th>data type</th>');
        tmpl_array.push('       <th>size</th>');
        tmpl_array.push('       <th>date (UTC)</th>');
        tmpl_array.push('   </thead>');
        tmpl_array.push('   <tbody>');
        tmpl_array.push('       <td><a href="#<% if (upper_folder_id !== 0){ print("folders/" + upper_folder_id)} %>" title="Go to parent folder" class="btn_open_folder btn btn-default btn-xs">..<a></td>');
        tmpl_array.push('       <td></td>');
        tmpl_array.push('       <td></td>');
        tmpl_array.push('       <td></td>');
        tmpl_array.push('       <td></td>');
        tmpl_array.push('       <td></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <% _.each(items, function(content_item) { %>');
        tmpl_array.push('           <% if (content_item.get("type") === "folder") { %>'); // folder
        tmpl_array.push('               <tr class="folder_row light" id="<%- content_item.id %>">');
        tmpl_array.push('                   <td>');
        tmpl_array.push('                       <span title="Folder" class="fa fa-folder-o"></span>');
        tmpl_array.push('                   </td>');
        tmpl_array.push('                   <td></td>');
        tmpl_array.push('                   <td>');
        tmpl_array.push('                       <a href="#folders/<%- content_item.id %>"><%- content_item.get("name") %></a>');
        tmpl_array.push('                       <% if (content_item.get("item_count") === 0) { %>'); // empty folder
        tmpl_array.push('                           <span class="muted">(empty folder)</span>');
        tmpl_array.push('                       <% } %>');
        tmpl_array.push('                   </td>');
        tmpl_array.push('                   <td>folder</td>');
        tmpl_array.push('                   <td><%= _.escape(content_item.get("item_count")) %> item(s)</td>'); // size
        tmpl_array.push('                   <td><%= _.escape(content_item.get("time_updated")) %></td>'); // time updated
        tmpl_array.push('               </tr>');
        tmpl_array.push('           <% } else {  %>');
        tmpl_array.push('               <tr class="dataset_row light" id="<%- content_item.id %>">');
        tmpl_array.push('                   <td>');
        tmpl_array.push('                       <span title="Dataset" class="fa fa-file-o"></span>');
        tmpl_array.push('                   </td>');
        tmpl_array.push('                   <td style="text-align: center; "><input style="margin: 0;" type="checkbox"></td>');
        tmpl_array.push('                   <td><a href="#" class="library-dataset"><%- content_item.get("name") %><a></td>'); // dataset
        tmpl_array.push('                   <td><%= _.escape(content_item.get("data_type")) %></td>'); // data type
        tmpl_array.push('                   <td><%= _.escape(content_item.get("readable_size")) %></td>'); // size
        tmpl_array.push('                   <td><%= _.escape(content_item.get("time_updated")) %></td>'); // time updated
        tmpl_array.push('               </tr>');
        tmpl_array.push('               <% } %>  ');
        tmpl_array.push('       <% }); %>');
        tmpl_array.push('       ');
        tmpl_array.push('   </tbody>');
        tmpl_array.push('</table>');

        tmpl_array.push('</div>');
        return tmpl_array.join('');
    },
    templateDatasetModal : function(){
        var tmpl_array = [];

        tmpl_array.push('<div class="modal_table">');
        tmpl_array.push('   <table class="table table-striped table-condensed">');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>');
        tmpl_array.push('           <td><%= _.escape(item.get("name")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row">Data type</th>');
        tmpl_array.push('           <td><%= _.escape(item.get("data_type")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row">Genome build</th>');
        tmpl_array.push('           <td><%= _.escape(item.get("genome_build")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('           <th scope="row">Size</th>');
        tmpl_array.push('           <td><%= _.escape(size) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row">Date uploaded (UTC)</th>');
        tmpl_array.push('           <td><%= _.escape(item.get("date_uploaded")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row">Uploaded by</th>');
        tmpl_array.push('           <td><%= _.escape(item.get("uploaded_by")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('           <tr scope="row">');
        tmpl_array.push('           <th scope="row">Data Lines</th>');
        tmpl_array.push('           <td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <th scope="row">Comment Lines</th>');
        tmpl_array.push('           <% if (item.get("metadata_comment_lines") === "") { %>');
        tmpl_array.push('               <td scope="row"><%= _.escape(item.get("metadata_comment_lines")) %></td>');
        tmpl_array.push('           <% } else { %>');
        tmpl_array.push('               <td scope="row">unknown</td>');
        tmpl_array.push('           <% } %>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row">Number of Columns</th>');
        tmpl_array.push('           <td scope="row"><%= _.escape(item.get("metadata_columns")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row">Column Types</th>');
        tmpl_array.push('           <td scope="row"><%= _.escape(item.get("metadata_column_types")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row">Miscellaneous information</th>');
        tmpl_array.push('           <td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('   </table>');
        tmpl_array.push('   <pre class="peek">');
        tmpl_array.push('   </pre>');
        tmpl_array.push('</div>');

        return tmpl_array.join('');
    },

    templateHistorySelectInModal : function(){
        var tmpl_array = [];

        tmpl_array.push('<span id="history_modal_combo" style="width:90%; margin-left: 1em; margin-right: 1em; ">');
        tmpl_array.push('Select history: ');
        tmpl_array.push('<select id="dataset_import_single" name="dataset_import_single" style="width:50%; margin-bottom: 1em; "> ');
        tmpl_array.push('   <% _.each(histories, function(history) { %>'); //history select box
        tmpl_array.push('       <option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>');
        tmpl_array.push('   <% }); %>');
        tmpl_array.push('</select>');
        tmpl_array.push('</span>');

        return tmpl_array.join('');
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

        return tmpl_array.join('');
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

        return tmpl_array.join('');
      },

    templateNewFolderInModal: function(){
        tmpl_array = [];

        tmpl_array.push('<div id="new_folder_modal">');
        tmpl_array.push('<form>');
        tmpl_array.push('<input type="text" name="Name" value="" placeholder="Name">');
        tmpl_array.push('<input type="text" name="Description" value="" placeholder="Description">');
        tmpl_array.push('</form>');
        tmpl_array.push('</div>');

        return tmpl_array.join('');
    },

// MMMMMMMMMMMMMMM
// === EVENTS ====
// MMMMMMMMMMMMMMM

      // event binding
      events: {
            'click #select-all-checkboxes' : 'selectAll',
            'click #toolbtn_bulk_import' : 'modalBulkImport',
            'click #toolbtn_dl' : 'bulkDownload',
            'click #toolbtn_create_folder' : 'createFolderFromModal',
            'click .library-dataset' : 'showDatasetDetails',
            'click .dataset_row' : 'selectClickedRow'
        },

// MMMMMMMMMMMMMMMMMM
// === FUNCTIONS ====
// MMMMMMMMMMMMMMMMMM

      //render the folder view
      render: function (options) {
        //hack to show scrollbars
        $("#center").css('overflow','auto');

        view = this;
        var that = this;

        var folderContainer = new FolderContainer({id: options.id});
        folderContainer.url = folderContainer.attributes.urlRoot + options.id + '/contents';

        folderContainer.fetch({
          success: function (container) {

            // prepare nice size strings
              for (var i = 0; i < folderContainer.attributes.folder.models.length; i++) {
                  var model = folderContainer.attributes.folder.models[i]
                  if (model.get('type') === 'file'){
                    model.set('readable_size', that.size_to_string(model.get('file_size')))
                  }
              };

              // find the upper id
              var path = folderContainer.full_path;
              var upper_folder_id;
              if (path.length === 1){ // library is above us
                upper_folder_id = 0;
              } else {
                upper_folder_id = path[path.length-2][0];
              }

              var template = _.template(that.templateFolder(), { path: folderContainer.full_path, items: folderContainer.attributes.folder.models, id: options.id, upper_folder_id: upper_folder_id });
              // var template = _.template(that.templateFolder(), { path: folderContainer.full_path, items: folderContainer.attributes.folder.models, id: options.id });
              that.$el.html(template);

            },
              error: function(){
                mod_toastr.error('An error occured :(');
              }
          })
        },

      // convert size to nice string
      size_to_string : function (size)
      {
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

      //show modal with current dataset info
      showDatasetDetails : function(event){
        // prevent default
        event.preventDefault();

        //TODO check whether we already have the data

        //load the ID of the row
        var id = $(event.target).parent().parent().parent().attr('id');
        if (typeof id === 'undefined'){
            id = $(event.target).parent().attr('id');
        }        
        if (typeof id === 'undefined'){
            id = $(event.target).parent().parent().attr('id')
        }

        //create new item
        var item = new Item();
        var histories = new GalaxyHistories();
        item.id = id;
        var self = this;

        //fetch the dataset info
        item.fetch({
          success: function (item) {
        // TODO can render here already
                //fetch user histories for import purposes
                histories.fetch({
                    success: function (histories){
                        self.renderModalAfterFetch(item, histories)
                    },
                      error: function(){
                        mod_toastr.error('An error occured during fetching histories:(');
                        self.renderModalAfterFetch(item)
                    }
                });
            },
              error: function(){
                mod_toastr.error('An error occured during loading dataset details :(');
              }
        });
    },

      // show the current dataset in a modal
      renderModalAfterFetch : function(item, histories){
        var size = this.size_to_string(item.get('file_size'));
        var template = _.template(this.templateDatasetModal(), { item : item, size : size });
            // make modal
            var self = this;
            this.modal = Galaxy.modal;
            this.modal.show({
                closing_events  : true,
                title           : 'Dataset Details',
                body            : template,
                buttons         : {
                    'Import'    : function() { self.importCurrentIntoHistory() },
                    'Download'  : function() { self.downloadCurrent() },
                    'Close'     : function() { self.modal.hide() }
                }
            });
            
            $(".peek").html(item.get("peek"));

            // show the import-into-history footer only if the request for histories succeeded
            if (typeof history.models !== undefined){
                var history_footer_tmpl = _.template(this.templateHistorySelectInModal(), {histories : histories.models});
                $(this.modal.elMain).find('.buttons').prepend(history_footer_tmpl);
                // preset last selected history if we know it
                if (self.lastSelectedHistory.length > 0) {
                    $(this.modal.elMain).find('#dataset_import_single').val(self.lastSelectedHistory);
                }
            }
        },

        // download dataset shown currently in modal
        downloadCurrent : function(){
            //disable the buttons
            this.modal.disableButton('Import');
            this.modal.disableButton('Download');

            var library_dataset_id = [];
            library_dataset_id.push($('#id_row').attr('data-id'));
            var url = '/api/libraries/datasets/download/uncompressed';
            var data = {'ldda_ids' : library_dataset_id};

            // we assume the view is existent
            folderContentView.processDownload(url, data);
            this.modal.enableButton('Import');
            this.modal.enableButton('Download');
        },

        // import dataset shown currently in modal into selected history
        importCurrentIntoHistory : function(){
            //disable the buttons
            this.modal.disableButton('Import');
            this.modal.disableButton('Download');

            var history_id = $(this.modal.elMain).find('select[name=dataset_import_single] option:selected').val();
            this.lastSelectedHistory = history_id; //save selected history for further use

            var library_dataset_id = $('#id_row').attr('data-id');
            var historyItem = new HistoryItem();
            var self = this;
            historyItem.url = historyItem.urlRoot + history_id + '/contents';

            // save the dataset into selected history
            historyItem.save({ content : library_dataset_id, source : 'library' }, { success : function(){
                mod_toastr.success('Dataset imported');
                //enable the buttons
                self.modal.enableButton('Import');
                self.modal.enableButton('Download');
            }, error : function(){
                mod_toastr.error('An error occured! Dataset not imported. Please try again.')
                //enable the buttons
                self.modal.enableButton('Import');
                self.modal.enableButton('Download');
            }
        });
        },

        // select all datasets
        selectAll : function (event) {
             var selected = event.target.checked;
             that = this;
             // Iterate each checkbox
             $(':checkbox').each(function () { 
                this.checked = selected; 
                $row = $(this.parentElement.parentElement);
                // Change color of selected/unselected
                (selected) ? that.makeDarkRow($row) : that.makeWhiteRow($row);
            });
             // Show the tools in menu
             this.checkTools();
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
                this.checkTools();
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

        // show toolbar in case something is selected
        checkTools : function(){
            var checkedValues = $('#folder_table').find(':checked');
            if(checkedValues.length > 0){
                $('#toolbtn_bulk_import').show();
                $('#toolbtn_dl').show();
            } else {
                $('#toolbtn_bulk_import').hide();
                $('#toolbtn_dl').hide();
            }
        },

        // show bulk import modal
        modalBulkImport : function(){
            var self = this;
            // fetch histories
            var histories = new GalaxyHistories();
            histories.fetch({
                    success: function (histories){
                        // make modal
                        var history_modal_tmpl =  _.template(self.templateBulkImportInModal(), {histories : histories.models});
                        self.modal = Galaxy.modal;
                        self.modal.show({
                            closing_events  : true,
                            title           : 'Import into History',
                            body            : history_modal_tmpl,
                            buttons         : {
                                'Import'    : function() {self.importAllIntoHistory()},
                                'Close'     : function() {self.modal.hide();}
                            }
                        });
                    },
                    error: function(){
                      mod_toastr.error('An error occured :(');
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
                if (this.parentElement.parentElement.id != '') {
                    dataset_ids.push(this.parentElement.parentElement.id);
                }
            });
            var progress_bar_tmpl = _.template(this.templateProgressBar(), { history_name : history_name });
            $(this.modal.elMain).find('.modal-body').html(progress_bar_tmpl);

            // init the progress bar
            var progressStep = 100 / dataset_ids.length;
            this.initProgress(progressStep);

            // prepare the dataset objects to be imported
            var datasets_to_import = [];
            for (var i = dataset_ids.length - 1; i >= 0; i--) {
                library_dataset_id = dataset_ids[i];
                var historyItem = new HistoryItem();
                var self = this;
                historyItem.url = historyItem.urlRoot + history_id + '/contents';
                historyItem.content = library_dataset_id;
                historyItem.source = 'library';
                datasets_to_import.push(historyItem);
            };

            // call the recursive function to call ajax one after each other (request FIFO queue)
            this.chainCall(datasets_to_import);
        },

        chainCall: function(history_item_set){
            var self = this;
            var popped_item = history_item_set.pop();
            if (typeof popped_item === "undefined") {
                mod_toastr.success('All datasets imported');
                this.modal.hide();
                return
            }
                var promise = $.when(popped_item.save({content: popped_item.content, source: popped_item.source})).done(function(a1){
                        self.updateProgress();
                        responses.push(a1);
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
                if (this.parentElement.parentElement.id != '') {
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
        };
      },

      // shows modal for creating folder
      createFolderFromModal: function(){
        event.preventDefault();
        event.stopPropagation();

        // create modal
        var self = this;
        this.modal = Galaxy.modal;
        this.modal.show({
            closing_events  : true,
            title           : 'Create New Folder',
            body            : this.templateNewFolderInModal(),
            buttons         : {
                'Create'    : function() {self.create_new_folder_event()},
                'Close'     : function() {self.modal.hide(); self.modal = null;}
            }
        });
      },

    // create the new folder from modal
    create_new_folder_event: function(){
        var folderDetails = this.serialize_new_folder();
        if (this.validate_new_folder(folderDetails)){
            var folder = new FolderAsModel();

            url_items = Backbone.history.fragment.split('/');
            current_folder_id = url_items[url_items.length-1];
            folder.url = folder.urlRoot + '/' + current_folder_id ;

            var self = this;
            folder.save(folderDetails, {
              success: function (folder) {
                self.modal.hide();
                mod_toastr.success('Folder created');
                self.render({id: current_folder_id});
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

    // serialize data from the form
    serialize_new_folder : function(){
        return {
            name: $("input[name='Name']").val(),
            description: $("input[name='Description']").val()
        };
    },

    // validate new library info
    validate_new_folder: function(folderDetails){
        return folderDetails.name !== '';
    }

    });

// galaxy library view
var GalaxyLibraryview = Backbone.View.extend({
    el: '#center',

    events: {
        'click #create_new_library_btn' : 'show_library_modal'
    },

    modal: null,

    collection: null,

    // initialize
    initialize : function(){
        var viewContext = this;
        this.collection = new Libraries();
        // this.collection.on('sort', this.render, this);

        this.collection.fetch({
          success: function(libraries){
            viewContext.render();
          },
          error: function(model, response){

            if (response.statusCode().status === 403){ //TODO open to public
                mod_toastr.info('Please log in first. Redirecting to login page in 3s.');   
                setTimeout(that.redirectToLogin, 3000);
            } else {
                mod_toastr.error('An error occured. Please try again.');
            }
          }
        })
        // modification of upper DOM element to show scrollbars due to the #center element inheritance
        $("#center").css('overflow','auto');
    },

    render: function (models) {
        var template = this.templateLibraryList();
        var libraries_to_render = null;

        if (this.collection !== null && typeof models === 'undefined'){
            libraries_to_render = this.collection.models;
        } else if (models !== null){
            libraries_to_render = models;
        } else {
            libraries_to_render = [];
        }
    
        this.$el.html(template({libraries: libraries_to_render, order: this.collection.sort_order}));

    },

    /** Sorts the underlying collection according to the parameters received through URL. 
        Currently supports only sorting by name. */
    sortLibraries: function(sort_by, order){
        if (sort_by === 'name'){
            if (order === 'asc'){
                this.collection.sort_order = 'asc';
                this.collection.comparator = function(libraryA, libraryB){
                      if (libraryA.get('name').toLowerCase() > libraryB.get('name').toLowerCase()) return 1; // after
                      if (libraryB.get('name').toLowerCase() > libraryA.get('name').toLowerCase()) return -1; // before
                      return 0; // equal
                }
            } else if (order === 'desc'){
                this.collection.sort_order = 'desc';
                this.collection.comparator = function(libraryA, libraryB){
                      if (libraryA.get('name').toLowerCase() > libraryB.get('name').toLowerCase()) return -1; // before
                      if (libraryB.get('name').toLowerCase() > libraryA.get('name').toLowerCase()) return 1; // after
                      return 0; // equal
                }
            }
            this.collection.sort();
        }

    },

// MMMMMMMMMMMMMMMMMM
// === TEMPLATES ====
// MMMMMMMMMMMMMMMMMM

    templateLibraryList: function(){
        tmpl_array = [];
        tmpl_array.push('<div class="library_container" style="width: 90%; margin: auto; margin-top: 2em; overflow: auto !important; ">');
        tmpl_array.push('');
        tmpl_array.push('<h3>Data Libraries Beta Test. This is work in progress. Please report problems & ideas via <a href="mailto:galaxy-bugs@bx.psu.edu?Subject=DataLibrariesBeta_Feedback" target="_blank">email</a> and <a href="https://trello.com/c/nwYQNFPK/56-data-library-ui-progressive-display-of-folders" target="_blank">Trello</a>.</h3>');
        tmpl_array.push('<a href="" id="create_new_library_btn" class="btn btn-primary file ">New Library</a>');
        tmpl_array.push('<table class="library_table table table-condensed">');
        tmpl_array.push('   <thead>');
        tmpl_array.push('     <th><a title="Click to reverse order" href="#sort/name/<% if(order==="desc"||order===null){print("asc")}else{print("desc")} %>">name</a> <span title="Sorted alphabetically" class="fa fa-sort-alpha-<%- order %>"></span></th>');
        tmpl_array.push('     <th>description</th>');
        tmpl_array.push('     <th>synopsis</th> ');
        tmpl_array.push('   </thead>');
        tmpl_array.push('   <tbody>');
        tmpl_array.push('       <% _.each(libraries, function(library) { %>');
        tmpl_array.push('           <tr>');
        tmpl_array.push('               <td><a href="#folders/<%- library.get("root_folder_id") %>"><%- library.get("name") %></a></td>');
        tmpl_array.push('               <td><%= _.escape(library.get("description")) %></td>');
        tmpl_array.push('               <td><%= _.escape(library.get("synopsis")) %></td>');
        tmpl_array.push('           </tr>');
        tmpl_array.push('       <% }); %>');
        tmpl_array.push('   </tbody>');
        tmpl_array.push('</table>');
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
    },

    redirectToHome: function(){
        window.location = '../';
    },    
    redirectToLogin: function(){
        window.location = '/user/login';
    },

    // show/hide create library modal
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
                'Create'    : function() {self.create_new_library_event()},
                'Close'     : function() {self.modal.hide();}
            }
        });
    },

    // create the new library from modal
    create_new_library_event: function(){
        var libraryDetails = this.serialize_new_library();
        if (this.validate_new_library(libraryDetails)){
            var library = new Library();
            var self = this;
            library.save(libraryDetails, {
              success: function (library) {
                self.collection.add(library);
                self.modal.hide();
                self.clear_library_modal();
                self.render();
                mod_toastr.success('Library created');
              },
              error: function(){
                mod_toastr.error('An error occured :(');
              }
            });
        } else {
            mod_toastr.error('Library\'s name is missing');
        }
        return false;
    },

    // clear the library modal once saved
    clear_library_modal : function(){
        $("input[name='Name']").val('');
        $("input[name='Description']").val('');
        $("input[name='Synopsis']").val('');
    },

    // serialize data from the form
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
    }
});


//ROUTER
var LibraryRouter = Backbone.Router.extend({
    routes: {
        ""                                      : "libraries",
        "sort/:sort_by/:order"                  : "sort_libraries",
        "folders/:id"                           : "folder_content",
        "folders/:folder_id/download/:format"   : "download"
    }
});

// galaxy library wrapper View
var GalaxyLibrary = Backbone.View.extend({
    // folderContentView : null,
    // galaxyLibraryview : null,

    initialize : function(){

        galaxyLibraryview = new GalaxyLibraryview();
        library_router = new LibraryRouter();
        folderContentView = new FolderContentView();

        library_router.on('route:libraries', function() {
          // render libraries list
          galaxyLibraryview.render();
        });

        library_router.on('route:sort_libraries', function(sort_by, order) {
          // sort libraries list
          galaxyLibraryview.sortLibraries(sort_by, order);
          galaxyLibraryview.render();
        });

        library_router.on('route:folder_content', function(id) {
            // if (this.folderContentView === null){
            // }
          // render folder's contents
          folderContentView.render({id: id});
        });

       library_router.on('route:download', function(folder_id, format) {
          if ($('#center').find(':checked').length === 0) { 
            // this happens rarely when there is a server/data error and client gets an actual response instead of an attachment
            // we don't know what was selected so we can't download again, we redirect to the folder provided
            library_router.navigate('folders/' + folder_id, {trigger: true, replace: true});
          } else {
            // send download stream
            folderContentView.download(folder_id, format);
            library_router.navigate('folders/' + folder_id, {trigger: false, replace: true});
          }
        });

    Backbone.history.start({pushState: false});
    }
});

// return
return {
    GalaxyApp: GalaxyLibrary
};

});
