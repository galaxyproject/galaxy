// dependencies
define([], function() {

    // LIBRARY
    var Library = Backbone.Model.extend({
      urlRoot: '/api/libraries/',

      /** based on show_deleted
       *      would this lib show in the list of lib's?
       *  @param {Boolean} show_deleted are we showing deleted libraries?
       */
      isVisible : function(show_deleted){
          var isVisible = true;
          if( (!show_delete) && (this.get('deleted')) ){
              isVisible = false;
          }
          return isVisible;
      }
    });

    // FOLDER AS MODEL
    var FolderAsModel = Backbone.Model.extend({
      urlRoot: '/api/folders'
    });

    // LIBRARIES
    var Libraries = Backbone.Collection.extend({
      url: '/api/libraries',

      model: Library,

      sort_key: 'name', // default

      sort_order: null, // default

      initialize : function(options){
          options = options || {};
      },

      /** Get every 'shown' library in this collection based on deleted filter
       *  @param {Boolean} show_deleted are we showing deleted libraries?
       *  @returns array of library models
       */
      getVisible : function(show_deleted, filters){
          filters = filters || [];
          // always filter by show deleted first
          var filteredLibraries = new Libraries( this.filter( function( item ){
              return item.isVisible(show_deleted);
          }));

          return filteredLibraries;
      }
    });

    // ITEM
    var Item = Backbone.Model.extend({
        urlRoot : '/api/libraries/datasets'
    });

    // FOLDER AS COLLECTION
    var Folder = Backbone.Collection.extend({
      model: Item
    });

    // CONTAINER for folder contents (folders, items and metadata).
    var FolderContainer = Backbone.Model.extend({
        defaults : {
            folder : new Folder(),
            urlRoot : "/api/folders/",
            id : "unknown"
        },
    parse : function(obj) {
      // response is not a simple array, it contains metadata
      // this will update the inner collection
      this.get("folder").reset(obj.folder_contents);
      return obj;
      }
    });

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

// return
return {
    Library: Library,
    FolderAsModel : FolderAsModel,
    Libraries : Libraries,
    Item : Item,
    Folder : Folder,
    FolderContainer : FolderContainer,
    HistoryItem : HistoryItem,
    GalaxyHistory : GalaxyHistory,
    GalaxyHistories : GalaxyHistories
};

});
