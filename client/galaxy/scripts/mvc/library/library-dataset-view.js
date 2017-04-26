define([
  "libs/toastr",
  "mvc/library/library-model",
  "utils/utils",
  'mvc/ui/ui-select'
  ],
function(
        mod_toastr,
        mod_library_model,
        mod_utils,
        mod_select
        ) {

var LibraryDatasetView = Backbone.View.extend({
  el: '#center',

  model: null,

  options: {

  },

  events: {
    "click .toolbtn_modify_dataset"       :   "enableModification",
    "click .toolbtn_cancel_modifications" :   "render",
    "click .toolbtn-download-dataset"     :   "downloadDataset",
    "click .toolbtn-import-dataset"       :   "importIntoHistory",
    "click .toolbtn-share-dataset"        :   "shareDataset",
    "click .btn-copy-link-to-clipboard"   :   "copyToClipboard",
    "click .btn-make-private"             :   "makeDatasetPrivate",
    "click .btn-remove-restrictions"      :   "removeDatasetRestrictions",
    "click .toolbtn_save_permissions"     :   "savePermissions",
    "click .toolbtn_save_modifications"   :   "comingSoon",

  },

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
    this.options = _.extend(this.options, options);
    this.fetchExtAndGenomes();
    if (this.options.id){
      this.fetchDataset();
    }
  },

  fetchDataset: function(options){
    this.options = _.extend(this.options, options);
    this.model = new mod_library_model.Item({id: this.options.id});
    var that = this;
    this.model.fetch({
      success: function() {
        if (that.options.show_permissions){
            that.showPermissions();
        } else if (that.options.show_version) {
            that.fetchVersion();
        } else {
            that.render();
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

  render: function(options){
    this.options = _.extend(this.options, options);
    $(".tooltip").remove();
    var template = this.templateDataset();
    this.$el.html(template({item: this.model}));
    $(".peek").html(this.model.get("peek"));
    $("#center [data-toggle]").tooltip();
  },

  fetchVersion: function(options){
    this.options = _.extend(this.options, options);
    that = this;
    if (!this.options.ldda_id){
      this.render();
      mod_toastr.error('Library dataset version requested but no id provided.');
    } else {
      this.ldda = new mod_library_model.Ldda({id: this.options.ldda_id});
      this.ldda.url = this.ldda.urlRoot + this.model.id + '/versions/' + this.ldda.id;
      this.ldda.fetch({
        success: function(){
          that.renderVersion();
        },
        error: function(model, response){
          if (typeof response.responseJSON !== "undefined"){
            mod_toastr.error(response.responseJSON.err_msg);
          } else {
            mod_toastr.error('An error ocurred.');
          }
        }
      });
    }
  },

  renderVersion: function(){
    $(".tooltip").remove();
    var template = this.templateVersion();
    this.$el.html(template({item: this.model, ldda: this.ldda}));
    $(".peek").html(this.ldda.get("peek"));
  },

  enableModification: function(){
    $(".tooltip").remove();
    var template = this.templateModifyDataset();
    this.$el.html(template({item: this.model}));
    this.renderSelectBoxes({genome_build: this.model.get('genome_build'), file_ext: this.model.get('file_ext') });
    $(".peek").html(this.model.get("peek"));
    $("#center [data-toggle]").tooltip();
  },

  downloadDataset: function(){
    var url = Galaxy.root + 'api/libraries/datasets/download/uncompressed';
    var data = {'ld_ids': this.id};
    this.processDownload(url, data);
  },

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

          mod_toastr.info('Your download will begin soon.');
        }
   },

  importIntoHistory: function(){
    this.refreshUserHistoriesList(function(self){
            var template = self.templateBulkImportInModal();
            self.modal = Galaxy.modal;
            self.modal.show({
                closing_events  : true,
                title           : 'Import into History',
                body            : template({histories : self.histories.models}),
                buttons         : {
                    'Import'    : function() {self.importCurrentIntoHistory();},
                    'Close'     : function() {Galaxy.modal.hide();}
                }
            });
          });
  },

 refreshUserHistoriesList: function(callback){
    var self = this;
    this.histories = new mod_library_model.GalaxyHistories();
    this.histories.fetch({
      success: function (histories){
        if (histories.length === 0){
          mod_toastr.warning('You have to create history first. Click this to do so.', '', {onclick: function() {window.location=Galaxy.root;}});
        } else {
          callback(self);
        }
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

  importCurrentIntoHistory: function(){
    this.modal.disableButton('Import');
    var new_history_name = this.modal.$('input[name=history_name]').val();
    var that = this;
    if (new_history_name !== ''){
      $.post( Galaxy.root + 'api/histories', {name: new_history_name})
        .done(function( new_history ) {
          that.processImportToHistory(new_history.id);
        })
        .fail(function( xhr, status, error ) {
          mod_toastr.error('An error ocurred.');
        })
        .always(function() {
          that.modal.enableButton('Import');
        });
    } else {
      var history_id = $(this.modal.$el).find('select[name=dataset_import_single] option:selected').val();
      this.processImportToHistory(history_id);
      this.modal.enableButton('Import');
    }
  },

  processImportToHistory: function( history_id ){
    var historyItem = new mod_library_model.HistoryItem();
    historyItem.url = historyItem.urlRoot + history_id + '/contents';
    // set the used history as current so user will see the last one
    // that he imported into in the history panel on the 'analysis' page
    jQuery.getJSON( Galaxy.root + 'history/set_as_current?id=' + history_id  );
    // save the dataset into selected history
    historyItem.save({ content : this.id, source : 'library' }, {
      success : function(){
        Galaxy.modal.hide();
        mod_toastr.success('Dataset imported. Click this to start analyzing it.', '', {onclick: function() {window.location=Galaxy.root;}});
      },
      error : function(model, response){
        if (typeof response.responseJSON !== "undefined"){
          mod_toastr.error('Dataset not imported. ' + response.responseJSON.err_msg);
        } else {
          mod_toastr.error('An error occured. Dataset not imported. Please try again.');
        }
      }
      });
  },

  shareDataset: function(){
    mod_toastr.info('Feature coming soon.');
  },

  goBack: function(){
    Galaxy.libraries.library_router.back();
  },

  showPermissions: function(options){
    this.options = _.extend(this.options, options);
    $(".tooltip").remove();
    if (this.options.fetched_permissions !== undefined){
      if (this.options.fetched_permissions.access_dataset_roles.length === 0){
        this.model.set({is_unrestricted:true});
      } else{
        this.model.set({is_unrestricted:false});
      }
    }
    // Select works different for admins, details in this.prepareSelectBoxes
    var is_admin = false;
    if (Galaxy.user){
      is_admin = Galaxy.user.isAdmin();
    }
    var template = this.templateDatasetPermissions();
    this.$el.html(template({item: this.model, is_admin: is_admin}));
    var self = this;
    $.get( Galaxy.root + "api/libraries/datasets/" + self.id + "/permissions?scope=current").done(function(fetched_permissions) {
      self.prepareSelectBoxes({fetched_permissions: fetched_permissions, is_admin: is_admin});
    }).fail(function(){
        mod_toastr.error('An error occurred while attempting to fetch dataset permissions.');
    });
    $("#center [data-toggle]").tooltip();
    $("#center").css('overflow','auto');
  },

  _serializeRoles : function(role_list){
    var selected_roles = [];
    for (var i = 0; i < role_list.length; i++) {
      selected_roles.push(role_list[i][1] + ':' + role_list[i][0]);
    }
    return selected_roles;
  },

  prepareSelectBoxes: function(options){
    this.options = _.extend(this.options, options);
    var fetched_permissions = this.options.fetched_permissions;
    var is_admin = this.options.is_admin
    var self = this;
    var selected_access_dataset_roles = [];
    var selected_modify_item_roles = [];
    var selected_manage_dataset_roles = [];
    selected_access_dataset_roles = this._serializeRoles(fetched_permissions.access_dataset_roles);
    selected_modify_item_roles = this._serializeRoles(fetched_permissions.modify_item_roles);
    selected_manage_dataset_roles = this._serializeRoles(fetched_permissions.manage_dataset_roles);

    if (is_admin){ // Admin has a special select that allows AJAX searching
        var access_select_options = {
          minimumInputLength: 0,
          css: 'access_perm',
          multiple:true,
          placeholder: 'Click to select a role',
          container: self.$el.find('#access_perm'),
          ajax: {
              url: Galaxy.root + "api/libraries/datasets/" + self.id + "/permissions?scope=available",
              dataType: 'json',
              quietMillis: 100,
              data: function (term, page) { // page is the one-based page number tracked by Select2
                  return {
                      q: term, //search term
                      page_limit: 10, // page size
                      page: page // page number
                  };
              },
              results: function (data, page) {
                  var more = (page * 10) < data.total; // whether or not there are more results available
                  // notice we return the value of more so Select2 knows if more results can be loaded
                  return {results: data.roles, more: more};
              }
          },
          formatResult : function roleFormatResult(role) {
              return role.name + ' type: ' + role.type;
          },

          formatSelection: function roleFormatSelection(role) {
              return role.name;
          },
          initSelection: function(element, callback) {
          // the input tag has a value attribute preloaded that points to a preselected role's id
          // this function resolves that id attribute to an object that select2 can render
          // using its formatResult renderer - that way the role name is shown preselected
              var data = [];
              $(element.val().split(",")).each(function() {
                  var item = this.split(':');
                  data.push({
                      id: item[0],
                      name: item[1]
                  });
              });
              callback(data);
          },
          initialData: selected_access_dataset_roles.join(','),
          dropdownCssClass: "bigdrop" // apply css that makes the dropdown taller
        };
        var modify_select_options = {
          minimumInputLength: 0,
          css: 'modify_perm',
          multiple:true,
          placeholder: 'Click to select a role',
          container: self.$el.find('#modify_perm'),
          ajax: {
              url: Galaxy.root + "api/libraries/datasets/" + self.id + "/permissions?scope=available",
              dataType: 'json',
              quietMillis: 100,
              data: function (term, page) { // page is the one-based page number tracked by Select2
                  return {
                      q: term, //search term
                      page_limit: 10, // page size
                      page: page // page number
                  };
              },
              results: function (data, page) {
                  var more = (page * 10) < data.total; // whether or not there are more results available
                  // notice we return the value of more so Select2 knows if more results can be loaded
                  return {results: data.roles, more: more};
              }
          },
          formatResult : function roleFormatResult(role) {
              return role.name + ' type: ' + role.type;
          },

          formatSelection: function roleFormatSelection(role) {
              return role.name;
          },
          initSelection: function(element, callback) {
          // the input tag has a value attribute preloaded that points to a preselected role's id
          // this function resolves that id attribute to an object that select2 can render
          // using its formatResult renderer - that way the role name is shown preselected
              var data = [];
              $(element.val().split(",")).each(function() {
                  var item = this.split(':');
                  data.push({
                      id: item[0],
                      name: item[1]
                  });
              });
              callback(data);
          },
          initialData: selected_modify_item_roles.join(','),
          dropdownCssClass: "bigdrop" // apply css that makes the dropdown taller
        };
        var manage_select_options = {
          minimumInputLength: 0,
          css: 'manage_perm',
          multiple:true,
          placeholder: 'Click to select a role',
          container: self.$el.find('#manage_perm'),
          ajax: {
              url: Galaxy.root + "api/libraries/datasets/" + self.id + "/permissions?scope=available",
              dataType: 'json',
              quietMillis: 100,
              data: function (term, page) { // page is the one-based page number tracked by Select2
                  return {
                      q: term, //search term
                      page_limit: 10, // page size
                      page: page // page number
                  };
              },
              results: function (data, page) {
                  var more = (page * 10) < data.total; // whether or not there are more results available
                  // notice we return the value of more so Select2 knows if more results can be loaded
                  return {results: data.roles, more: more};
              }
          },
          formatResult : function roleFormatResult(role) {
              return role.name + ' type: ' + role.type;
          },

          formatSelection: function roleFormatSelection(role) {
              return role.name;
          },
          initSelection: function(element, callback) {
          // the input tag has a value attribute preloaded that points to a preselected role's id
          // this function resolves that id attribute to an object that select2 can render
          // using its formatResult renderer - that way the role name is shown preselected
              var data = [];
              $(element.val().split(",")).each(function() {
                  var item = this.split(':');
                  data.push({
                      id: item[0],
                      name: item[1]
                  });
              });
              callback(data);
          },
          initialData: selected_manage_dataset_roles.join(','),
          dropdownCssClass: "bigdrop" // apply css that makes the dropdown taller
        };

        self.accessSelectObject = new mod_select.View(access_select_options);
        self.modifySelectObject = new mod_select.View(modify_select_options);
        self.manageSelectObject = new mod_select.View(manage_select_options);
    } else { // Non-admins have select with pre-loaded options
        var template = self.templateAccessSelect();
        $.get( Galaxy.root + "api/libraries/datasets/" + self.id + "/permissions?scope=available", function( data ) {
            $('.access_perm').html(template({options: data.roles}));
            self.accessSelectObject = $('#access_select').select2();
        }).fail(function() {
            mod_toastr.error('An error occurred while attempting to fetch dataset permissions.');
        });
    }
  },

  comingSoon: function(){
    mod_toastr.warning('Feature coming soon.');
  },

  copyToClipboard: function(){
    var href = Backbone.history.location.href;
    if (href.lastIndexOf('/permissions') !== -1){
      href = href.substr(0, href.lastIndexOf('/permissions'));
    }
    window.prompt("Copy to clipboard: Ctrl+C, Enter", href);
  },

  makeDatasetPrivate: function(){
    var self = this;
    $.post( Galaxy.root + "api/libraries/datasets/" + self.id + "/permissions?action=make_private").done(function(fetched_permissions) {
      self.model.set({is_unrestricted: false});
      self.showPermissions({fetched_permissions: fetched_permissions})
      mod_toastr.success('The dataset is now private to you.');
    }).fail(function(){
      mod_toastr.error('An error occurred while attempting to make dataset private.');
    });
  },

  removeDatasetRestrictions: function(){
    var self = this;
    $.post( Galaxy.root + "api/libraries/datasets/" + self.id + "/permissions?action=remove_restrictions")
    .done(function(fetched_permissions) {
      self.model.set({is_unrestricted: true});
      self.showPermissions({fetched_permissions: fetched_permissions})
      mod_toastr.success('Access to this dataset is now unrestricted.');
    })
    .fail(function(){
      mod_toastr.error('An error occurred while attempting to make dataset unrestricted.');
    });
  },

  /**
   * Extract the role ids from Select2 elements's 'data'
   */
  _extractIds: function(roles_list){
    ids_list = [];
    for (var i = roles_list.length - 1; i >= 0; i--) {
      ids_list.push(roles_list[i].id);
    };
    return ids_list;
  },

  /**
   * Save the permissions for roles entered in the select boxes.
   */
  savePermissions: function(event){
    var self = this;
    var access_ids = this._extractIds(this.accessSelectObject.$el.select2('data'));
    var manage_ids = this._extractIds(this.manageSelectObject.$el.select2('data'));
    var modify_ids = this._extractIds(this.modifySelectObject.$el.select2('data'));
    $.post( Galaxy.root + "api/libraries/datasets/" + self.id + "/permissions?action=set_permissions", { 'access_ids[]': access_ids, 'manage_ids[]': manage_ids, 'modify_ids[]': modify_ids, } )
    .done(function(fetched_permissions){
      self.showPermissions({fetched_permissions: fetched_permissions})
      mod_toastr.success('Permissions saved.');
    })
    .fail(function(){
      mod_toastr.error('An error occurred while attempting to set dataset permissions.');
    })
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
                    }
      });
    mod_utils.get({
        url     :    Galaxy.root + "api/genomes",
        success : function( genomes ) {
                    for ( key in genomes ) {
                        that.list_genomes.push({
                            id      : genomes[key][1],
                            text    : genomes[key][0]
                        });
                    }
                    that.list_genomes.sort(function(a, b) {
                        return a.id > b.id ? 1 : a.id < b.id ? -1 : 0;
                    });
                }
    });
  },

  renderSelectBoxes: function(options){
    // This won't work properly unlesss we already have the data fetched.
    // See this.fetchExtAndGenomes()
    // TODO switch to common resources:
    // https://trello.com/c/dIUE9YPl/1933-ui-common-resources-and-data-into-galaxy-object
    var current_genome = '?';
    var current_ext = 'auto';
    if (typeof options !== 'undefined'){
      if (typeof options.genome_build !== 'undefined'){
        current_genome = options.genome_build;
      }
      if (typeof options.file_ext !== 'undefined'){
        current_ext = options.file_ext;
      }
    }
    var that = this;
    this.select_genome = new mod_select.View( {
        css: 'dataset-genome-select',
        data: that.list_genomes,
        container: that.$el.find( '#dataset_genome_select' ),
        value: current_genome
    } );
    this.select_extension = new mod_select.View({
      css: 'dataset-extension-select',
      data: that.list_extensions,
      container: that.$el.find( '#dataset_extension_select' ),
      value: current_ext
    });
  },

  templateDataset : function(){
    return _.template([
    // CONTAINER START
    '<div class="library_style_container">',
      '<div id="library_toolbar">',
        '<button data-toggle="tooltip" data-placement="top" title="Download dataset" class="btn btn-default toolbtn-download-dataset primary-button toolbar-item" type="button">',
          '<span class="fa fa-download"></span>',
          '&nbsp;Download',
        '</button>',
        '<button data-toggle="tooltip" data-placement="top" title="Import dataset into history" class="btn btn-default toolbtn-import-dataset primary-button toolbar-item" type="button">',
          '<span class="fa fa-book"></span>',
          '&nbsp;to History',
        '</button>',
        '<% if (item.get("can_user_modify")) { %>',
          '<button data-toggle="tooltip" data-placement="top" title="Modify library item" class="btn btn-default toolbtn_modify_dataset primary-button toolbar-item" type="button">',
            '<span class="fa fa-pencil"></span>',
            '&nbsp;Modify',
          '</button>',
        '<% } %>',
        '<% if (item.get("can_user_manage")) { %>',
          '<a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>/permissions">',
            '<button data-toggle="tooltip" data-placement="top" title="Manage permissions" class="btn btn-default toolbtn_change_permissions primary-button toolbar-item" type="button">',
              '<span class="fa fa-group"></span>',
              '&nbsp;Permissions',
            '</button>',
          '</a>',
        '<% } %>',
      '</div>',

    // BREADCRUMBS
    '<ol class="breadcrumb">',
      '<li><a title="Return to the list of libraries" href="#">Libraries</a></li>',
      '<% _.each(item.get("full_path"), function(path_item) { %>',
        '<% if (path_item[0] != item.id) { %>',
          '<li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',
        '<% } else { %>',
          '<li class="active"><span title="You are here"><%- path_item[1] %></span></li>',
        '<% } %>',
      '<% }); %>',
    '</ol>',

    '<% if (item.get("is_unrestricted")) { %>',
      '<div class="alert alert-info">',
        'This dataset is unrestricted so everybody can access it. Just share the URL of this page. ',
        '<button data-toggle="tooltip" data-placement="top" title="Copy to clipboard" class="btn btn-default btn-copy-link-to-clipboard primary-button" type="button">',
          '<span class="fa fa-clipboard"></span>',
          '&nbsp;To Clipboard',
        '</button> ',
      '</div>',
    '<% } %>',

    // TABLE START
    '<div class="dataset_table">',
      '<table class="grid table table-striped table-condensed">',
        '<tr>',
          '<th class="dataset-first-column" scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>',
          '<td><%= _.escape(item.get("name")) %></td>',
        '</tr>',
        '<% if (item.get("file_ext")) { %>',
          '<tr>',
            '<th scope="row">Data type</th>',
            '<td><%= _.escape(item.get("file_ext")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("genome_build")) { %>',
          '<tr>',
            '<th scope="row">Genome build</th>',
            '<td><%= _.escape(item.get("genome_build")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("file_size")) { %>',
          '<tr>',
            '<th scope="row">Size</th>',
            '<td><%= _.escape(item.get("file_size")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("date_uploaded")) { %>',
          '<tr>',
            '<th scope="row">Date uploaded (UTC)</th>',
            '<td><%= _.escape(item.get("date_uploaded")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("uploaded_by")) { %>',
          '<tr>',
            '<th scope="row">Uploaded by</th>',
            '<td><%= _.escape(item.get("uploaded_by")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("metadata_data_lines")) { %>',
          '<tr>',
            '<th scope="row">Data Lines</th>',
            '<td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("metadata_comment_lines")) { %>',
          '<tr>',
            '<th scope="row">Comment Lines</th>',
            '<td scope="row"><%= _.escape(item.get("metadata_comment_lines")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("metadata_columns")) { %>',
          '<tr>',
            '<th scope="row">Number of Columns</th>',
            '<td scope="row"><%= _.escape(item.get("metadata_columns")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("metadata_column_types")) { %>',
          '<tr>',
            '<th scope="row">Column Types</th>',
            '<td scope="row"><%= _.escape(item.get("metadata_column_types")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("message")) { %>',
          '<tr>',
            '<th scope="row">Message</th>',
            '<td scope="row"><%= _.escape(item.get("message")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("misc_blurb")) { %>',
          '<tr>',
            '<th scope="row">Miscellaneous blurb</th>',
            '<td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>',
          '</tr>',
        '<% } %>',
        '<% if (item.get("misc_info")) { %>',
          '<tr>',
            '<th scope="row">Miscellaneous information</th>',
            '<td scope="row"><%= _.escape(item.get("misc_info")) %></td>',
          '</tr>',
        '<% } %>',
      '</table>',

    '<div>',
      '<pre class="peek">',
      '</pre>',
    '</div>',

    '<% if (item.get("has_versions")) { %>',
      '<div>',
        '<h3>Expired versions:</h3>',
        '<ul>',
          '<% _.each(item.get("expired_versions"), function(version) { %>',
            '<li><a title="See details of this version" href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>/versions/<%- version[0] %>"><%- version[1] %></a></li>',
          '<% }) %>',
        '<ul>',
      '</div>',
    '<% } %>',
    // TABLE END
    '</div>',
    // CONTAINER END
    '</div>'
    ].join(''));
  },

  templateVersion : function(){
    return _.template([
    // CONTAINER START
    '<div class="library_style_container">',
      '<div id="library_toolbar">',
        '<a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>">',
          '<button data-toggle="tooltip" data-placement="top" title="Go to latest dataset" class="btn btn-default primary-button toolbar-item" type="button">',
            '<span class="fa fa-caret-left fa-lg"></span>',
            '&nbsp;Latest dataset',
          '</button>',
        '<a>',
      '</div>',

      // BREADCRUMBS
      '<ol class="breadcrumb">',
        '<li><a title="Return to the list of libraries" href="#">Libraries</a></li>',
        '<% _.each(item.get("full_path"), function(path_item) { %>',
          '<% if (path_item[0] != item.id) { %>',
            '<li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',
          '<% } else { %>',
            '<li class="active"><span title="You are here"><%- path_item[1] %></span></li>',
          '<% } %>',
        '<% }); %>',
      '</ol>',

      '<div class="alert alert-warning">This is an expired version of the library dataset: <%= _.escape(item.get("name")) %></div>',
      // DATASET START
      '<div class="dataset_table">',
        '<table class="grid table table-striped table-condensed">',
          '<tr>',
            '<th scope="row" id="id_row" data-id="<%= _.escape(ldda.id) %>">Name</th>',
            '<td><%= _.escape(ldda.get("name")) %></td>',
          '</tr>',
          '<% if (ldda.get("file_ext")) { %>',
            '<tr>',
              '<th scope="row">Data type</th>',
              '<td><%= _.escape(ldda.get("file_ext")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("genome_build")) { %>',
            '<tr>',
              '<th scope="row">Genome build</th>',
              '<td><%= _.escape(ldda.get("genome_build")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("file_size")) { %>',
            '<tr>',
              '<th scope="row">Size</th>',
              '<td><%= _.escape(ldda.get("file_size")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("date_uploaded")) { %>',
            '<tr>',
              '<th scope="row">Date uploaded (UTC)</th>',
              '<td><%= _.escape(ldda.get("date_uploaded")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("uploaded_by")) { %>',
            '<tr>',
              '<th scope="row">Uploaded by</th>',
              '<td><%= _.escape(ldda.get("uploaded_by")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("metadata_data_lines")) { %>',
            '<tr>',
              '<th scope="row">Data Lines</th>',
              '<td scope="row"><%= _.escape(ldda.get("metadata_data_lines")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("metadata_comment_lines")) { %>',
            '<tr>',
              '<th scope="row">Comment Lines</th>',
              '<td scope="row"><%= _.escape(ldda.get("metadata_comment_lines")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("metadata_columns")) { %>',
            '<tr>',
              '<th scope="row">Number of Columns</th>',
              '<td scope="row"><%= _.escape(ldda.get("metadata_columns")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("metadata_column_types")) { %>',
            '<tr>',
              '<th scope="row">Column Types</th>',
              '<td scope="row"><%= _.escape(ldda.get("metadata_column_types")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("message")) { %>',
            '<tr>',
              '<th scope="row">Message</th>',
              '<td scope="row"><%= _.escape(ldda.get("message")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("misc_blurb")) { %>',
            '<tr>',
              '<th scope="row">Miscellaneous blurb</th>',
              '<td scope="row"><%= _.escape(ldda.get("misc_blurb")) %></td>',
            '</tr>',
          '<% } %>',
          '<% if (ldda.get("misc_info")) { %>',
            '<tr>',
              '<th scope="row">Miscellaneous information</th>',
              '<td scope="row"><%= _.escape(ldda.get("misc_info")) %></td>',
            '</tr>',
          '<% } %>',
        '</table>',
        '<div>',
          '<pre class="peek">',
          '</pre>',
        '</div>',
      // DATASET END
      '</div>',
    // CONTAINER END
    '</div>'
    ].join(''));
  },

  templateModifyDataset : function(){
    return _.template([
    // CONTAINER START
    '<div class="library_style_container">',
      '<div id="library_toolbar">',
        '<button data-toggle="tooltip" data-placement="top" title="Cancel modifications" class="btn btn-default toolbtn_cancel_modifications primary-button toolbar-item" type="button">',
          '<span class="fa fa-times"></span>',
          '&nbsp;Cancel',
        '</button>',
        '<button data-toggle="tooltip" data-placement="top" title="Save modifications" class="btn btn-default toolbtn_save_modifications primary-button toolbar-item" type="button">',
          '<span class="fa fa-floppy-o"></span>',
          '&nbsp;Save',
        '</button>',
      '</div>',

      // BREADCRUMBS
      '<ol class="breadcrumb">',
        '<li><a title="Return to the list of libraries" href="#">Libraries</a></li>',
        '<% _.each(item.get("full_path"), function(path_item) { %>',
          '<% if (path_item[0] != item.id) { %>',
            '<li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',
          '<% } else { %>',
            '<li class="active"><span title="You are here"><%- path_item[1] %></span></li>',
          '<% } %>',
        '<% }); %>',
      '</ol>',

      '<div class="dataset_table">',
        '<p>For full editing options please import the dataset to history and use "Edit attributes" on it.</p>',
        '<table class="grid table table-striped table-condensed">',
          '<tr>',
            '<th class="dataset-first-column" scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>',
            '<td><input class="input_dataset_name form-control" type="text" placeholder="name" value="<%= _.escape(item.get("name")) %>"></td>',
          '</tr>',
          '<tr>',
            '<th scope="row">Data type</th>',
            '<td>',
              '<span id="dataset_extension_select" class="dataset-extension-select" />',
            '</td>',
          '</tr>',
          '<tr>',
            '<th scope="row">Genome build</th>',
            '<td>',
              '<span id="dataset_genome_select" class="dataset-genome-select" />',
            '</td>',
          '</tr>',
          '<tr>',
            '<th scope="row">Size</th>',
            '<td><%= _.escape(item.get("file_size")) %></td>',
          '</tr>',
          '<tr>',
            '<th scope="row">Date uploaded (UTC)</th>',
            '<td><%= _.escape(item.get("date_uploaded")) %></td>',
          '</tr>',
          '<tr>',
            '<th scope="row">Uploaded by</th>',
            '<td><%= _.escape(item.get("uploaded_by")) %></td>',
          '</tr>',
          '<tr scope="row">',
            '<th scope="row">Data Lines</th>',
            '<td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>',
          '</tr>',
            '<th scope="row">Comment Lines</th>',
            '<% if (item.get("metadata_comment_lines") === "") { %>',
              '<td scope="row"><%= _.escape(item.get("metadata_comment_lines")) %></td>',
            '<% } else { %>',
              '<td scope="row">unknown</td>',
            '<% } %>',
          '</tr>',
          '<tr>',
            '<th scope="row">Number of Columns</th>',
            '<td scope="row"><%= _.escape(item.get("metadata_columns")) %></td>',
          '</tr>',
          '<tr>',
            '<th scope="row">Column Types</th>',
            '<td scope="row"><%= _.escape(item.get("metadata_column_types")) %></td>',
          '</tr>',
          '<tr>',
            '<th scope="row">Message</th>',
            '<td scope="row"><%= _.escape(item.get("message")) %></td>',
          '</tr>',
          '<tr>',
            '<th scope="row">Miscellaneous information</th>',
            '<td scope="row"><%= _.escape(item.get("misc_info")) %></td>',
          '</tr>',
          '<tr>',
            '<th scope="row">Miscellaneous blurb</th>',
            '<td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>',
          '</tr>',
        '</table>',
        '<div>',
          '<pre class="peek">',
          '</pre>',
        '</div>',
      '</div>',
    // CONTAINER END
    '</div>'
    ].join(''));
  },

  templateDatasetPermissions : function(){
    return _.template([
    // CONTAINER START
    '<div class="library_style_container">',
      '<div id="library_toolbar">',
        '<a href="#folders/<%- item.get("folder_id") %>">',
          '<button data-toggle="tooltip" data-placement="top" title="Go back to containing folder" class="btn btn-default primary-button toolbar-item" type="button">',
            '<span class="fa fa-folder-open-o"></span>',
            '&nbsp;Containing Folder',
          '</button>',
        '</a>',
        '<a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>">',
          '<button data-toggle="tooltip" data-placement="top" title="Go back to dataset" class="btn btn-default primary-button toolbar-item" type="button">',
            '<span class="fa fa-file-o"></span>',
            '&nbsp;Dataset Details',
          '</button>',
        '<a>',
      '</div>',

      // BREADCRUMBS
      '<ol class="breadcrumb">',
        '<li><a title="Return to the list of libraries" href="#">Libraries</a></li>',
          '<% _.each(item.get("full_path"), function(path_item) { %>',
            '<% if (path_item[0] != item.id) { %>',
              '<li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ',
            '<% } else { %>',
              '<li class="active"><span title="You are here"><%- path_item[1] %></span></li>',
            '<% } %>',
        '<% }); %>',
      '</ol>',

      '<h1>Dataset: <%= _.escape(item.get("name")) %></h1>',
      '<div class="alert alert-warning">',
        '<% if (is_admin) { %>',
          'You are logged in as an <strong>administrator</strong> therefore you can manage any dataset on this Galaxy instance. Please make sure you understand the consequences.',
        '<% } else { %>',
          'You can assign any number of roles to any of the following permission types. However please read carefully the implications of such actions.',
        '<% } %>',
      '</div>',
      '<div class="dataset_table">',
        '<h2>Library-related permissions</h2>',
        '<h4>Roles that can modify the library item</h4>',
        '<div id="modify_perm" class="modify_perm roles-selection"></div>',
        '<div class="alert alert-info roles-selection">User with <strong>any</strong> of these roles can modify name, metadata, and other information about this library item.</div>',
        '<hr/>',
        '<h2>Dataset-related permissions</h2>',
        '<div class="alert alert-warning">Changes made below will affect <strong>every</strong> library item that was created from this dataset and also every history this dataset is part of.</div>',
        '<% if (!item.get("is_unrestricted")) { %>',
          '<p>You can remove all access restrictions on this dataset. ',
            '<button data-toggle="tooltip" data-placement="top" title="Everybody will be able to access the dataset." class="btn btn-default btn-remove-restrictions primary-button" type="button">',
              '<span class="fa fa-globe"></span>',
              '&nbsp;Remove restrictions',
            '</button>',
          '</p>',
        '<% } else { %>',
          'This dataset is unrestricted so everybody can access it. Just share the URL of this page.',
          '<button data-toggle="tooltip" data-placement="top" title="Copy to clipboard" class="btn btn-default btn-copy-link-to-clipboard primary-button" type="button">',
            '<span class="fa fa-clipboard"></span>',
            '&nbsp;To Clipboard',
            '</button>',
          '<p>You can make this dataset private to you. ',
            '<button data-toggle="tooltip" data-placement="top" title="Only you will be able to access the dataset." class="btn btn-default btn-make-private primary-button" type="button">',
              '<span class="fa fa-key"></span>',
              '&nbsp;Make Private',
            '</button>',
          '</p>',
        '<% } %>',
        '<h4>Roles that can access the dataset</h4>',
        '<div id="access_perm" class="access_perm roles-selection"></div>',
        '<div class="alert alert-info roles-selection">',
          'User has to have <strong>all these roles</strong> in order to access this dataset.',
          ' Users without access permission <strong>cannot</strong> have other permissions on this dataset.',
          ' If there are no access roles set on the dataset it is considered <strong>unrestricted</strong>.',
        '</div>',
        '<h4>Roles that can manage permissions on the dataset</h4>',
        '<div id="manage_perm" class="manage_perm roles-selection"></div>',
        '<div class="alert alert-info roles-selection">',
          'User with <strong>any</strong> of these roles can manage permissions of this dataset. If you remove yourself you will loose the ability manage this dataset unless you are an admin.',
        '</div>',
        '<button data-toggle="tooltip" data-placement="top" title="Save modifications made on this page" class="btn btn-default toolbtn_save_permissions primary-button" type="button">',
          '<span class="fa fa-floppy-o"></span>',
          '&nbsp;Save',
        '</button>',
      '</div>',
    // CONTAINER END
    '</div>'
    ].join(''));
  },

  templateBulkImportInModal: function(){
    return _.template([
    '<div>',
      '<div class="library-modal-item">',
        'Select history: ',
        '<select id="dataset_import_single" name="dataset_import_single" style="width:50%; margin-bottom: 1em; " autofocus>',
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


  templateAccessSelect: function(){
    return _.template([
    '<select id="access_select" multiple>',
      '<% _.each(options, function(option) { %>',
        '<option value="<%- option.name %>"><%- option.name %></option>',
      '<% }); %>',
    '</select>'
    ].join(''));
  }

});

return {
    LibraryDatasetView: LibraryDatasetView
};

});
