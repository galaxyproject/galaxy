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
    "mvc/base-mvc",
    "mvc/library/library-model",
    "mvc/library/library-folderlist-view",
    "mvc/library/library-librarylist-view",
    "mvc/library/library-librarytoolbar-view"], 
function(mod_masthead, 
         mod_utils, 
         mod_toastr,
         mod_baseMVC,
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

// ============================================================================
/** session storage for library preferences */
var LibraryPrefs = mod_baseMVC.SessionStorageModel.extend({
    defaults : {
        with_deleted : false,
        sort_order   : 'asc',
        sort_by      : 'name'
    }
});

// galaxy library wrapper View
var GalaxyLibrary = Backbone.View.extend({
    toolbarView: null,
    libraryListView: null,
    library_router: null,
    folderContentView: null,
    initialize : function(){
        Galaxy.libraries = this;

        this.preferences = new LibraryPrefs( {id: 'global-lib-prefs'} );

        this.library_router = new LibraryRouter();

        this.library_router.on('route:libraries', function() {
          // initialize and render the toolbar first
          Galaxy.libraries.toolbarView = new mod_librarytoolbar_view.ToolbarView();
          // initialize and render libraries second
          Galaxy.libraries.libraryListView = new mod_librarylist_view.LibraryListView();
        });

        this.library_router.on('route:folder_content', function(id) {
          // render folder contents
          if (!Galaxy.libraries.folderContentView) {Galaxy.libraries.folderContentView = new mod_folderlist_view.FolderContentView();}
          Galaxy.libraries.folderContentView.render({id: id});
        });

       this.library_router.on('route:download', function(folder_id, format) {
          if ($('#center').find(':checked').length === 0) { 
            // this happens rarely when there is a server/data error and client gets an actual response instead of an attachment
            // we don't know what was selected so we can't download again, we redirect to the folder provided
            Galaxy.libraries.library_router.navigate('folders/' + folder_id, {trigger: true, replace: true});
          } else {
            // send download stream
            Galaxy.libraries.folderContentView.download(folder_id, format);
            Galaxy.libraries.library_router.navigate('folders/' + folder_id, {trigger: false, replace: true});
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
