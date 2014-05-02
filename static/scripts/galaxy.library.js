// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
// === MAIN GALAXY LIBRARY MODULE ====
// MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM

define([
    "galaxy.masthead",
    "utils/utils",
    "libs/toastr",
    "mvc/base-mvc",
    "mvc/library/library-model",
    "mvc/library/library-folderlist-view",
    "mvc/library/library-librarylist-view",
    "mvc/library/library-librarytoolbar-view",
    "mvc/library/library-foldertoolbar-view"
    ],
function(mod_masthead,
         mod_utils,
         mod_toastr,
         mod_baseMVC,
         mod_library_model,
         mod_folderlist_view,
         mod_librarylist_view,
         mod_librarytoolbar_view,
         mod_foldertoolbar_view
         ) {

// ============================================================================
// ROUTER
var LibraryRouter = Backbone.Router.extend({
    routes: {
        ""                                      : "libraries",
        "folders/:id"                           : "folder_content",
        "folders/:folder_id/datasets/:dataset_id"      : "dataset_detail",
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

// ============================================================================
// Main controller of Galaxy Library
var GalaxyLibrary = Backbone.View.extend({

    libraryToolbarView: null,
    libraryListView: null,
    library_router: null,
    folderToolbarView: null,
    folderListView: null,

    initialize : function(){
        Galaxy.libraries = this;

        this.preferences = new LibraryPrefs( {id: 'global-lib-prefs'} );

        this.library_router = new LibraryRouter();

        this.library_router.on('route:libraries', function() {
          // initialize and render the toolbar first
          Galaxy.libraries.libraryToolbarView = new mod_librarytoolbar_view.LibraryToolbarView();
          // initialize and render libraries second
          Galaxy.libraries.libraryListView = new mod_librarylist_view.LibraryListView();
        });

        this.library_router.on('route:folder_content', function(id) {
            // TODO place caching here, sessionstorage/localstorage?
            if (Galaxy.libraries.folderToolbarView){ 
              Galaxy.libraries.folderToolbarView.$el.unbind('click');
            }
            Galaxy.libraries.folderToolbarView = new mod_foldertoolbar_view.FolderToolbarView({id: id});
            Galaxy.libraries.folderListView = new mod_folderlist_view.FolderListView({id: id});
        });

       this.library_router.on('route:download', function(folder_id, format) {
          if ($('#folder_list_body').find(':checked').length === 0) {
            //TODO make URL sharable
            mod_toastr.info('You have to select some datasets to download');
            Galaxy.libraries.library_router.navigate('folders/' + folder_id, {trigger: true, replace: true});
          } else {
            Galaxy.libraries.folderToolbarView.download(folder_id, format);
            Galaxy.libraries.library_router.navigate('folders/' + folder_id, {trigger: false, replace: true});
          }
        });

       this.library_router.on('route:dataset_detail', function(folder_id, dataset_id){
        if (Galaxy.libraries.folderToolbarView){ 
          Galaxy.libraries.folderToolbarView.$el.unbind('click');
        }
        Galaxy.libraries.folderToolbarView = new mod_foldertoolbar_view.FolderToolbarView({id: folder_id});
        Galaxy.libraries.folderListView = new mod_folderlist_view.FolderListView({id: folder_id, dataset_id: dataset_id});
        // Galaxy.libraries.folderListView.rowViews.get(dataset_id).showDatasetDetails();
       });

    Backbone.history.start({pushState: false});
    }
});

return {
    GalaxyApp: GalaxyLibrary
};

});
