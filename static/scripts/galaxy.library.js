// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === MAIN GALAXY LIBRARY MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

// global variables
var library_router  = null;

// dependencies
define([
    "galaxy.masthead", 
    "utils/utils",
    "libs/toastr",
    "mvc/library/library-model",
    "mvc/library/library-folderlist-view",
    "mvc/library/library-librarylist-view",
    "mvc/library/library-librarytoolbar-view"], 
function(mod_masthead, 
         mod_utils, 
         mod_toastr,
         mod_library_model,
         mod_folderlist_view,
         mod_librarylist_view,
         mod_librarytoolbar_view) {

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

    initialize : function(){
        toolbarView = new mod_librarytoolbar_view.ToolbarView();
        galaxyLibraryview = new mod_librarylist_view.GalaxyLibraryview();
        library_router = new LibraryRouter();
        
        folderContentView = null;

        library_router.on('route:libraries', function() {
          // initialize and render the toolbar first
          toolbarView = new mod_librarytoolbar_view.ToolbarView();
          // initialize and render libraries second
          galaxyLibraryview = new mod_librarylist_view.GalaxyLibraryview();
        });

        library_router.on('route:sort_libraries', function(sort_by, order) {
          // sort libraries list
          galaxyLibraryview.sortLibraries(sort_by, order);
          galaxyLibraryview.render();
        });

        library_router.on('route:folder_content', function(id) {
          // render folder contents
          if (!folderContentView) {folderContentView = new mod_folderlist_view.FolderContentView();}
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
