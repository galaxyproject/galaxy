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

var LibraryView = Backbone.View.extend({
  el: '#center',

  model: null,

  options: {

  },

  events: {
    "click .toolbtn_save_permissions"     :   "savePermissions"
  },

  initialize: function(options){
    this.options = _.extend(this.options, options);
    if (this.options.id){
      this.fetchLibrary();
    }
  },

  fetchLibrary: function(options){
    this.options = _.extend(this.options, options);
    this.model = new mod_library_model.Library({id:this.options.id});
    var that = this;
    this.model.fetch({
      success: function() {
        if (that.options.show_permissions){
            that.showPermissions();
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
    $(".tooltip").remove();
    this.options = _.extend(this.options, options);
    var template = this.templateLibrary();
    this.$el.html(template({item: this.model}));
    $("#center [data-toggle]").tooltip();
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
      if (this.options.fetched_permissions.access_library_role_list.length === 0){
        this.model.set({is_unrestricted:true});
      } else{
        this.model.set({is_unrestricted:false});
      }
    }
    var is_admin = false;
    if (Galaxy.currUser){
      is_admin = Galaxy.currUser.isAdmin();
    } 
    var template = this.templateLibraryPermissions();
    this.$el.html(template({library: this.model, is_admin:is_admin}));

    var self = this;
    if (this.options.fetched_permissions === undefined){
      $.get( "/api/libraries/" + self.id + "/permissions?scope=current").done(function(fetched_permissions) {
        self.prepareSelectBoxes({fetched_permissions:fetched_permissions});
      }).fail(function(){
          mod_toastr.error('An error occurred while attempting to fetch library permissions.');
      });
    } else {
      this.prepareSelectBoxes({});
    }

    $("#center [data-toggle]").tooltip();
    //hack to show scrollbars
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
    var self = this;

    var selected_access_library_roles = this._serializeRoles(fetched_permissions.access_library_role_list);
    var selected_add_item_roles = this._serializeRoles(fetched_permissions.add_library_item_role_list);
    var selected_manage_library_roles = this._serializeRoles(fetched_permissions.manage_library_role_list);
    var selected_modify_library_roles = this._serializeRoles(fetched_permissions.modify_library_role_list);

    self.accessSelectObject = new mod_select.View(this._createSelectOptions(this, 'access_perm', selected_access_library_roles, true));
    self.addSelectObject = new mod_select.View(this._createSelectOptions(this, 'add_perm', selected_add_item_roles, false));
    self.manageSelectObject = new mod_select.View(this._createSelectOptions(this, 'manage_perm', selected_manage_library_roles, false));
    self.modifySelectObject = new mod_select.View(this._createSelectOptions(this, 'modify_perm', selected_modify_library_roles, false));
  },

  _createSelectOptions: function(self, id, init_data, is_library_access){
    is_library_access = is_library_access === true ? is_library_access : false;
    var select_options = {
      minimumInputLength: 0,
      css: id,
      multiple:true,
      placeholder: 'Click to select a role',
      container: self.$el.find('#' + id),
      ajax: {
          url: "/api/libraries/" + self.id + "/permissions?scope=available&is_library_access=" + is_library_access,
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
      // initialData: init_data.join(','),
      initialData: init_data,
      dropdownCssClass: "bigdrop" // apply css that makes the dropdown taller
    };

    return select_options;
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

  _extractIds: function(roles_list){
    ids_list = [];
    for (var i = roles_list.length - 1; i >= 0; i--) {
      ids_list.push(roles_list[i].id);
    };
    return ids_list;
  },
  savePermissions: function(event){
    var self = this;

    var access_ids = this._extractIds(this.accessSelectObject.$el.select2('data'));
    var add_ids = this._extractIds(this.addSelectObject.$el.select2('data'));
    var manage_ids = this._extractIds(this.manageSelectObject.$el.select2('data'));
    var modify_ids = this._extractIds(this.modifySelectObject.$el.select2('data'));

    $.post("/api/libraries/" + self.id + "/permissions?action=set_permissions", { 'access_ids[]': access_ids, 'add_ids[]': add_ids, 'manage_ids[]': manage_ids, 'modify_ids[]': modify_ids, } )
    .done(function(fetched_permissions){
      //fetch dataset again
      self.showPermissions({fetched_permissions:fetched_permissions})
      mod_toastr.success('Permissions saved.');
    })
    .fail(function(){
      mod_toastr.error('An error occurred while attempting to set library permissions.');
    })
  },

  templateLibrary : function(){
    var tmpl_array = [];
    // CONTAINER START
    tmpl_array.push('<div class="library_style_container">');

    tmpl_array.push('  <div id="library_toolbar">');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Modify library item" class="btn btn-default toolbtn_modify_dataset primary-button" type="button"><span class="fa fa-pencil"></span> Modify</span></button>');
    tmpl_array.push('   <a href="#folders/<%- item.get("folder_id") %>/datasets/<%- item.id %>/permissions"><button data-toggle="tooltip" data-placement="top" title="Manage permissions" class="btn btn-default toolbtn_change_permissions primary-button" type="button"><span class="fa fa-group"></span> Permissions</span></button></a>');
    tmpl_array.push('   <button data-toggle="tooltip" data-placement="top" title="Share dataset" class="btn btn-default toolbtn-share-dataset primary-button" type="button"><span class="fa fa-share"></span> Share</span></button>');
    tmpl_array.push('  </div>');

    // tmpl_array.push('<% if (item.get("is_unrestricted")) { %>');
    tmpl_array.push('  <p>');
    tmpl_array.push('  This dataset is unrestricted so everybody can access it. Just share the URL of this page. ');
    tmpl_array.push('  <button data-toggle="tooltip" data-placement="top" title="Copy to clipboard" class="btn btn-default btn-copy-link-to-clipboard primary-button" type="button"><span class="fa fa-clipboard"></span> To Clipboard</span></button> ');
    tmpl_array.push('  </p>');
    // tmpl_array.push('<% } %>');

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

    tmpl_array.push('    </table>');
    tmpl_array.push('</div>');

    // CONTAINER END
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  },

  templateLibraryPermissions : function(){
    var tmpl_array = [];
    // CONTAINER START
    tmpl_array.push('<div class="library_style_container">');
    

    tmpl_array.push('  <div id="library_toolbar">');
    tmpl_array.push('   <a href="#"><button data-toggle="tooltip" data-placement="top" title="Go back to the list of Libraries" class="btn btn-default primary-button" type="button"><span class="fa fa-list"></span> Libraries</span></button></a>');
    tmpl_array.push('  </div>');

    tmpl_array.push('<h1>Library: <%= _.escape(library.get("name")) %></h1>');

    tmpl_array.push('<div class="alert alert-warning">');
    tmpl_array.push('<% if (is_admin) { %>');
    tmpl_array.push('You are logged in as an <strong>administrator</strong> therefore you can manage any library on this Galaxy instance. Please make sure you understand the consequences.');
    tmpl_array.push('<% } else { %>');
    tmpl_array.push('You can assign any number of roles to any of the following permission types. However please read carefully the implications of such actions.');
    tmpl_array.push('<% }%>');
    tmpl_array.push('</div>');
    
    tmpl_array.push('<div class="dataset_table">');

    tmpl_array.push('<h2>Library permissions</h2>');

    tmpl_array.push('<h4>Roles that can access the library</h4>');
    tmpl_array.push('<div id="access_perm" class="access_perm roles-selection"></div>');
    tmpl_array.push('<div class="alert alert-info roles-selection">User with <strong>any</strong> of these roles can access this library. If there are no access roles set on the library it is considered <strong>unrestricted</strong>.</div>');
    
    tmpl_array.push('<h4>Roles that can manage permissions on this library</h4>');
    tmpl_array.push('<div id="manage_perm" class="manage_perm roles-selection"></div>');
    tmpl_array.push('<div class="alert alert-info roles-selection">User with <strong>any</strong> of these roles can manage permissions on this library (includes giving access).</div>');

    tmpl_array.push('<h4>Roles that can add items to this library</h4>');
    tmpl_array.push('<div id="add_perm" class="add_perm roles-selection"></div>');
    tmpl_array.push('<div class="alert alert-info roles-selection">User with <strong>any</strong> of these roles can add items to this library (folders and datasets).</div>');

    tmpl_array.push('<h4>Roles that can modify this library</h4>');
    tmpl_array.push('<div id="modify_perm" class="modify_perm roles-selection"></div>');
    tmpl_array.push('<div class="alert alert-info roles-selection">User with <strong>any</strong> of these roles can modify this library (name, synopsis, etc.).</div>');

    tmpl_array.push('<button data-toggle="tooltip" data-placement="top" title="Save modifications made on this page" class="btn btn-default toolbtn_save_permissions primary-button" type="button"><span class="fa fa-floppy-o"></span> Save</span></button>');

    tmpl_array.push('</div>');

    // CONTAINER END
    tmpl_array.push('</div>');

    return _.template(tmpl_array.join(''));
  }

});

return {
    LibraryView: LibraryView
};

});
