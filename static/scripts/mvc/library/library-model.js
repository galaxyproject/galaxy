// dependencies
define([], function() {

    // LIBRARY
    var Library = Backbone.Model.extend({
      urlRoot: '/api/libraries/'
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

      sort_order: null // default

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
            full_path : "unknown",
            urlRoot : "/api/folders/",
            id : "unknown"
        },
    parse : function(obj) {
      this.full_path = obj[0].full_path;
          // response is not a simple array, it contains metadata
          // this will update the inner collection
          this.get("folder").reset(obj[1].folder_contents);
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
