define([
  "libs/toastr",
  "mvc/library/library-model",
  'mvc/ui/ui-select'
  ],
function(
        mod_toastr,
        mod_library_model,
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

    // missing features below
    "click .toolbtn_save_modifications"   :   "comingSoon",
    // "click .btn-share-dataset"            :   "comingSoon"

  },

  initialize: function(options){
    this.options = _.extend(this.options, options);
    if (this.options.id){
      this.fetchDataset();
    }
  },

  fetchDataset: function(options){
    this.options = _.extend(this.options, options);

    this.model = new mod_library_model.Item({id:this.options.id});
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
      this.ldda = new mod_library_model.Ldda({id:this.options.ldda_id});
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
    $(".peek").html(this.model.get("peek"));
    $("#center [data-toggle]").tooltip();
  },

  downloadDataset: function(){
    var url = '/api/libraries/datasets/download/uncompressed';
    var data = {'ldda_ids' : this.id};
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
          mod_toastr.warning('You have to create history first. Click this to do so.', '', {onclick: function() {window.location='/';}});
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
      // var self = this;
      var history_id = $(this.modal.elMain).find('select[name=dataset_import_single] option:selected').val();
      var historyItem = new mod_library_model.HistoryItem();
      historyItem.url = historyItem.urlRoot + history_id + '/contents';

      // set the used history as current so user will see the last one 
      // that he imported into in the history panel on the 'analysis' page
      jQuery.getJSON( galaxy_config.root + 'history/set_as_current?id=' + history_id  );

      // save the dataset into selected history
      historyItem.save({ content : this.id, source : 'library' }, { 
        success : function(){
            Galaxy.modal.hide();
          mod_toastr.success('Dataset imported. Click this to start analysing it.', '', {onclick: function() {window.location='/';}});
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
    // Select works different for admins
    var is_admin = false;
    if (Galaxy.currUser){
      is_admin = Galaxy.currUser.isAdmin();
    }
    var template = this.templateDatasetPermissions();
    this.$el.html(template({item: this.model, is_admin: is_admin}));

    var self = this;
    if (this.options.fetched_permissions === undefined){
      $.get( "/api/libraries/datasets/" + self.id + "/permissions?scope=current").done(function(fetched_permissions) {
        self.prepareSelectBoxes({fetched_permissions:fetched_permissions, is_admin:is_admin});
      }).fail(function(){
          mod_toastr.error('An error occurred while attempting to fetch dataset permissions.');
      });
    } else {
      this.prepareSelectBoxes({is_admin:is_admin});
    }

    $("#center [data-toggle]").tooltip();
    //hack to show scrollbars
    $("#center").css('overflow','auto');
  },

  prepareSelectBoxes: function(options){
    this.options = _.extend(this.options, options);
    var fetched_permissions = this.options.fetched_permissions;
    var is_admin = this.options.is_admin
    var self = this;
    var selected_access_dataset_roles = [];
        for (var i = 0; i < fetched_permissions.access_dataset_roles.length; i++) {
            selected_access_dataset_roles.push(fetched_permissions.access_dataset_roles[i] + ':' + fetched_permissions.access_dataset_roles[i]);
        }
        var selected_modify_item_roles = [];
        for (var i = 0; i < fetched_permissions.modify_item_roles.length; i++) {
            selected_modify_item_roles.push(fetched_permissions.modify_item_roles[i] + ':' + fetched_permissions.modify_item_roles[i]);
        }
        var selected_manage_dataset_roles = [];
        for (var i = 0; i < fetched_permissions.manage_dataset_roles.length; i++) {
            selected_manage_dataset_roles.push(fetched_permissions.manage_dataset_roles[i] + ':' + fetched_permissions.manage_dataset_roles[i]);
        }
        
        // ACCESS PERMISSIONS
        if (is_admin){ // Admin has a special select that allows AJAX searching
            var access_select_options = {
              minimumInputLength: 0,
              css: 'access_perm',
              multiple:true,
              placeholder: 'Click to select a role',
              container: self.$el.find('#access_perm'),
              ajax: {
                  url: "/api/libraries/datasets/" + self.id + "/permissions?scope=available",
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
                          id: item[1],
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
                  url: "/api/libraries/datasets/" + self.id + "/permissions?scope=available",
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
                          id: item[1],
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
                  url: "/api/libraries/datasets/" + self.id + "/permissions?scope=available",
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
                          id: item[1],
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
            $.get( "/api/libraries/datasets/" + self.id + "/permissions?scope=available", function( data ) {
                $('.access_perm').html(template({options:data.roles}));
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
    $.post("/api/libraries/datasets/" + self.id + "/permissions?action=make_private").done(function(fetched_permissions) {
      self.model.set({is_unrestricted:false});
      self.showPermissions({fetched_permissions:fetched_permissions})
      mod_toastr.success('The dataset is now private to you.');
    }).fail(function(){
      mod_toastr.error('An error occurred while attempting to make dataset private.');
    });
  },

  removeDatasetRestrictions: function(){
    var self = this;
    $.post("/api/libraries/datasets/" + self.id + "/permissions?action=remove_restrictions")
    .done(function(fetched_permissions) {
      self.model.set({is_unrestricted:true});
      self.showPermissions({fetched_permissions:fetched_permissions})
      mod_toastr.success('Access to this dataset is now unrestricted.');
    })
    .fail(function(){
      mod_toastr.error('An error occurred while attempting to make dataset unrestricted.');
    });
  },

  savePermissions: function(event){
    var self = this;
    var access_roles = this.accessSelectObject.$el.select2('data');
    var manage_roles = this.manageSelectObject.$el.select2('data');
    var modify_roles = this.modifySelectObject.$el.select2('data');

    var access_ids = [];
    var manage_ids = [];
    var modify_ids = [];

    for (var i = access_roles.length - 1; i >= 0; i--) {
      access_ids.push(access_roles[i].id);
    };
    for (var i = manage_roles.length - 1; i >= 0; i--) {
      manage_ids.push(manage_roles[i].id);
    };
    for (var i = modify_roles.length - 1; i >= 0; i--) {
      modify_ids.push(modify_roles[i].id);
    };

    $.post("/api/libraries/datasets/" + self.id + "/permissions?action=set_permissions", { 'access_ids[]': access_ids, 'manage_ids[]': manage_ids, 'modify_ids[]': modify_ids, } )
    .done(function(fetched_permissions){
      //fetch dataset again
      self.showPermissions({fetched_permissions:fetched_permissions})
      mod_toastr.success('Permissions saved.');
    })
    .fail(function(){
      mod_toastr.error('An error occurred while attempting to set dataset permissions.');
    })
  },

  templateDataset : function(){
    var tmpl_array = [];
    // CONTAINER START
    tmpl_array.push('<div class="library_style_container">');

    tmpl_array.push('  <div id="library_toolbar">');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Download dataset" class="btn btn-default toolbtn-download-dataset primary-button" type="button"><span class="fa fa-download"></span> Download</span></button>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Import dataset into history" class="btn btn-default toolbtn-import-dataset primary-button" type="button"><span class="fa fa-book"></span> to History</span></button>');

    tmpl_array.push('   <% if (item.get("can_user_modify")) { %>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Modify library item" class="btn btn-default toolbtn_modify_dataset primary-button" type="button"><span class="fa fa-pencil"></span> Modify</span></button>');
    tmpl_array.push('   <% } %>');
    
    tmpl_array.push('   <% if (item.get("can_user_manage")) { %>');
    tmpl_array.push('   <a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>/permissions"><button data-toggle="tooltip" data-placement="top" title="Manage permissions" class="btn btn-default toolbtn_change_permissions primary-button" type="button"><span class="fa fa-group"></span> Permissions</span></button></a>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Share dataset" class="btn btn-default toolbtn-share-dataset primary-button" type="button"><span class="fa fa-share"></span> Share</span></button>');
    tmpl_array.push('   <% } %>');


    tmpl_array.push('  </div>');

    // BREADCRUMBS
    tmpl_array.push('<ol class="breadcrumb">');
    tmpl_array.push('   <li><a title="Return to the list of libraries" href="#">Libraries</a></li>');
    tmpl_array.push('   <% _.each(item.get("full_path"), function(path_item) { %>');
    tmpl_array.push('   <% if (path_item[0] != item.id) { %>');
    tmpl_array.push('   <li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ');
    tmpl_array.push(    '<% } else { %>');
    tmpl_array.push('   <li class="active"><span title="You are here"><%- path_item[1] %></span></li>');
    tmpl_array.push('   <% } %>');
    tmpl_array.push('   <% }); %>');
    tmpl_array.push('</ol>');

    tmpl_array.push('<% if (item.get("is_unrestricted")) { %>');
    tmpl_array.push('  <div class="alert alert-info">');
    tmpl_array.push('  This dataset is unrestricted so everybody can access it. Just share the URL of this page. ');
    tmpl_array.push('  <button data-toggle="tooltip" data-placement="top" title="Copy to clipboard" class="btn btn-default btn-copy-link-to-clipboard primary-button" type="button"><span class="fa fa-clipboard"></span> To Clipboard</span></button> ');
    tmpl_array.push('  </div>');
    tmpl_array.push('<% } %>');

    tmpl_array.push('<div class="dataset_table">');

    tmpl_array.push('   <table class="grid table table-striped table-condensed">');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>');
    tmpl_array.push('           <td><%= _.escape(item.get("name")) %></td>');
    tmpl_array.push('       </tr>');

    tmpl_array.push('   <% if (item.get("file_ext")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Data type</th>');
    tmpl_array.push('           <td><%= _.escape(item.get("file_ext")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("genome_build")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Genome build</th>');
    tmpl_array.push('           <td><%= _.escape(item.get("genome_build")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("file_size")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Size</th>');
    tmpl_array.push('           <td><%= _.escape(item.get("file_size")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("date_uploaded")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Date uploaded (UTC)</th>');
    tmpl_array.push('           <td><%= _.escape(item.get("date_uploaded")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("uploaded_by")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Uploaded by</th>');
    tmpl_array.push('           <td><%= _.escape(item.get("uploaded_by")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("metadata_data_lines")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Data Lines</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("metadata_comment_lines")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Comment Lines</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("metadata_comment_lines")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("metadata_columns")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Number of Columns</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("metadata_columns")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("metadata_column_types")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Column Types</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("metadata_column_types")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("message")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Message</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("message")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("misc_blurb")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Miscellaneous blurb</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (item.get("misc_info")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Miscellaneous information</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("misc_info")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('    </table>');
    tmpl_array.push('    <div>');
    tmpl_array.push('        <pre class="peek">');
    tmpl_array.push('        </pre>');
    tmpl_array.push('    </div>');

    tmpl_array.push('   <% if (item.get("has_versions")) { %>');
    tmpl_array.push('      <div>');
    tmpl_array.push('      <h3>Expired versions:</h3>');
    tmpl_array.push('      <ul>');
    tmpl_array.push('      <% _.each(item.get("expired_versions"), function(version) { %>');
    tmpl_array.push('        <li><a title="See details of this version" href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>/versions/<%- version[0] %>"><%- version[1] %></a></li>');
    tmpl_array.push('      <% }) %>');
    tmpl_array.push('      <ul>');
    tmpl_array.push('      </div>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('</div>');

    // CONTAINER END
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  }, 

  templateVersion : function(){
    var tmpl_array = [];
    // CONTAINER START
    tmpl_array.push('<div class="library_style_container">');

    tmpl_array.push('  <div id="library_toolbar">');
    tmpl_array.push('   <a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>"><button data-toggle="tooltip" data-placement="top" title="Go to latest dataset" class="btn btn-default primary-button" type="button"><span class="fa fa-caret-left fa-lg"></span> Latest dataset</span></button><a>');
    tmpl_array.push('  </div>');

    // BREADCRUMBS
    tmpl_array.push('<ol class="breadcrumb">');
    tmpl_array.push('   <li><a title="Return to the list of libraries" href="#">Libraries</a></li>');
    tmpl_array.push('   <% _.each(item.get("full_path"), function(path_item) { %>');
    tmpl_array.push('   <% if (path_item[0] != item.id) { %>');
    tmpl_array.push('   <li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ');
    tmpl_array.push(    '<% } else { %>');
    tmpl_array.push('   <li class="active"><span title="You are here"><%- path_item[1] %></span></li>');
    tmpl_array.push('   <% } %>');
    tmpl_array.push('   <% }); %>');
    tmpl_array.push('</ol>');

    tmpl_array.push('  <div class="alert alert-warning">This is an expired version of the library dataset: <%= _.escape(item.get("name")) %></div>');
    
    tmpl_array.push('<div class="dataset_table">');

    tmpl_array.push('   <table class="grid table table-striped table-condensed">');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row" id="id_row" data-id="<%= _.escape(ldda.id) %>">Name</th>');
    tmpl_array.push('           <td><%= _.escape(ldda.get("name")) %></td>');
    tmpl_array.push('       </tr>');

    tmpl_array.push('   <% if (ldda.get("file_ext")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Data type</th>');
    tmpl_array.push('           <td><%= _.escape(ldda.get("file_ext")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("genome_build")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Genome build</th>');
    tmpl_array.push('           <td><%= _.escape(ldda.get("genome_build")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("file_size")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Size</th>');
    tmpl_array.push('           <td><%= _.escape(ldda.get("file_size")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("date_uploaded")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Date uploaded (UTC)</th>');
    tmpl_array.push('           <td><%= _.escape(ldda.get("date_uploaded")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("uploaded_by")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Uploaded by</th>');
    tmpl_array.push('           <td><%= _.escape(ldda.get("uploaded_by")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("metadata_data_lines")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Data Lines</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(ldda.get("metadata_data_lines")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("metadata_comment_lines")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Comment Lines</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(ldda.get("metadata_comment_lines")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("metadata_columns")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Number of Columns</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(ldda.get("metadata_columns")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("metadata_column_types")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Column Types</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(ldda.get("metadata_column_types")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("message")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Message</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(ldda.get("message")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("misc_blurb")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Miscellaneous blurb</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(ldda.get("misc_blurb")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('   <% if (ldda.get("misc_info")) { %>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Miscellaneous information</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(ldda.get("misc_info")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('   <% } %>');

    tmpl_array.push('    </table>');
    tmpl_array.push('    <div>');
    tmpl_array.push('        <pre class="peek">');
    tmpl_array.push('        </pre>');
    tmpl_array.push('    </div>');

    tmpl_array.push('</div>');

    // CONTAINER END
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  },

  templateModifyDataset : function(){
    var tmpl_array = [];
    // CONTAINER START
    tmpl_array.push('<div class="library_style_container">');

    tmpl_array.push('  <div id="library_toolbar">');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Cancel modifications" class="btn btn-default toolbtn_cancel_modifications primary-button" type="button"><span class="fa fa-times"></span> Cancel</span></button>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Save modifications" class="btn btn-default toolbtn_save_modifications primary-button" type="button"><span class="fa fa-floppy-o"></span> Save</span></button>');

    tmpl_array.push('  </div>');

    // BREADCRUMBS
    tmpl_array.push('<ol class="breadcrumb">');
    tmpl_array.push('   <li><a title="Return to the list of libraries" href="#">Libraries</a></li>');
    tmpl_array.push('   <% _.each(item.get("full_path"), function(path_item) { %>');
    tmpl_array.push('   <% if (path_item[0] != item.id) { %>');
    tmpl_array.push('   <li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ');
    tmpl_array.push(    '<% } else { %>');
    tmpl_array.push('   <li class="active"><span title="You are here"><%- path_item[1] %></span></li>');
    tmpl_array.push('   <% } %>');
    tmpl_array.push('   <% }); %>');
    tmpl_array.push('</ol>');

    tmpl_array.push('<div class="dataset_table">');
    tmpl_array.push('<p>For more editing options please import the dataset to history and use "Edit attributes" on it.</p>');
    tmpl_array.push('   <table class="grid table table-striped table-condensed">');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row" id="id_row" data-id="<%= _.escape(item.get("ldda_id")) %>">Name</th>');
    tmpl_array.push('           <td><input class="input_dataset_name form-control" type="text" placeholder="name" value="<%= _.escape(item.get("name")) %>"></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Data type</th>');
    tmpl_array.push('           <td><%= _.escape(item.get("file_ext")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Genome build</th>');
    tmpl_array.push('           <td><%= _.escape(item.get("genome_build")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Size</th>');
    tmpl_array.push('           <td><%= _.escape(item.get("file_size")) %></td>');
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
    tmpl_array.push('           <th scope="row">Message</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("message")) %></td>');
    tmpl_array.push('       </tr>');    
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Miscellaneous information</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("misc_info")) %></td>');
    tmpl_array.push('       </tr>');
    tmpl_array.push('       <tr>');
    tmpl_array.push('           <th scope="row">Miscellaneous blurb</th>');
    tmpl_array.push('           <td scope="row"><%= _.escape(item.get("misc_blurb")) %></td>');
    tmpl_array.push('       </tr>');    
    tmpl_array.push('   </table>');
    tmpl_array.push('<div>');
    tmpl_array.push('   <pre class="peek">');
    tmpl_array.push('   </pre>');
    tmpl_array.push('</div>');
    tmpl_array.push('</div>');

    // CONTAINER END
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  },

  templateDatasetPermissions : function(){
    var tmpl_array = [];
    // CONTAINER START
    tmpl_array.push('<div class="library_style_container">');

    tmpl_array.push('  <div id="library_toolbar">');
    tmpl_array.push('   <a href="#folders/<%- item.get("folder_id") %>"><button data-toggle="tooltip" data-placement="top" title="Go back to containing folder" class="btn btn-default primary-button" type="button"><span class="fa fa-folder-open-o"></span> Containing Folder</span></button></a>');
    tmpl_array.push('   <a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>"><button data-toggle="tooltip" data-placement="top" title="Go back to dataset" class="btn btn-default primary-button" type="button"><span class="fa fa-file-o"></span> Dataset Details</span></button><a>');

    tmpl_array.push('  </div>');

    // BREADCRUMBS
    tmpl_array.push('<ol class="breadcrumb">');
    tmpl_array.push('   <li><a title="Return to the list of libraries" href="#">Libraries</a></li>');
    tmpl_array.push('   <% _.each(item.get("full_path"), function(path_item) { %>');
    tmpl_array.push('   <% if (path_item[0] != item.id) { %>');
    tmpl_array.push('   <li><a title="Return to this folder" href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> </li> ');
    tmpl_array.push(    '<% } else { %>');
    tmpl_array.push('   <li class="active"><span title="You are here"><%- path_item[1] %></span></li>');
    tmpl_array.push('   <% } %>');
    tmpl_array.push('   <% }); %>');
    tmpl_array.push('</ol>');

    tmpl_array.push('<h1>Dataset: <%= _.escape(item.get("name")) %></h1>');

    tmpl_array.push('<div class="alert alert-warning">');
    tmpl_array.push('<% if (is_admin) { %>');
    tmpl_array.push('You are logged in as an <strong>administrator</strong> therefore you can manage any dataset on this Galaxy instance. Please make sure you understand the consequences.');
    tmpl_array.push('<% } else { %>');
    tmpl_array.push('You can assign any number of roles to any of the following permission types. However please read carefully the implications of such actions.');
    tmpl_array.push('<% } %>');
    tmpl_array.push('</div>');
    
    tmpl_array.push('<div class="dataset_table">');

    tmpl_array.push('<h2>Library-related permissions</h2>');
    tmpl_array.push('<h4>Roles that can modify the library item</h4>');
    tmpl_array.push('<div id="modify_perm" class="modify_perm roles-selection"></div>');
    tmpl_array.push('<div class="alert alert-info roles-selection">User with <strong>any</strong> of these roles can modify name, metadata, and other information about this library item.</div>');
    tmpl_array.push('<hr/>');

    tmpl_array.push('<h2>Dataset-related permissions</h2>');
    tmpl_array.push('<div class="alert alert-warning">Changes made below will affect <strong>every</strong> library item that was created from this dataset and also every history this dataset is part of.</div>');

    tmpl_array.push('<% if (!item.get("is_unrestricted")) { %>');
    tmpl_array.push(' <p>You can remove all access restrictions on this dataset. ');
    tmpl_array.push(' <button data-toggle="tooltip" data-placement="top" title="Everybody will be able to access the dataset." class="btn btn-default btn-remove-restrictions primary-button" type="button">');
    tmpl_array.push(' <span class="fa fa-globe"> Remove restrictions</span>');
    tmpl_array.push(' </button>');
    tmpl_array.push(' </p>');
    tmpl_array.push('<% } else { %>');
    tmpl_array.push('  This dataset is unrestricted so everybody can access it. Just share the URL of this page.');
    tmpl_array.push('  <button data-toggle="tooltip" data-placement="top" title="Copy to clipboard" class="btn btn-default btn-copy-link-to-clipboard primary-button" type="button"><span class="fa fa-clipboard"> To Clipboard</span></button> ');
    tmpl_array.push('  <p>You can make this dataset private to you. ');
    tmpl_array.push(' <button data-toggle="tooltip" data-placement="top" title="Only you will be able to access the dataset." class="btn btn-default btn-make-private primary-button" type="button"><span class="fa fa-key"> Make Private</span></button>');
    tmpl_array.push(' </p>');
    // tmpl_array.push(' <p>You can share this dataset privately with other Galaxy users. ');
    // tmpl_array.push(' <button data-toggle="tooltip" data-placement="top" title="Only you and the suers you choose will be able to access the dataset." class="btn btn-default btn-share-dataset primary-button" type="button"><span class="fa fa-share"> Share Privately</span></button>');
    // tmpl_array.push(' </p>');
    tmpl_array.push('<% } %>');

    tmpl_array.push('<h4>Roles that can access the dataset</h4>');
    tmpl_array.push('<div id="access_perm" class="access_perm roles-selection"></div>');
    tmpl_array.push('<div class="alert alert-info roles-selection">User has to have <strong>all these roles</strong> in order to access this dataset. Users without access permission <strong>cannot</strong> have other permissions on this dataset. If there are no access roles set on the dataset it is considered <strong>unrestricted</strong>.</div>');
    tmpl_array.push('<h4>Roles that can manage permissions on the dataset</h4>');
    tmpl_array.push('<div id="manage_perm" class="manage_perm roles-selection"></div>');
    tmpl_array.push('<div class="alert alert-info roles-selection">User with <strong>any</strong> of these roles can manage permissions of this dataset. If you remove yourself you will loose the ability manage this dataset unless you are an admin.</div>');
    tmpl_array.push('<button data-toggle="tooltip" data-placement="top" title="Save modifications made on this page" class="btn btn-default toolbtn_save_permissions primary-button" type="button"><span class="fa fa-floppy-o"></span> Save</span></button>');

    tmpl_array.push('</div>');

    // CONTAINER END
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  },

  templateBulkImportInModal: function(){
    var tmpl_array = [];

    tmpl_array.push('<span id="history_modal_combo_bulk" style="width:90%; margin-left: 1em; margin-right: 1em; ">');
    tmpl_array.push('Select history: ');
    tmpl_array.push('<select id="dataset_import_single" name="dataset_import_single" style="width:50%; margin-bottom: 1em; "> ');
    tmpl_array.push('   <% _.each(histories, function(history) { %>'); //history select box
    tmpl_array.push('       <option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>');
    tmpl_array.push('   <% }); %>');
    tmpl_array.push('</select>');
    tmpl_array.push('</span>');

    return _.template(tmpl_array.join(''));
  },

  templateAccessSelect: function(){
    var tmpl_array = [];

    tmpl_array.push('<select id="access_select" multiple>');

    tmpl_array.push('   <% _.each(options, function(option) { %>');    
    tmpl_array.push('       <option value="<%- option.name %>"><%- option.name %></option>');
    tmpl_array.push('   <% }); %>');

    tmpl_array.push('</select>');


    return _.template(tmpl_array.join(''));
  }

});

return {
    LibraryDatasetView: LibraryDatasetView
};

});
