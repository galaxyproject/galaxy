// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === GALAXY LIBRARY MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

// global variables
var view            = null;
var library_router  = null;

// dependencies
define(["galaxy.modal", "galaxy.master", "galaxy.library.router"], function(mod_modal, mod_master, router) {

// MMMMMMMMMMMMMMM
// === Models ====
// MMMMMMMMMMMMMMM

    // LIBRARY
    var Library = Backbone.Model.extend({
      urlRoot: '/api/libraries',
    });

    // LIBRARIES
    var Libraries = Backbone.Collection.extend({
      url: '/api/libraries',
      model: Library
    });

    // ITEM
    var Item = Backbone.Model.extend({
    })

    // FOLDER
    var Folder = Backbone.Collection.extend({
      model: Item      
    })

    // Container for folder contents (folders, items and metadata).
    var FolderContainer = Backbone.Model.extend({
       defaults: {
        folder: new Folder(),
        full_path: "unknown",
        urlRoot: "/api/folders/",
        id: "unknown"
      },
      parse: function(obj) {
          this.full_path = obj[0].full_path;
          // this.folder.reset(obj[1].folder_contents);
          // update the inner collection
          this.get("folder").reset(obj[1].folder_contents);
          return obj;
        }
    })

// MMMMMMMMMMMMMM
// === Views ====
// MMMMMMMMMMMMMM

// galaxy folder
var FolderContentView = Backbone.View.extend({
      el : '#center',
    // initialize
    initialize : function(){
        // view = this;
        //set up the library router
        // this.set_up_router();

        //render
        // this.render();
    },    
   // set up router
    set_up_router : function(){   
        if (library_router === null){
            library_router = new router.LibraryRouter();
            Backbone.history.start();   
        }
    },
      template_folder : function (){
                tmpl_array = [];

                tmpl_array.push('<% _.each(path, function(path_item) { %>');
                tmpl_array.push('<% if (path_item[0] != id) { %>');
                tmpl_array.push('<a href="#/folders/<%- path_item[0] %>"><%- path_item[1] %></a> |');
                tmpl_array.push('<% } else { %>');
                tmpl_array.push('<%- path_item[1] %>');
                tmpl_array.push('<% } %>');
                tmpl_array.push('<% }); %>');
                tmpl_array.push('<table class="table table-hover table-condensed">');
                tmpl_array.push('   <thead>');
                tmpl_array.push('       <th style="text-align: center; width: 20px; "><input id="select-all-checkboxes" style="margin: 0;" type="checkbox"></th>');
                tmpl_array.push('       <th>name</th>');
                tmpl_array.push('       <th>type</th>');
                tmpl_array.push('   </thead>');
                tmpl_array.push('   <tbody>');
                tmpl_array.push('       <% _.each(items, function(content_item) { %>');
                tmpl_array.push('       <tr class="folder_row" id="<%- content_item.id %>">');
                tmpl_array.push('           <td style="text-align: center; "><input style="margin: 0;" type="checkbox"></td>');
                tmpl_array.push('           <% if (content_item.get("type") === "folder") { %>');
                tmpl_array.push('           <td><a href="#/folders/<%- content_item.id %>"><%- content_item.get("name") %></a>');
                tmpl_array.push('           <% if (content_item.get("item_count") === 0) { %>');
                tmpl_array.push('           <span class="muted">(empty folder)</span>');
                tmpl_array.push('           <% } %>');
                tmpl_array.push('           </td>');
                tmpl_array.push('           <% } else {  %>');
                tmpl_array.push('           <td><%- content_item.get("name") %></td>');
                tmpl_array.push('           <% } %>  ');
                tmpl_array.push('           <td><%= _.escape(content_item.get("type")) %></td>');
                tmpl_array.push('       </tr>');
                tmpl_array.push('       <% }); %>');
                tmpl_array.push('       ');
                tmpl_array.push('       ');
                tmpl_array.push('       ');
                tmpl_array.push('   </tbody>');
                tmpl_array.push('</table>');

                return tmpl_array.join('');
      },
      events: {
        'click #select-all-checkboxes' : 'selectAll',
        'click .folder_row' : 'selectClicked'
      },
      render: function (options) {
        var that = this;

        var folderContainer = new FolderContainer({id: options.id});
        folderContainer.url = folderContainer.attributes.urlRoot + options.id + '/contents';

        folderContainer.fetch({
          success: function (container) {
          // folderContainer.attributes.folder = container.attributes.folder;
          var template = _.template(that.template_folder(), {path: folderContainer.full_path, items: folderContainer.attributes.folder.models, id: options.id});
          that.$el.html(template);
          }
        })
      },
      selectAll : function (ev) {
         var selected = ev.target.checked;
         // Iterate each checkbox
         $(':checkbox').each(function () { this.checked = selected; });
      },
      selectClicked : function (ev) {
        var checkbox = $("#" + ev.target.parentElement.id).find(':checkbox')
        if (checkbox[0] != undefined) {
          if (checkbox[0].checked){
            checkbox[0].checked = '';
          } else {
            checkbox[0].checked = 'selected';
          }
        }
      }
});


// galaxy library
var GalaxyLibraryview = Backbone.View.extend({
    el: '#center',

   events: {
        'click #create_new_library_btn' : 'show_library_modal'
      },

       
    // initialize
    initialize : function(){
        // view = this;
        //set up the libray router
        // this.set_up_router();

        //render
        // this.render();
    },    

    // set up router
    set_up_router : function(){
        if (library_router === null){
            library_router = new router.LibraryRouter();
            Backbone.history.start();   
        }
    },

    // template
    template_library_list : function (){
        tmpl_array = [];

        tmpl_array.push('');
        tmpl_array.push('<h1>Welcome to the data libraries</h1>');
        tmpl_array.push('<a href="" id="create_new_library_btn" class="btn btn-primary">New Library</a>');
        tmpl_array.push('<table class="table table-striped">');
        tmpl_array.push('   <thead>');
        tmpl_array.push('    <th>name</th>');
        tmpl_array.push('     <th>description</th>');
        tmpl_array.push('     <th>synopsis</th> ');
        tmpl_array.push('     <th>model type</th> ');
        tmpl_array.push('     <th>id</th> ');
        tmpl_array.push('   </thead>');
        tmpl_array.push('   <tbody>');
        tmpl_array.push('       <% _.each(libraries, function(library) { %>');
        tmpl_array.push('           <tr>');
        tmpl_array.push('               <td><a href="#/folders/<%- library.id %>"><%- library.get("name") %></a></td>');
        tmpl_array.push('               <td><%= _.escape(library.get("description")) %></td>');
        tmpl_array.push('               <td><%= _.escape(library.get("synopsis")) %></td>');
        tmpl_array.push('               <td><%= _.escape(library.get("model_class")) %></td>');
        tmpl_array.push('               <td><a href="#/folders/<%- library.id %>"><%= _.escape(library.get("id")) %></a></td>');
        tmpl_array.push('           </tr>');
        tmpl_array.push('       <% }); %>');
        tmpl_array.push('');
        tmpl_array.push('');
        tmpl_array.push('');
        tmpl_array.push('');
        tmpl_array.push('   </tbody>');
        tmpl_array.push('</table>');

        return tmpl_array.join('');
    },

    // render
    render: function () {
        var that = this;
        // if (typeof libraries === "undefined") {
          libraries = new Libraries();
        // }
        libraries.fetch({
          success: function (libraries) {
            var template = _.template(that.template_library_list(), {libraries: libraries.models});
            that.$el.html(template);
          }
        })
    },

    // own modal
    modal : null,

    // show/hide create library modal
    show_library_modal : function (e)
    {
        // prevent default
        e.preventDefault();
        
        // create modal
        if (!this.modal){
            // make modal
            var self = this;
            this.modal = new mod_modal.GalaxyModal(
            {
                title   : 'Create New Library',
                body    : this.template_new_library(),
                buttons : {
                    'Create' : function() {self.create_new_library_event()},
                    'Close'  : function() {self.modal.hide()}
                }
            });
        }
        
        // show modal
        this.modal.show();
    },
    create_new_library_event: function(){
        var libraryDetails = this.serialize_new_library();
        var library = new Library();
        library.save(libraryDetails, {
          success: function (library) {

            library_router.navigate('', {trigger: true})
          }
        });
        // console.log(libraryDetails);
        return false;
    },
    serialize_new_library : function(){
        return {
            name: $("input[name='Name']").val(),
            description: $("input[name='Description']").val(),
            synopsis: $("input[name='Synopsis']").val()
        };
    },
    // load html template
    template_new_library: function()
    {
        tmpl_array = [];
        tmpl_array.push('<div id="new_library_modal">');
        tmpl_array.push('<form>');
        tmpl_array.push('<input type="text" name="Name" value="" placeholder="Name">');
        tmpl_array.push('<input type="text" name="Description" value="" placeholder="Description">');
        // tmpl_array.push('<label>Synopsis</label>');
        tmpl_array.push('<input type="text" name="Synopsis" value="" placeholder="Synopsis">');
        tmpl_array.push('');
        tmpl_array.push('</form>');
        tmpl_array.push('</div>');
        return tmpl_array.join('');


        // return  '<div id="'+ id +'"></div>';
    }
});

// galaxy library wrapper View
var GalaxyLibrary = Backbone.View.extend({
    folderContentView : null,
    galaxyLibraryview : null,
    initialize : function(){

        folderContentView = new FolderContentView();
        galaxyLibraryview = new GalaxyLibraryview();

        library_router = new router.LibraryRouter();
            
        library_router.on('route:libraries', function() {
          // render libraries list
          galaxyLibraryview.render();
        })           
         
        library_router.on('route:folder_content', function(id) {
          // render folder's contents
          folderContentView.render({id: id});
        
        })      

        // library_router.on('route:show_library_modal', function() {
        //   // render folder's contents
        //   galaxyLibraryview.show_library_modal();
        
        // })

        Backbone.history.start();   

        return this
    }
});

// return
return {
    GalaxyApp: GalaxyLibrary
};

});
