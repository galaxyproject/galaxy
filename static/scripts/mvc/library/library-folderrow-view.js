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
var FolderRowView = Backbone.View.extend({
  // last selected history in modal for UX
  lastSelectedHistory: '',

  events: {
    'click .library-dataset' : 'showDatasetDetails'
  },

  options: {
    type: null
  },

  initialize : function(folder_item){
    this.render(folder_item);
  },

  render: function(folder_item){
    // if (typeof folder_item === 'undefined'){
      // folder_item = Galaxy.libraries.libraryFolderView.collection.get(this.$el.data('id'));
    // }
    var template = null;
    if (folder_item.get('type') === 'folder'){
      this.options.type = 'folder';
      template = this.templateRowFolder();
    } else {
      this.options.type = 'file';
      template = this.templateRowFile();
    }
    this.setElement(template({content_item:folder_item}));
    this.$el.show();
    return this;
  },

  //show modal with current dataset info
  showDatasetDetails : function(event){
    // prevent default
    event.preventDefault();

    var id = this.id;

    //create new item
    var item = new mod_library_model.Item();
    var histories = new mod_library_model.GalaxyHistories();
    item.id = id;
    var self = this;

    //fetch the dataset info
    item.fetch({
      success: function (item) {
    // TODO can start rendering here already
            //fetch user histories for import purposes
            histories.fetch({
                success: function (histories){
                    self.renderModalAfterFetch(item, histories);
                },
                  error: function(){
                    mod_toastr.error('An error occured during fetching histories:(');
                    self.renderModalAfterFetch(item);
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
                'Import'    : function() { self.importCurrentIntoHistory(); },
                'Download'  : function() { self.downloadCurrent(); },
                'Close'     : function() { self.modal.hide(); }
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

    // TODO this is dup func, unify
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

    // download dataset shown currently in modal
    downloadCurrent : function(){
        //disable the buttons
        this.modal.disableButton('Import');
        this.modal.disableButton('Download');

        var library_dataset_id = [];
        library_dataset_id.push($('#id_row').attr('data-id'));
        var url = '/api/libraries/datasets/download/uncompressed';
        var data = {'ldda_ids' : library_dataset_id};

        this.processDownload(url, data);
        this.modal.enableButton('Import');
        this.modal.enableButton('Download');
    },

  // TODO this is dup func, unify
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

    // import dataset shown currently in modal into selected history
    importCurrentIntoHistory : function(){
        //disable the buttons
        this.modal.disableButton('Import');
        this.modal.disableButton('Download');

        var history_id = $(this.modal.elMain).find('select[name=dataset_import_single] option:selected').val();
        this.lastSelectedHistory = history_id; //save selected history for further use

        var library_dataset_id = $('#id_row').attr('data-id');
        var historyItem = new mod_library_model.HistoryItem();
        var self = this;
        historyItem.url = historyItem.urlRoot + history_id + '/contents';

        // save the dataset into selected history
        historyItem.save({ content : library_dataset_id, source : 'library' }, { success : function(){
            mod_toastr.success('Dataset imported');
            //enable the buttons
            self.modal.enableButton('Import');
            self.modal.enableButton('Download');
        }, error : function(){
            mod_toastr.error('An error occured! Dataset not imported. Please try again.');
            //enable the buttons
            self.modal.enableButton('Import');
            self.modal.enableButton('Download');
        }
    });
    },

  templateRowFolder: function() {
    tmpl_array = [];

    tmpl_array.push('<tr class="folder_row light" id="<%- content_item.id %>">');
    tmpl_array.push('  <td>');
    tmpl_array.push('    <span title="Folder" class="fa fa-folder-o"></span>');
    tmpl_array.push('  </td>');
    tmpl_array.push('  <td></td>');
    tmpl_array.push('  <td>');
    tmpl_array.push('    <a href="#folders/<%- content_item.id %>"><%- content_item.get("name") %></a>');
    tmpl_array.push('    <% if (content_item.get("item_count") === 0) { %>'); // empty folder
    tmpl_array.push('      <span>(empty folder)</span>');
    tmpl_array.push('    <% } %>');
    tmpl_array.push('  </td>');
    tmpl_array.push('  <td>folder</td>');
    tmpl_array.push('  <td><%= _.escape(content_item.get("item_count")) %> item(s)</td>'); // size
    tmpl_array.push('  <td><%= _.escape(content_item.get("time_updated")) %></td>'); // time updated
    tmpl_array.push('</tr>');

    return _.template(tmpl_array.join(''));
  },

  templateRowFile: function(){
    tmpl_array = [];

    tmpl_array.push('<tr class="dataset_row light" id="<%- content_item.id %>">');
    tmpl_array.push('  <td>');
    tmpl_array.push('    <span title="Dataset" class="fa fa-file-o"></span>');
    tmpl_array.push('  </td>');
    tmpl_array.push('  <td style="text-align: center; "><input style="margin: 0;" type="checkbox"></td>');
    tmpl_array.push('  <td><a href="#" class="library-dataset"><%- content_item.get("name") %><a></td>'); // dataset
    tmpl_array.push('  <td><%= _.escape(content_item.get("data_type")) %></td>'); // data type
    tmpl_array.push('  <td><%= _.escape(content_item.get("readable_size")) %></td>'); // size
    tmpl_array.push('  <td><%= _.escape(content_item.get("time_updated")) %></td>'); // time updated
    tmpl_array.push('</tr>');

    return _.template(tmpl_array.join(''));
  },

templateDatasetModal : function(){
  var tmpl_array = [];

  tmpl_array.push('<div class="modal_table">');
  tmpl_array.push('   <table class="grid table table-striped table-condensed">');
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

  tmpl_array.push('<span id="history_modal_combo" style="width:100%; margin-left: 1em; margin-right: 1em; ">');
  tmpl_array.push('Select history: ');
  tmpl_array.push('<select id="dataset_import_single" name="dataset_import_single" style="width:40%; margin-bottom: 1em; "> ');
  tmpl_array.push('   <% _.each(histories, function(history) { %>'); //history select box
  tmpl_array.push('       <option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>');
  tmpl_array.push('   <% }); %>');
  tmpl_array.push('</select>');
  tmpl_array.push('</span>');

    return tmpl_array.join('');
}
   
});

return {
    FolderRowView: FolderRowView
};

});
