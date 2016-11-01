define([
    "layout/masthead",
    "utils/utils",
    "libs/toastr",
    "mvc/library/library-model",
    "mvc/ui/ui-select"
    ],
function( mod_masthead,
          mod_utils,
          mod_toastr,
          mod_library_model,
          mod_select
        ){

var FolderToolbarView = Backbone.View.extend({
  el: '#center',

  events: {
    'click #toolbtn_create_folder'        : 'createFolderFromModal',
    'click #toolbtn_bulk_import'          : 'modalBulkImport',
    'click #include_deleted_datasets_chk' : 'checkIncludeDeleted',
    'click #toolbtn_bulk_delete'          : 'deleteSelectedItems',
    'click .toolbtn-show-locinfo'         : 'showLocInfo',
    'click .page_size_prompt'             : 'showPageSizePrompt'

  },

  defaults: {
    'can_add_library_item'    : false,
    'contains_file_or_folder' : false,
    'chain_call_control'      : {
                                'total_number'  : 0,
                                'failed_number' : 0
                              },
    'disabled_jstree_element' : 'folders'
  },

  modal : null,

  // directory browsing object
  jstree: null,

  // user's histories
  histories : null,

  // genome select
  select_genome : null,

  // extension select
  select_extension : null,

  // extension types
  list_extensions :[],

  // datatype placeholder for extension auto-detection
  auto: {
      id          : 'auto',
      text        : 'Auto-detect',
      description : 'This system will try to detect the file type automatically.' +
                    ' If your file is not detected properly as one of the known formats,' +
                    ' it most likely means that it has some format problems (e.g., different' +
                    ' number of columns on different rows). You can still coerce the system' +
                    ' to set your data to the format you think it should be.' +
                    ' You can also upload compressed files, which will automatically be decompressed.'
  },

  // genomes
  list_genomes : [],

  initialize: function(options){
    this.options = _.defaults( options || {}, this.defaults );
    this.fetchExtAndGenomes();
    this.render();
  },

  render: function(options){
    this.options = _.extend( this.options, options );
    var toolbar_template = this.templateToolBar();
    var template_defaults = {
        id: this.options.id,
        is_admin: false,
        is_anonym: true,
        mutiple_add_dataset_options: false
    }
    if (Galaxy.user){
      template_defaults.is_admin = Galaxy.user.isAdmin();
      template_defaults.is_anonym = Galaxy.user.isAnonymous();
      if ( Galaxy.config.user_library_import_dir !== null || Galaxy.config.allow_library_path_paste !== false || Galaxy.config.library_import_dir !== null ){
        template_defaults.mutiple_add_dataset_options = true;
      }
    }
    this.$el.html(toolbar_template(template_defaults));
  },

  /**
   * Called from FolderListView when needed.
   * @param  {object} options common options
   */
  renderPaginator: function( options ){
      this.options = _.extend( this.options, options );
      var paginator_template = this.templatePaginator();
      $("body").find( '.folder-paginator' ).html( paginator_template({
          id: this.options.id,
          show_page: parseInt( this.options.show_page ),
          page_count: parseInt( this.options.page_count ),
          total_items_count: this.options.total_items_count,
          items_shown: this.options.items_shown
      }));
  },

  configureElements: function(options){
    this.options = _.extend(this.options, options);

    if (this.options.can_add_library_item === true){
      $('.add-library-items').show();
    } else{
      $('.add-library-items').hide();
    }
    if (this.options.contains_file_or_folder === true){
      if (Galaxy.user){
        if (!Galaxy.user.isAnonymous()){
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
  createFolderFromModal: function( event ){
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
          folder.url = folder.urlRoot + current_folder_id ;

          folder.save(folderDetails, {
            success: function (folder) {
              Galaxy.modal.hide();
              mod_toastr.success('Folder created.');
              folder.set({'type' : 'folder'});
              Galaxy.libraries.folderListView.collection.add(folder);
            },
            error: function(model, response){
              Galaxy.modal.hide();
              if (typeof response.responseJSON !== "undefined"){
                mod_toastr.error(response.responseJSON.err_msg);
              } else {
                mod_toastr.error('An error ocurred.');
              }
            }
          });
      } else {
          mod_toastr.error('Folder\'s name is missing.');
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
          mod_toastr.info('You must select some datasets first.');
      } else {
          this.refreshUserHistoriesList(function(that){
            var template = that.templateBulkImportInModal();
            that.modal = Galaxy.modal;
            that.modal.show({
                closing_events  : true,
                title           : 'Import into History',
                body            : template({histories : that.histories.models}),
                buttons         : {
                    'Import'    : function() {that.importAllIntoHistory();},
                    'Close'     : function() {Galaxy.modal.hide();}
                }
            });
          });
      }
  },

  refreshUserHistoriesList: function(callback){
    var that = this;
    this.histories = new mod_library_model.GalaxyHistories();
    this.histories.fetch({
      success: function (){
        callback(that);
      },
      error: function(model, response){
        if (typeof response.responseJSON !== "undefined"){
          mod_toastr.error(response.responseJSON.err_msg);
        } else {
          mod_toastr.error('An error ocurred.');
        }
      }
    });
  },

  /**
   * Import all selected datasets into history.
   */
  importAllIntoHistory : function (){
    this.modal.disableButton('Import');
    var new_history_name = this.modal.$('input[name=history_name]').val();
    var that = this;
    if (new_history_name !== ''){
      $.post( Galaxy.root + 'api/histories', {name: new_history_name})
        .done(function( new_history ) {
          that.options.last_used_history_id = new_history.id;
          that.processImportToHistory(new_history.id, new_history.name);
        })
        .fail(function( xhr, status, error ) {
          mod_toastr.error('An error ocurred.');
        })
        .always(function() {
          that.modal.enableButton('Import');
        });
    } else {
      var history_id = $("select[name=dataset_import_bulk] option:selected").val();
      this.options.last_used_history_id = history_id;
      var history_name = $("select[name=dataset_import_bulk] option:selected").text();
      this.processImportToHistory(history_id, history_name);
      this.modal.enableButton('Import');
    }
  },

  processImportToHistory: function( history_id, history_name ){
    var dataset_ids = [];
    var folder_ids = [];
    $('#folder_table').find(':checked').each(function(){
        if ($(this.parentElement.parentElement).data('id') !== '' && this.parentElement.parentElement.classList.contains('dataset_row') ) {
            dataset_ids.push($(this.parentElement.parentElement).data('id'));
        } else if ($(this.parentElement.parentElement).data('id') !== '' && this.parentElement.parentElement.classList.contains('folder_row') ) {
            folder_ids.push($(this.parentElement.parentElement).data('id'));
        }
    });
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

    // prepare the folder objects to be imported
    var folders_to_import = [];
    for (var i = folder_ids.length - 1; i >= 0; i--) {
        var library_folder_id = folder_ids[i];
        var historyItem = new mod_library_model.HistoryItem();
        historyItem.url = historyItem.urlRoot + history_id + '/contents';
        historyItem.content = library_folder_id;
        historyItem.source = 'library_folder';
        datasets_to_import.push(historyItem);
    }

    this.initChainCallControl( { length: datasets_to_import.length, action: 'to_history', history_name: history_name } );
    // set the used history as current so user will see the last one
    // that he imported into in the history panel on the 'analysis' page
    jQuery.getJSON( Galaxy.root + 'history/set_as_current?id=' + history_id  );
    this.chainCallImportingIntoHistory( datasets_to_import, history_name );
  },

  /**
   * Update the progress bar in modal window.
   */
  updateProgress: function(){
      this.progress += this.progressStep;
      $( '.progress-bar-import' ).width( Math.round( this.progress ) + '%' );
      txt_representation = Math.round( this.progress ) + '% Complete';
      $( '.completion_span' ).text( txt_representation );
  },

  /**
   * download selected datasets
   * @param  {str} folder_id id of the current folder
   * @param  {str} format    requested archive format
   */
  download : function( folder_id, format ){
    var dataset_ids = [];
    var folder_ids = [];
        $( '#folder_table' ).find( ':checked' ).each( function(){
            if ( $(this.parentElement.parentElement).data('id') !== '' && this.parentElement.parentElement.classList.contains('dataset_row') ) {
                dataset_ids.push( $(this.parentElement.parentElement).data('id') );
            } else if ( $(this.parentElement.parentElement).data('id') !== '' && this.parentElement.parentElement.classList.contains('folder_row') ) {
                folder_ids.push( $(this.parentElement.parentElement).data('id') );
            }
        } );
    var url = Galaxy.root + 'api/libraries/datasets/download/' + format;
    var data = { 'ld_ids' : dataset_ids, 'folder_ids' : folder_ids };
    this.processDownload( url, data, 'get' );
  },

  /**
   * Create hidden form and submit it through POST
   * to initialize the download.
   * @param  {str} url    url to call
   * @param  {obj} data   data to include in the request
   * @param  {str} method method of the request
   */
  processDownload: function( url, data, method ){
    if ( url && data ){
      // data can be string of parameters or array/object
      data = typeof data === 'string' ? data : $.param( data );
      // split params into form inputs
      var inputs = '';
      $.each( data.split( '&' ), function(){
              var pair = this.split( '=' );
              inputs+='<input type="hidden" name="'+ pair[0] +'" value="'+ pair[1] +'" />';
      });
      // send request
      $('<form action="'+ url +'" method="'+ (method||'post') +'">'+inputs+'</form>')
      .appendTo( 'body' ).submit().remove();
      mod_toastr.info( 'Your download will begin soon.' );
    } else {
      mod_toastr.error( 'An error occurred.' );
    }
  },

  addFilesFromHistoryModal: function(){
    this.refreshUserHistoriesList( function( self ){
      self.modal = Galaxy.modal;
      var template_modal = self.templateAddFilesFromHistory();
      var folder_name = self.options.full_path[self.options.full_path.length - 1][1]
      self.modal.show({
          closing_events  : true,
          title           : 'Adding datasets from your history to folder ' + folder_name,
          body            : template_modal({histories: self.histories.models}),
          buttons         : {
              'Add'       : function() {self.addAllDatasetsFromHistory();},
              'Close'     : function() {Galaxy.modal.hide();}
          },
          closing_callback: function(){
            Galaxy.libraries.library_router.back();
          }
      });

      // user should always have a history, even anonymous user
      if (self.histories.models.length > 0){
        self.fetchAndDisplayHistoryContents(self.histories.models[0].id);
        $( "#dataset_add_bulk" ).change(function(event) {
          self.fetchAndDisplayHistoryContents(event.target.value);
        });
      } else {
        mod_toastr.error( 'An error ocurred.' );
      }
    });
  },

  /**
   * Create modal for importing from Galaxy path.
   * This feature is admin-only.
   */
  importFilesFromPathModal: function(){
    var that = this;
    this.modal = Galaxy.modal;
    var template_modal = this.templateImportPathModal();
    this.modal.show({
        closing_events  : true,
        title           : 'Please enter paths to import',
        body            : template_modal({}),
        buttons         : {
            'Import'    : function() { that.importFromPathsClicked(that); },
            'Close'     : function() { Galaxy.modal.hide(); }
        },
        closing_callback: function(){
          //  TODO: should not trigger routes outside of the router
          Galaxy.libraries.library_router.navigate( 'folders/' + that.id, { trigger: true } );
        }
    });
    this.renderSelectBoxes();
  },

  /**
   * Request all extensions and genomes from Galaxy
   * and save them sorted in arrays.
   */
  fetchExtAndGenomes: function(){
    var that = this;
    mod_utils.get({
        url      :  Galaxy.root + "api/datatypes?extension_only=False",
        success  :  function( datatypes ) {
                        that.list_extensions = [];
                        for (key in datatypes) {
                            that.list_extensions.push({
                                id              : datatypes[key].extension,
                                text            : datatypes[key].extension,
                                description     : datatypes[key].description,
                                description_url : datatypes[key].description_url
                            });
                        }
                        that.list_extensions.sort(function(a, b) {
                            return a.id > b.id ? 1 : a.id < b.id ? -1 : 0;
                        });
                        that.list_extensions.unshift(that.auto);
                    },
        cache    : true
      });
    mod_utils.get({
        url     :    Galaxy.root + "api/genomes",
        success : function( genomes ) {
                    that.list_genomes = [];
                    for ( key in genomes ) {
                        that.list_genomes.push({
                            id      : genomes[key][1],
                            text    : genomes[key][0]
                        });
                    }
                    that.list_genomes.sort(function(a, b) {
                        return a.id > b.id ? 1 : a.id < b.id ? -1 : 0;
                    });
                },
        cache   : true
    });
  },

  renderSelectBoxes: function(){
    // This won't work properly unlesss we already have the data fetched.
    // See this.fetchExtAndGenomes()
    // TODO switch to common resources:
    // https://trello.com/c/dIUE9YPl/1933-ui-common-resources-and-data-into-galaxy-object
    var that = this;
    this.select_genome = new mod_select.View( {
        css: 'library-genome-select',
        data: that.list_genomes,
        container: Galaxy.modal.$el.find( '#library_genome_select' ),
        value: '?'
    } );
    this.select_extension = new mod_select.View({
      css: 'library-extension-select',
      data: that.list_extensions,
      container: Galaxy.modal.$el.find( '#library_extension_select' ),
      value: 'auto'
    });
  },

  /**
   * Create modal for importing from given directory
   * on Galaxy. Bind jQuery events.
   */
  importFilesFromGalaxyFolderModal: function( options ){
    var that = this;
    var template_modal = this.templateBrowserModal();
    this.modal = Galaxy.modal;
    this.modal.show({
      closing_events  : true,
      title           : 'Please select folders or files',
      body            : template_modal({}),
      buttons         : {
          'Import'    : function() {
            that.importFromJstreePath( that, options );
          },
          'Close'     : function() {
            Galaxy.modal.hide();
          }
      },
      closing_callback: function(){
        //  TODO: should not trigger routes outside of the router
        Galaxy.libraries.library_router.navigate('folders/' + that.id, {trigger: true});
      }
    });

    $('.libimport-select-all').bind("click", function(){
      $('#jstree_browser').jstree("check_all");
    });
    $('.libimport-select-none').bind("click", function(){
      $('#jstree_browser').jstree("uncheck_all");
    });

    this.renderSelectBoxes();
    options.disabled_jstree_element = 'folders';
    this.renderJstree( options );

    $( 'input[type=radio]' ).change( function( event ){
        if (event.target.value ==='jstree-disable-folders') {
          options.disabled_jstree_element = 'folders';
          that.renderJstree( options );
          $('.jstree-folders-message').hide();
          $('.jstree-preserve-structure').hide();
          $('.jstree-link-files').hide();
          $('.jstree-files-message').show();
        } else if ( event.target.value ==='jstree-disable-files' ){
          $('.jstree-files-message').hide();
          $('.jstree-folders-message').show();
          $('.jstree-link-files').show();
          $('.jstree-preserve-structure').show();
          options.disabled_jstree_element = 'files';
          that.renderJstree( options );
        }
      }
    );
  },

  /**
   * Fetch the contents of user directory on Galaxy
   * and render jstree component based on received
   * data.
   * @param  {[type]} options [description]
   */
  renderJstree: function( options ){
    var that = this;
    this.options = _.extend( this.options, options );
    var target = options.source || 'userdir';
    var disabled_jstree_element = this.options.disabled_jstree_element;
    this.jstree = new mod_library_model.Jstree();
    this.jstree.url = this.jstree.urlRoot +
                        '?target=' + target +
                        '&format=jstree' +
                        '&disable=' + disabled_jstree_element;
    this.jstree.fetch({
      success: function(model, response){
        // This is to prevent double jquery load. I think. Carl is magician.
        define( 'jquery', function(){ return jQuery; });
        // Now we need jstree, time to lazy load it.
        require([ 'libs/jquery/jstree' ], function(jstree){
          $('#jstree_browser').jstree("destroy");
          $('#jstree_browser').jstree({
            'core':{
              'data': model
            },
            'plugins': ['types', 'checkbox'],
            'types': {
              "folder": {
                "icon": "jstree-folder"
              },
              "file": {
                "icon": "jstree-file"
              }
            },
            'checkbox': {
              three_state: false
            }
          });
        });
      },
      error: function(model, response){
        if (typeof response.responseJSON !== "undefined"){
          if (response.responseJSON.err_code === 404001){
            mod_toastr.warning(response.responseJSON.err_msg);
          } else{
            mod_toastr.error(response.responseJSON.err_msg);
          }
        } else {
          mod_toastr.error('An error ocurred.');
        }
      }
    })
  },

  /**
   * Take the paths from the textarea, split it, create
   * a request queue and call a function that starts sending
   * one by one to be imported on the server.
   */
  importFromPathsClicked: function(){
    var preserve_dirs = this.modal.$el.find('.preserve-checkbox').is(':checked');
    var link_data = this.modal.$el.find('.link-checkbox').is(':checked');
    var file_type = this.select_extension.value();
    var dbkey = this.select_genome.value();
    var paths = $('textarea#import_paths').val();
    var valid_paths = [];
    if (!paths){
      mod_toastr.info('Please enter a path relative to Galaxy root.');
    } else {
      this.modal.disableButton('Import');
      paths = paths.split('\n');
      for (var i = paths.length - 1; i >= 0; i--) {
        trimmed = paths[i].trim();
        if (trimmed.length!==0){
          valid_paths.push(trimmed);
        }
      };
      this.initChainCallControl( { length: valid_paths.length, action: 'adding_datasets' } );
      this.chainCallImportingFolders( { paths: valid_paths,
                                        preserve_dirs: preserve_dirs,
                                        link_data: link_data,
                                        source: 'admin_path',
                                        file_type: file_type,
                                        dbkey: dbkey } );
    }
  },

  /**
   * Initialize the control of chaining requests
   * in the current modal.
   * @param {int} length The number of items in the chain call.
   */
  initChainCallControl: function( options ){
    var template;
    switch( options.action ){
      case "adding_datasets":
        template = this.templateAddingDatasetsProgressBar();
        this.modal.$el.find( '.modal-body' ).html( template( { folder_name : this.options.folder_name } ) );
        break;
      case "deleting_datasets":
        template = this.templateDeletingItemsProgressBar();
        this.modal.$el.find( '.modal-body' ).html( template() );
        break;
      case "to_history":
        template = this.templateImportIntoHistoryProgressBar();
        this.modal.$el.find( '.modal-body' ).html( template( { history_name : options.history_name } ) );
        break;
      default:
        Galaxy.emit.error( 'Wrong action specified.', 'datalibs');
        break;
    }

    // var progress_bar_tmpl = this.templateAddingDatasetsProgressBar();
    // this.modal.$el.find( '.modal-body' ).html( progress_bar_tmpl( { folder_name : this.options.folder_name } ) );
    this.progress = 0;
    this.progressStep = 100 / options.length;
    this.options.chain_call_control.total_number = options.length;
    this.options.chain_call_control.failed_number = 0;
  },

  /**
   * Take the selected items from the jstree, create a request queue
   * and send them one by one to the server for importing into
   * the current folder.
   *
   * jstree.js has to be loaded before
   * @see renderJstree
   */
  importFromJstreePath: function ( that, options ){
    var all_nodes = $( '#jstree_browser' ).jstree().get_selected( true );
    // remove the disabled elements that could have been trigerred with the 'select all'
    selected_nodes = _.filter(all_nodes, function(node){ return node.state.disabled == false; })
    var preserve_dirs = this.modal.$el.find( '.preserve-checkbox' ).is( ':checked' );
    var link_data = this.modal.$el.find( '.link-checkbox' ).is( ':checked' );
    var file_type = this.select_extension.value();
    var dbkey = this.select_genome.value();
    var selection_type = selected_nodes[0].type;
    var paths = [];
    if ( selected_nodes.length < 1 ){
      mod_toastr.info( 'Please select some items first.' );
    } else {
      this.modal.disableButton( 'Import' );
      for ( var i = selected_nodes.length - 1; i >= 0; i-- ){
        if ( selected_nodes[i].li_attr.full_path !== undefined ){
          paths.push( selected_nodes[i].li_attr.full_path );
        }
      }
      this.initChainCallControl( { length: paths.length, action: 'adding_datasets' } );
      if ( selection_type === 'folder' ){
        var full_source = options.source + '_folder';
        this.chainCallImportingFolders( { paths: paths,
                                          preserve_dirs: preserve_dirs,
                                          link_data: link_data,
                                          source: full_source,
                                          file_type: file_type,
                                          dbkey: dbkey } );
      } else if ( selection_type === 'file' ){
        var full_source = options.source + '_file';
        this.chainCallImportingUserdirFiles( { paths : paths,
                                               file_type: file_type,
                                               dbkey: dbkey,
                                               source: full_source } );
      }
    }
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
      error: function(model, response){
        if (typeof response.responseJSON !== "undefined"){
          mod_toastr.error(response.responseJSON.err_msg);
        } else {
          mod_toastr.error('An error ocurred.');
        }
      }
    });
  },

  /**
   * Import all selected datasets from history into the current folder.
   */
  addAllDatasetsFromHistory : function (){
    var checked_hdas = this.modal.$el.find( '#selected_history_content' ).find( ':checked' );
    var history_dataset_ids = [];
    var hdas_to_add = [];
    if ( checked_hdas.length < 1 ){
      mod_toastr.info( 'You must select some datasets first.' );
    } else {
      this.modal.disableButton( 'Add' );
      checked_hdas.each(function(){
        var hid = $( this.parentElement ).data( 'id' );
          if ( hid ) {
            history_dataset_ids.push( hid );
          }
      });
      for ( var i = history_dataset_ids.length - 1; i >= 0; i-- ) {
        history_dataset_id = history_dataset_ids[i];
        var folder_item = new mod_library_model.Item();
        folder_item.url = Galaxy.root + 'api/folders/' + this.options.id + '/contents';
        folder_item.set( { 'from_hda_id':history_dataset_id } );
        hdas_to_add.push( folder_item );
      }
      this.initChainCallControl( { length: hdas_to_add.length, action: 'adding_datasets' } );
      this.chainCallAddingHdas( hdas_to_add );
    }
  },

  /**
   * Take array of empty history items and make request for each of them
   * to create it on server. Update progress in between calls.
   * @param  {array} history_item_set array of empty history items
   * @param  {str} history_name     name of the history to import to
   */
  chainCallImportingIntoHistory: function( history_item_set, history_name ){
    var self = this;
    var popped_item = history_item_set.pop();
    if ( typeof popped_item == "undefined" ) {
      if ( this.options.chain_call_control.failed_number === 0 ){
        mod_toastr.success( 'Selected datasets imported into history. Click this to start analyzing it.', '', { onclick: function() { window.location=Galaxy.root } } );
      } else if ( this.options.chain_call_control.failed_number === this.options.chain_call_control.total_number ){
        mod_toastr.error( 'There was an error and no datasets were imported into history.' );
      } else if ( this.options.chain_call_control.failed_number < this.options.chain_call_control.total_number ){
        mod_toastr.warning( 'Some of the datasets could not be imported into history. Click this to see what was imported.', '', { onclick: function() { window.location=Galaxy.root } } );
      }
      Galaxy.modal.hide();
      return true;
    }
    var promise = $.when( popped_item.save( { content: popped_item.content, source: popped_item.source } ) );

    promise.done( function(){
              self.updateProgress();
              self.chainCallImportingIntoHistory( history_item_set, history_name );
            } )
            .fail( function(){
              self.options.chain_call_control.failed_number += 1;
              self.updateProgress();
              self.chainCallImportingIntoHistory( history_item_set, history_name );
            } );
  },

  /**
   * Take the array of paths and createa request for each of them
   * calling them in chain. Update the progress bar in between each.
   * @param  {array} paths           paths relative to user folder on Galaxy
   */
  chainCallImportingUserdirFiles: function( options ){

    var that = this;
    var popped_item = options.paths.pop();
    if ( typeof popped_item === "undefined" ) {
      if ( this.options.chain_call_control.failed_number === 0 ){
        mod_toastr.success( 'Selected files imported into the current folder' );
        Galaxy.modal.hide();
      } else {
        mod_toastr.error( 'An error occured.' );
      }
      return true;
    }
    var promise = $.when( $.post( Galaxy.root + 'api/libraries/datasets?encoded_folder_id=' + that.id +
                                                       '&source=' + options.source +
                                                       '&path=' + popped_item +
                                                       '&file_type=' + options.file_type +
                                                       '&dbkey=' + options.dbkey ) )
    promise.done( function( response ){
              that.updateProgress();
              that.chainCallImportingUserdirFiles( options );
            } )
            .fail( function(){
              that.options.chain_call_control.failed_number += 1;
              that.updateProgress();
              that.chainCallImportingUserdirFiles( options );
            } );
  },

  /**
   * Take the array of paths and createa request for each of them
   * calling them in chain. Update the progress bar in between each.
   * @param  {array} paths           paths relative to Galaxy root folder
   * @param  {boolean} preserve_dirs indicates whether to preserve folder structure
   * @param  {boolean} link_data     copy files to Galaxy or link instead
   * @param  {str} source            string representing what type of folder
   *                                 is the source of import
   */
  chainCallImportingFolders: function( options ){
    // TODO need to check which paths to call
    var that = this;
    var popped_item = options.paths.pop();
    if (typeof popped_item == "undefined") {
      if (this.options.chain_call_control.failed_number === 0){
        mod_toastr.success('Selected folders and their contents imported into the current folder.');
        Galaxy.modal.hide();
      } else {
        // TODO better error report
        mod_toastr.error('An error occured.');
      }
      return true;
    }
    var promise = $.when( $.post( Galaxy.root + 'api/libraries/datasets?encoded_folder_id=' + that.id +
                                                          '&source=' + options.source +
                                                          '&path=' + popped_item +
                                                          '&preserve_dirs=' + options.preserve_dirs +
                                                          '&link_data=' + options.link_data +
                                                          '&file_type=' + options.file_type +
                                                          '&dbkey=' + options.dbkey ) )
    promise.done(function(response){
              that.updateProgress();
              that.chainCallImportingFolders( options );
            })
            .fail(function(){
              that.options.chain_call_control.failed_number += 1;
              that.updateProgress();
              that.chainCallImportingFolders( options );
            });
  },

  /**
   * Take the array of hdas and create a request for each.
   * Call them in chain and update progress bar in between each.
   * @param  {array} hdas_set array of empty hda objects
   */
  chainCallAddingHdas: function( hdas_set ){
    var self = this;
    this.added_hdas = new mod_library_model.Folder();
    var popped_item = hdas_set.pop();
    if ( typeof popped_item == "undefined" ) {
      if ( this.options.chain_call_control.failed_number === 0 ){
        mod_toastr.success( 'Selected datasets from history added to the folder' );
      } else if ( this.options.chain_call_control.failed_number === this.options.chain_call_control.total_number ){
        mod_toastr.error( 'There was an error and no datasets were added to the folder.' );
      } else if ( this.options.chain_call_control.failed_number < this.options.chain_call_control.total_number ){
        mod_toastr.warning( 'Some of the datasets could not be added to the folder' );
      }
      Galaxy.modal.hide();
      return this.added_hdas;
    }
    var promise = $.when( popped_item.save( { from_hda_id: popped_item.get( 'from_hda_id' ) } ) );

    promise.done( function( model ){
              Galaxy.libraries.folderListView.collection.add( model );
              self.updateProgress();
              self.chainCallAddingHdas( hdas_set );
            })
            .fail( function(){
              self.options.chain_call_control.failed_number += 1;
              self.updateProgress();
              self.chainCallAddingHdas( hdas_set );
            });
  },

  /**
   * Take the array of lddas, create request for each and
   * call them in chain. Update progress bar in between each.
   * @param  {array} lddas_set array of lddas to delete
   */
  chainCallDeletingItems: function( items_to_delete ){
  var self = this;
  this.deleted_items = new mod_library_model.Folder();
  var popped_item = items_to_delete.pop();
  if ( typeof popped_item === "undefined" ) {
    if ( this.options.chain_call_control.failed_number === 0 ){
      mod_toastr.success( 'Selected items were deleted.' );
    } else if ( this.options.chain_call_control.failed_number === this.options.chain_call_control.total_number ){
      mod_toastr.error( 'There was an error and no items were deleted. Please make sure you have sufficient permissions.' );
    } else if ( this.options.chain_call_control.failed_number < this.options.chain_call_control.total_number ){
      mod_toastr.warning( 'Some of the items could not be deleted. Please make sure you have sufficient permissions.' );
    }
    Galaxy.modal.hide();
    return this.deleted_items;
  }
  var promise = $.when( popped_item.destroy() );

  promise.done( function( item ){
            Galaxy.libraries.folderListView.collection.remove( popped_item.id );
            self.updateProgress();
            // add the deleted item to collection, triggers rendering
            if ( Galaxy.libraries.folderListView.options.include_deleted ){
              var updated_item = null;
              if (item.type === 'folder' || item.model_class === 'LibraryFolder'){
                updated_item = new mod_library_model.FolderAsModel( item );
              } else if (item.type === 'file' || item.model_class === 'LibraryDataset'){
                updated_item = new mod_library_model.Item( item );
              } else {
                Galaxy.emit.error('Unknown library item type found.', 'datalibs');
                Galaxy.emit.error(item.type || item.model_class, 'datalibs');
              }
              Galaxy.libraries.folderListView.collection.add( updated_item );
            }
            self.chainCallDeletingItems( items_to_delete );
          })
          .fail( function(){
            self.options.chain_call_control.failed_number += 1;
            self.updateProgress();
            self.chainCallDeletingItems( items_to_delete );
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
   * Delete the selected items. Atomic. One by one.
   */
  deleteSelectedItems: function(){
    var checkedValues = $('#folder_table').find(':checked');
    if(checkedValues.length === 0){
        mod_toastr.info('You must select at least one item for deletion.');
    } else {
      var template = this.templateDeletingItemsProgressBar();
      this.modal = Galaxy.modal;
      this.modal.show({
          closing_events  : true,
          title           : 'Deleting selected items',
          body            : template({}),
          buttons         : {
              'Close'     : function() {Galaxy.modal.hide();}
          }
      });
      // init the control counters
      this.options.chain_call_control.total_number = 0;
      this.options.chain_call_control.failed_number = 0;

      var dataset_ids = [];
      var folder_ids = [];
      checkedValues.each(function(){
          if ($(this.parentElement.parentElement).data('id') !== undefined) {
              if ($(this.parentElement.parentElement).data('id').substring(0,1) == 'F'){
                folder_ids.push($(this.parentElement.parentElement).data('id'));
              } else {
                dataset_ids.push($(this.parentElement.parentElement).data('id'));
              }
          }
      });
      // init the progress bar
      var items_total = dataset_ids.length + folder_ids.length
      this.progressStep = 100 / items_total;
      this.progress = 0;

      // prepare the dataset items to be added
      var items_to_delete = [];
      for (var i = dataset_ids.length - 1; i >= 0; i--) {
          var dataset = new mod_library_model.Item({id:dataset_ids[i]});
          items_to_delete.push(dataset);
      }
      for (var i = folder_ids.length - 1; i >= 0; i--) {
          var folder = new mod_library_model.FolderAsModel({id:folder_ids[i]});
          items_to_delete.push(folder);
      }

      this.options.chain_call_control.total_number = items_total.length;
      // call the recursive function to call ajax one after each other (request FIFO queue)
      this.chainCallDeletingItems(items_to_delete);
    }
  },


  showLocInfo: function(){
    var library = null;
    var that = this;
    if (Galaxy.libraries.libraryListView !== null){
      library = Galaxy.libraries.libraryListView.collection.get(this.options.parent_library_id);
      this.showLocInfoModal(library);
    } else {
      library = new mod_library_model.Library({id: this.options.parent_library_id});
      library.fetch({
        success: function(){
          that.showLocInfoModal(library);
        },
        error: function(model, response){
          if (typeof response.responseJSON !== "undefined"){
            mod_toastr.error(response.responseJSON.err_msg);
          } else {
            mod_toastr.error('An error ocurred.');
          }
        }
      })
    }
  },

  showLocInfoModal: function(library){
    var that = this;
    var template = this.templateLocInfoInModal();
    this.modal = Galaxy.modal;
    this.modal.show({
        closing_events  : true,
        title           : 'Location Details',
        body            : template({library: library, options: that.options}),
        buttons         : {
            'Close'     : function() {Galaxy.modal.hide();}
        }
    });
  },

  showImportModal: function(options){
    switch(options.source){
      case "history":
        this.addFilesFromHistoryModal();
        break;
      case "importdir":
        this.importFilesFromGalaxyFolderModal( { source: 'importdir' } );
        break;
      case "path":
        this.importFilesFromPathModal();
        break;
      case "userdir":
        this.importFilesFromGalaxyFolderModal( { source: 'userdir' } );
        break;
      default:
        Galaxy.libraries.library_router.back();
        mod_toastr.error('Invalid import source.');
        break;
    }
  },

  /**
   * Show user the prompt to change the number of items shown on page.
   */
  showPageSizePrompt: function(){
    var folder_page_size = prompt( 'How many items per page do you want to see?', Galaxy.libraries.preferences.get( 'folder_page_size' ) );
    if ( ( folder_page_size != null ) && ( folder_page_size == parseInt( folder_page_size ) ) ) {
        Galaxy.libraries.preferences.set( { 'folder_page_size': parseInt( folder_page_size ) } );
        Galaxy.libraries.folderListView.render( { id: this.options.id, show_page: 1 } );
    }
  },

  templateToolBar: function(){
    return _.template([
    // container start
    '<div class="library_style_container">',
      // toolbar start
      '<div id="library_toolbar">',
        '<form class="form-inline" role="form">',
          '<span><strong>DATA LIBRARIES</strong></span>',
          // paginator will append here
          '<span class="library-paginator folder-paginator"></span>',
          '<div class="checkbox toolbar-item logged-dataset-manipulation" style="height: 20px; display:none;">',
            '<label>',
              '<input id="include_deleted_datasets_chk" type="checkbox">include deleted</input>',
            '</label>',
          '</div>',
          '<button style="display:none;" data-toggle="tooltip" data-placement="top" title="Create New Folder" id="toolbtn_create_folder" class="btn btn-default primary-button add-library-items toolbar-item" type="button">',
            '<span class="fa fa-plus"></span><span class="fa fa-folder"></span>',
          '</button>',
          '<% if(mutiple_add_dataset_options) { %>',
          '<div class="btn-group add-library-items" style="display:none;">',
            '<button title="Add Datasets to Current Folder" id="" type="button" class="primary-button dropdown-toggle" data-toggle="dropdown">',
              '<span class="fa fa-plus"></span><span class="fa fa-file"></span><span class="caret"></span>',
            '</button>',
            '<ul class="dropdown-menu" role="menu">',
              '<li><a href="#folders/<%= id %>/import/history"> from History</a></li>',
              '<% if(Galaxy.config.user_library_import_dir !== null) { %>',
                '<li><a href="#folders/<%= id %>/import/userdir"> from User Directory</a></li>',
              '<% } %>',
              '<% if(Galaxy.config.allow_library_path_paste) { %>',
                '<li class="divider"></li>',
                '<li class="dropdown-header">Admins only</li>',
                '<% if(Galaxy.config.library_import_dir !== null) { %>',
                  '<li><a href="#folders/<%= id %>/import/importdir">from Import Directory</a></li>',
                '<% } %>',
                '<% if(Galaxy.config.allow_library_path_paste) { %>',
                  '<li><a href="#folders/<%= id %>/import/path">from Path</a></li>',
                '<% } %>',
              '<% } %>',
            '</ul>',
          '</div>',
          '<% } else { %>',
            '<a  data-placement="top" title="Add Datasets to Current Folder" style="display:none;" class="btn btn-default add-library-items" href="#folders/<%= id %>/import/history" role="button">',
              '<span class="fa fa-plus"></span><span class="fa fa-file"></span>',
            '</a>',
          '<% } %>',
          '<button data-toggle="tooltip" data-placement="top" title="Import selected datasets into history" id="toolbtn_bulk_import" class="primary-button dataset-manipulation" style="margin-left: 0.5em; display:none;" type="button">',
            '<span class="fa fa-book"></span>',
            '&nbsp;to History',
          '</button>',
          '<div class="btn-group dataset-manipulation" style="margin-left: 0.5em; display:none; ">',
            '<button title="Download selected items as archive" type="button" class="primary-button dropdown-toggle" data-toggle="dropdown">',
              '<span class="fa fa-download"></span> Download <span class="caret"></span>',
            '</button>',
            '<ul class="dropdown-menu" role="menu">',
              '<li><a href="#/folders/<%= id %>/download/tgz">.tar.gz</a></li>',
              '<li><a href="#/folders/<%= id %>/download/tbz">.tar.bz</a></li>',
              '<li><a href="#/folders/<%= id %>/download/zip">.zip</a></li>',
            '</ul>',
          '</div>',
            '<button data-toggle="tooltip" data-placement="top" title="Mark selected items deleted" id="toolbtn_bulk_delete" class="primary-button logged-dataset-manipulation" style="margin-left: 0.5em; display:none; " type="button">',
            '<span class="fa fa-times"></span> Delete</button>',
            '<button data-id="<%- id %>" data-toggle="tooltip" data-placement="top" title="Show location details" class="primary-button toolbtn-show-locinfo" style="margin-left: 0.5em;" type="button">',
              '<span class="fa fa-info-circle"></span>',
              '&nbsp;Details',
            '</button>',
            '<span class="help-button" data-toggle="tooltip" data-placement="top" title="Visit Libraries Wiki">',
              '<a href="https://wiki.galaxyproject.org/DataLibraries/screen/FolderContents" target="_blank">',
                '<button class="primary-button" type="button">',
                  '<span class="fa fa-question-circle"></span>',
                  '&nbsp;Help',
                '</button>',
              '</a>',
            '</span>',
          '</div>',
        '</form>',
      // toolbar end
      '<div id="folder_items_element">',
      '</div>',
      // paginator will append here
      '<div class="folder-paginator paginator-bottom"></div>',
    // container end
    '</div>',
    ].join(''));
  },

  templateLocInfoInModal: function(){
    return _.template([
      '<div>',
        '<table class="grid table table-condensed">',
          '<thead>',
            '<th style="width: 25%;">library</th>',
            '<th></th>',
          '</thead>',
          '<tbody>',
            '<tr>',
              '<td>name</td>',
              '<td><%- library.get("name") %></td>',
            '</tr>',
            '<% if(library.get("description") !== "") { %>',
              '<tr>',
                '<td>description</td>',
                '<td><%- library.get("description") %></td>',
              '</tr>',
            '<% } %>',
            '<% if(library.get("synopsis") !== "") { %>',
              '<tr>',
                '<td>synopsis</td>',
                '<td><%- library.get("synopsis") %></td>',
              '</tr>',
            '<% } %>',
            '<% if(library.get("create_time_pretty") !== "") { %>',
              '<tr>',
                '<td>created</td>',
                '<td><span title="<%- library.get("create_time") %>"><%- library.get("create_time_pretty") %></span></td>',
              '</tr>',
            '<% } %>',
            '<tr>',
              '<td>id</td>',
              '<td><%- library.get("id") %></td>',
            '</tr>',
          '</tbody>',
        '</table>',
        '<table class="grid table table-condensed">',
          '<thead>',
            '<th style="width: 25%;">folder</th>',
            '<th></th>',
          '</thead>',
          '<tbody>',
            '<tr>',
              '<td>name</td>',
              '<td><%- options.folder_name %></td>',
            '</tr>',
            '<% if(options.folder_description !== "") { %>',
              '<tr>',
                '<td>description</td>',
                '<td><%- options.folder_description %></td>',
              '</tr>',
            '<% } %>',
            '<tr>',
              '<td>id</td>',
              '<td><%- options.id %></td>',
            '</tr>',
            '</tbody>',
        '</table>',
    '</div>'
    ].join(''));
  },

  templateNewFolderInModal: function(){
    return _.template([
    '<div id="new_folder_modal">',
      '<form>',
        '<input type="text" name="Name" value="" placeholder="Name" autofocus>',
        '<input type="text" name="Description" value="" placeholder="Description">',
      '</form>',
    '</div>'
    ].join(''));
  },


  templateBulkImportInModal : function(){
    return _.template([
    '<div>',
      '<div class="library-modal-item">',
        'Select history: ',
        '<select id="dataset_import_bulk" name="dataset_import_bulk" style="width:50%; margin-bottom: 1em; " autofocus>',
          '<% _.each(histories, function(history) { %>',
            '<option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>',
          '<% }); %>',
        '</select>',
      '</div>',
      '<div class="library-modal-item">',
        'or create new: ',
        '<input type="text" name="history_name" value="" placeholder="name of the new history" style="width:50%;">',
        '</input>',
      '</div>',
    '</div>'
    ].join(''));
  },

  templateImportIntoHistoryProgressBar : function (){
    return _.template([
    '<div class="import_text">',
      'Importing selected items to history <b><%= _.escape(history_name) %></b>',
    '</div>',
    '<div class="progress">',
      '<div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 00%;">',
        '<span class="completion_span">0% Complete</span>',
      '</div>',
    '</div>'
    ].join(''));
  },

  templateAddingDatasetsProgressBar: function (){
    return _.template([
    '<div class="import_text">',
      'Adding selected datasets to library folder <b><%= _.escape(folder_name) %></b>',
    '</div>',
    '<div class="progress">',
      '<div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 00%;">',
        '<span class="completion_span">0% Complete</span>',
      '</div>',
    '</div>'
    ].join(''));
  },

  templateDeletingItemsProgressBar: function (){
    return _.template([
    '<div class="import_text">',
    '</div>',
    '<div class="progress">',
      '<div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 00%;">',
        '<span class="completion_span">0% Complete</span>',
      '</div>',
    '</div>'
    ].join(''));
  },

  templateBrowserModal: function(){
    return _.template([
    '<div id="file_browser_modal">',
      '<div class="alert alert-info jstree-files-message">All files you select will be imported into the current folder ignoring their folder structure.</div>',
      '<div class="alert alert-info jstree-folders-message" style="display:none;">All files within the selected folders and their subfolders will be imported into the current folder.</div>',
      '<div style="margin-bottom:1em;">',
        '<label title="Switch to selecting files" class="radio-inline import-type-switch">',
          '<input type="radio" name="jstree-radio" value="jstree-disable-folders" checked="checked"> Choose Files',
        '</label>',
        '<label title="Switch to selecting folders" class="radio-inline import-type-switch">',
        '<input type="radio" name="jstree-radio" value="jstree-disable-files"> Choose Folders',
        '</label>',
      '</div>',
      '<div style="margin-bottom:1em;">',
        '<label class="checkbox-inline jstree-preserve-structure" style="display:none;">',
          '<input class="preserve-checkbox" type="checkbox" value="preserve_directory_structure">',
          'Preserve directory structure',
        '</label>',
        '<label class="checkbox-inline jstree-link-files" style="display:none;">',
          '<input class="link-checkbox" type="checkbox" value="link_files">',
          'Link files instead of copying',
        '</label>',
      '</div>',
      '<button title="Select all files" type="button" class="button primary-button libimport-select-all">',
        'Select all',
      '</button>',
      '<button title="Select no files" type="button" class="button primary-button libimport-select-none">',
        'Select none',
      '</button>',
      '<hr />',
      // append jstree object here
      '<div id="jstree_browser">',
      '</div>',
      '<hr />',
      '<p>You can set extension type and genome for all imported datasets at once:</p>',
      '<div>',
        'Type: <span id="library_extension_select" class="library-extension-select" />',
        'Genome: <span id="library_genome_select" class="library-genome-select" />',
        '</div>',
    '</div>'
    ].join(''));
  },

  templateImportPathModal: function(){
    return _.template([
    '<div id="file_browser_modal">',
      '<div class="alert alert-info jstree-folders-message">All files within the given folders and their subfolders will be imported into the current folder.</div>',
      '<div style="margin-bottom: 0.5em;">',
        '<label class="checkbox-inline jstree-preserve-structure">',
          '<input class="preserve-checkbox" type="checkbox" value="preserve_directory_structure">',
          'Preserve directory structure',
        '</label>',
        '<label class="checkbox-inline jstree-link-files">',
          '<input class="link-checkbox" type="checkbox" value="link_files">',
          'Link files instead of copying',
        '</label>',
      '</div>',
      '<textarea id="import_paths" class="form-control" rows="5" placeholder="Absolute paths (or paths relative to Galaxy root) separated by newline" autofocus></textarea>',
      '<hr />',
      '<p>You can set extension type and genome for all imported datasets at once:</p>',
      '<div>',
        'Type: <span id="library_extension_select" class="library-extension-select" />',
        'Genome: <span id="library_genome_select" class="library-genome-select" />',
      '</div>',
    '</div>'
    ].join(''));
  },

  templateAddFilesFromHistory: function (){
    return _.template([
    '<div id="add_files_modal">',
      '<div>',
        'Select history:  ',
        '<select id="dataset_add_bulk" name="dataset_add_bulk" style="width:66%; "> ',
          '<% _.each(histories, function(history) { %>', //history select box
            '<option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>',
          '<% }); %>',
        '</select>',
      '</div>',
      '<br/>',
      '<div id="selected_history_content">',
      '</div>',
    '</div>'
    ].join(''));
  },

  templateHistoryContents: function (){
    return _.template([
    '<strong>Choose the datasets to import:</strong>',
    '<ul>',
      '<% _.each(history_contents, function(history_item) { %>',
        '<li data-id="<%= _.escape(history_item.get("id")) %>">',
          '<input style="margin: 0;" type="checkbox"> <%= _.escape(history_item.get("hid")) %>: <%= _.escape(history_item.get("name")) %>',
        '</li>',
      '<% }); %>',
    '</ul>'
    ].join(''));
  },

  templatePaginator: function(){
    return _.template([
    '<ul class="pagination pagination-sm">',
      '<% if ( ( show_page - 1 ) > 0 ) { %>',
        '<% if ( ( show_page - 1 ) > page_count ) { %>', // we are on higher page than total page count
          '<li><a href="#folders/<%= id %>/page/1"><span class="fa fa-angle-double-left"></span></a></li>',
          '<li class="disabled"><a href="#folders/<%= id %>/page/<% print( show_page ) %>"><% print( show_page - 1 ) %></a></li>',
        '<% } else { %>',
          '<li><a href="#folders/<%= id %>/page/1"><span class="fa fa-angle-double-left"></span></a></li>',
          '<li><a href="#folders/<%= id %>/page/<% print( show_page - 1 ) %>"><% print( show_page - 1 ) %></a></li>',
        '<% } %>',
      '<% } else { %>', // we are on the first page
        '<li class="disabled"><a href="#folders/<%= id %>/page/1"><span class="fa fa-angle-double-left"></span></a></li>',
        '<li class="disabled"><a href="#folders/<%= id %>/page/<% print( show_page ) %>"><% print( show_page - 1 ) %></a></li>',
      '<% } %>',
      '<li class="active">',
        '<a href="#folders/<%= id %>/page/<% print( show_page ) %>"><% print( show_page ) %></a>',
      '</li>',
      '<% if ( ( show_page ) < page_count ) { %>',
        '<li><a href="#folders/<%= id %>/page/<% print( show_page + 1 ) %>"><% print( show_page + 1 ) %></a></li>',
        '<li><a href="#folders/<%= id %>/page/<% print( page_count ) %>"><span class="fa fa-angle-double-right"></span></a></li>',
      '<% } else { %>',
        '<li class="disabled"><a href="#folders/<%= id %>/page/<% print( show_page  ) %>"><% print( show_page + 1 ) %></a></li>',
        '<li class="disabled"><a href="#folders/<%= id %>/page/<% print( page_count ) %>"><span class="fa fa-angle-double-right"></span></a></li>',
      '<% } %>',
    '</ul>',
    '<span>',
      '&nbsp;showing&nbsp;',
      '<a data-toggle="tooltip" data-placement="top" title="Click to change the number of items on page" class="page_size_prompt">',
        '<%- items_shown %>',
      '</a>',
      '&nbsp;of <%- total_items_count %> items',
    '</span>'
    ].join(''));
  },

});

return {
    FolderToolbarView: FolderToolbarView
};

});
