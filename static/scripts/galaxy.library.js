// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === GALAXY LIBRARY MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

// global variables
var view            = null;
var library_router  = null;

// dependencies
define(["galaxy.modal", "galaxy.master"], function(mod_modal, mod_master) {

// MMMMMMMMMMMMMMM
// === Models ====
// MMMMMMMMMMMMMMM

    // LIBRARY
    var Library = Backbone.Model.extend({
      urlRoot: '/api/libraries'
  });

    // LIBRARIES
    var Libraries = Backbone.Collection.extend({
      url: '/api/libraries',
      model: Library
  });

    // ITEM
    var Item = Backbone.Model.extend({
        urlRoot : '/api/libraries/datasets'
    })

    // FOLDER
    var Folder = Backbone.Collection.extend({
      model: Item      
  })

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
  })

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

    //ROUTER
    var LibraryRouter = Backbone.Router.extend({    
        routes: {
            "" :                 "libraries",
            "folders/:id" :      "folder_content"
        }
    });


// MMMMMMMMMMMMMM
// === Views ====
// MMMMMMMMMMMMMM

// galaxy folder
var FolderContentView = Backbone.View.extend({
    //main element
    el : '#center',
    // initialize
    initialize : function(){
        this.folders = [];
    },    
    // set up 
    templateFolder : function (){
        var tmpl_array = [];

        tmpl_array.push('<a href="#">Libraries</a> | ');
        tmpl_array.push('<% _.each(path, function(path_item) { %>'); //breadcrumb
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
                tmpl_array.push('       <td style="text-align: center; "><input style="margin: 0;" type="checkbox"></td>');
        tmpl_array.push('           <% if (content_item.get("type") === "folder") { %>'); //folder
        tmpl_array.push('           <td><a href="#/folders/<%- content_item.id %>"><%- content_item.get("name") %></a>');
        tmpl_array.push('           <% if (content_item.get("item_count") === 0) { %>'); //empty folder
        tmpl_array.push('           <span class="muted">(empty folder)</span>');
        tmpl_array.push('           <% } %>');
        tmpl_array.push('           </td>');
        tmpl_array.push('           <% } else {  %>');
        tmpl_array.push('           <td><a class="library-dataset" href="#"><%- content_item.get("name") %></a></td>'); //dataset
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
    templateDatasetModal : function(){
        var tmpl_array = [];

        tmpl_array.push('<div id="dataset_info_modal">');
        tmpl_array.push('   <table class="table table-striped table-condensed">');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row">Name</th>');
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
        tmpl_array.push('           <th scope="row">Date uploaded</th>');
        tmpl_array.push('           <td><%= _.escape(item.get("date_uploaded")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <tr>');
        tmpl_array.push('           <th scope="row">Uploaded by</th>');
        tmpl_array.push('           <td><%= _.escape(item.get("uploaded_by")) %></td>');
        tmpl_array.push('       </tr>');
        // tmpl_array.push('    </table>');
        // tmpl_array.push('    <hr/>');
        // tmpl_array.push('    <table class="table table-striped">');
        tmpl_array.push('           <tr scope="row">');
        tmpl_array.push('           <th scope="row">Data Lines</th>');
        tmpl_array.push('           <td scope="row"><%= _.escape(item.get("metadata_data_lines")) %></td>');
        tmpl_array.push('       </tr>');
        tmpl_array.push('       <th scope="row">Comment Lines</th>');
        tmpl_array.push('           <% if (item.get("metadata_comment_lines") === "") { %>'); //folder        
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
        tmpl_array.push('       <tr>');
        tmpl_array.push('       ');
        tmpl_array.push('   </table>');
        // tmpl_array.push('   <hr/>');
        tmpl_array.push('   <pre class="peek">');
        tmpl_array.push('   </pre>');
        tmpl_array.push('</div>');

        return tmpl_array.join('');
    },
    templateHistorySelectInModal : function(){
        var tmpl_array = [];

        tmpl_array.push('<span id="history_modal_footer" style="width:60%;">');
        tmpl_array.push('<select name="history_import" style="width:60%; margin-left: 2em; "> ');
        tmpl_array.push('   <% _.each(histories, function(history) { %>'); //history select box
            tmpl_array.push('       <option value="<%= _.escape(history.get("id")) %>"><%= _.escape(history.get("name")) %></option>');
            tmpl_array.push('   <% }); %>');
            tmpl_array.push('</span>');
            tmpl_array.push('</div>');
            tmpl_array.push('');

            return tmpl_array.join('');
        },
      // to string
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
        events: {
            'click #select-all-checkboxes' : 'selectAll',
            'click .folder_row' : 'selectClicked',
            'click .library-dataset' : 'showDatasetDetails'
        },
      //self modal
      modal : null,
      //loaded folders
      folders : null,
      //render the view
      render: function (options) {
        var that = this;

        var folderContainer = new FolderContainer({id: options.id});
        folderContainer.url = folderContainer.attributes.urlRoot + options.id + '/contents';

        folderContainer.fetch({
          success: function (container) {
              // folderContainer.attributes.folder = container.attributes.folder;
              var template = _.template(that.templateFolder(), {path: folderContainer.full_path, items: folderContainer.attributes.folder.models, id: options.id});
              that.$el.html(template);
          }
      })
    },
      //show modal with dataset info
      showDatasetDetails : function(e){
        // prevent default
        e.preventDefault();
        
        //TODO check whether we already have the data

        //load the ID of the row
        var id = $(e.target).parent().parent().attr('id');
        
        //create new item
        var item = new Item();
        var histories = new GalaxyHistories();
        item.id = id;
        var self = this;
        //fetch the dataset info
        item.fetch({
          success: function (item) {
                //fetch user histories for import 
                histories.fetch({
                    success: function (histories){self.modalFetchSuccess(item, histories)}
                });
            }
        });
    },

    modalFetchSuccess : function(item, histories){
        var histories_modal = this.templateHistorySelectInModal();
        var size = this.size_to_string(item.get('file_size'));
        var template = _.template(this.templateDatasetModal(), { item : item, size : size });
            // make modal
            var self = this;
            this.modal = new mod_modal.GalaxyModal({
                title   : 'Dataset Details',
                body    : template,
                buttons : {
                    'Import' : function() {self.importIntoHistory()},
                    // 'Notify' : function() {self.modal.showNotification("TEST")},
                    'Close'  : function() {self.modal.hide()}
                }
            });
            $(".peek").html(item.get("peek"));
            // this.modal.hideButton('Import');
            // $(this.modal.elMain).find('.modal-footer').prepend("<div>BUBUBUBU" + "</div>");
            var history_footer_tmpl = _.template(this.templateHistorySelectInModal(), {histories : histories.models});

            $(this.modal.elMain).find('.buttons').prepend(history_footer_tmpl);

            // show the prepared modal
            this.modal.show();
        },

        importIntoHistory : function(){
            var history_id = 'a0c15f4d91084599';
            var library_dataset_id = '03501d7626bd192f';

            var historyItem = new HistoryItem();
            var self = this;
            historyItem.url = historyItem.urlRoot + history_id + '/contents';
            console.log(historyItem);
            historyItem.save({ content : library_dataset_id, source : 'library' }, { success : function(){
                self.modal.showNotification('Dataset imported', 3000, '#e1f4e0', '#32a427');
            }
        });
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
    },    

    // template
    template_library_list : function (){
        tmpl_array = [];

        tmpl_array.push('');
        tmpl_array.push('<h1>Welcome to the data libraries</h1>');
        tmpl_array.push('<a href="" id="create_new_library_btn" class="btn btn-primary icon-file ">New Library</a>');
        tmpl_array.push('<table class="table table-striped">');
        tmpl_array.push('   <thead>');
        tmpl_array.push('    <th>name</th>');
        tmpl_array.push('     <th>description</th>');
        tmpl_array.push('     <th>synopsis</th> ');
        tmpl_array.push('     <th>model type</th> ');
        // tmpl_array.push('     <th>id</th> ');
        tmpl_array.push('   </thead>');
        tmpl_array.push('   <tbody>');
        tmpl_array.push('       <% _.each(libraries, function(library) { %>');
            tmpl_array.push('           <tr>');
            tmpl_array.push('               <td><a href="#/folders/<%- library.id %>"><%- library.get("name") %></a></td>');
            tmpl_array.push('               <td><%= _.escape(library.get("description")) %></td>');
            tmpl_array.push('               <td><%= _.escape(library.get("synopsis")) %></td>');
            tmpl_array.push('               <td><%= _.escape(library.get("model_class")) %></td>');
        // tmpl_array.push('               <td><a href="#/folders/<%- library.id %>"><%= _.escape(library.get("id")) %></a></td>');
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
            var template = _.template(that.template_library_list(), { libraries : libraries.models });
            that.$el.html(template);
        }
    })
    },

    // own modal
    modal : null,

    // show/hide create library modal
    show_library_modal : function (e){
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
        var self = this;
        library.save(libraryDetails, {
          success: function (library) {
            self.modal.hide();
            self.clear_library_modal();
            self.render();
        }
    });
        return false;
    },
    clear_library_modal : function(){
        $("input[name='Name']").val('');
        $("input[name='Description']").val('');
        $("input[name='Synopsis']").val('');
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

        library_router = new LibraryRouter();

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
