define([], function() {

// ============================================================================
// LIBRARY RELATED MODELS

    var Library = Backbone.Model.extend({
      urlRoot: '/api/libraries/',

      /** based on show_deleted would this lib show in the list of lib's?
       *  @param {Boolean} show_deleted are we including deleted libraries?
       */
      isVisible : function(show_deleted){
          var isVisible = true;
          if( (!show_deleted) && (this.get('deleted')) ){
              isVisible = false;
          }
          return isVisible;
      }
    });

    var Libraries = Backbone.Collection.extend({
      url: '/api/libraries',

      model: Library,

      sort_key: 'name', // default

      sort_order: null, // default

      initialize : function(options){
          options = options || {};
      },

      /** Get every 'shown' library in this collection based on deleted filter
       *  @param {Boolean} show_deleted are we including deleted libraries?
       *  @returns array of library models
       */
      getVisible : function(show_deleted, filters){
          filters = filters || [];
          var filteredLibraries = new Libraries( this.filter( function( item ){
              return item.isVisible(show_deleted);
          }));

          return filteredLibraries;
      },

      /** Sort collection by library name (ascending) and return the sorted
       *  collection 
       */
      sortByNameAsc: function(){
        this.comparator = function(libraryA, libraryB){
          if (libraryA.get('name').toLowerCase() > libraryB.get('name').toLowerCase()) {
            return 1; // after
          }
          if (libraryB.get('name').toLowerCase() > libraryA.get('name').toLowerCase()) {
            return -1; // before
          }
          return 0; // equal
        };
        this.sort();
        return this;
      },

      /** Sort collection by library name (descending) and return the sorted
       *  collection 
       */
      sortByNameDesc: function(){
        this.comparator = function(libraryA, libraryB){
          if (libraryA.get('name').toLowerCase() > libraryB.get('name').toLowerCase()) {
            return -1; // before
          }
            if (libraryB.get('name').toLowerCase() > libraryA.get('name').toLowerCase()) {
          return 1; // after
          }
          return 0; // equal
        };
        this.sort();
        return this;
      }

    });

// ============================================================================
// FOLDER RELATED MODELS

    var Item = Backbone.Model.extend({
      urlRoot : '/api/libraries/datasets/'
    });

    var Ldda = Backbone.Model.extend({
      urlRoot : '/api/libraries/datasets/'
    });

    var FolderAsModel = Backbone.Model.extend({
      urlRoot: '/api/folders'
    });

    var Folder = Backbone.Collection.extend({
      model: Item,

      /** Sort collection by item name (ascending) and return the sorted
       *  collection. Folders go before datasets. 
       */
      sortByNameAsc: function(){
        this.comparator = function(itemA, itemB){
          if (itemA.get('type') === itemB.get('type')){
            if (itemA.get('name').toLowerCase() > itemB.get('name').toLowerCase()) {
              return 1; // after
            }
            if (itemB.get('name').toLowerCase() > itemA.get('name').toLowerCase()) {
              return -1; // before
            }
            return 0; // equal
          } else {
            if (itemA.get('type') === 'folder'){
              return -1; // folder is always before dataset
            } else {
              return 1;
            }
          }
        };
        this.sort();
        return this;
      },

      /** Sort collection by item name (descending) and return the sorted
       *  collection. Folders go before datasets. 
       */
      sortByNameDesc: function(){
        this.comparator = function(itemA, itemB){
          if (itemA.get('type') === itemB.get('type')){
            if (itemA.get('name').toLowerCase() > itemB.get('name').toLowerCase()) {
              return -1; // after
            }
            if (itemB.get('name').toLowerCase() > itemA.get('name').toLowerCase()) {
              return 1; // before
            }
            return 0; // equal
          } else {
            if (itemA.get('type') === 'folder'){
              return -1; // folder is always before dataset
            } else {
              return 1;
            }
          }
        };
        this.sort();
        return this;
      }
    });

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


// ============================================================================
// HISTORY RELATED MODELS
// TODO UNITE

    var HistoryItem = Backbone.Model.extend({
      urlRoot : '/api/histories/'
    });

    var HistoryContents = Backbone.Collection.extend({
      urlRoot : '/api/histories/',
      initialize: function(options){
        this.id = options.id;
      },
      url : function(){
        return this.urlRoot + this.id + '/contents';
      },
      model : HistoryItem
    });

    var GalaxyHistory = Backbone.Model.extend({
      urlRoot : '/api/histories/'
    });

    var GalaxyHistories = Backbone.Collection.extend({
      url : '/api/histories',
      model : GalaxyHistory
    });

// ============================================================================
// JSTREE MODEL
    /** Represents folder structure parsable by the jstree component.
     * 
     */
    
    var Jstree = Backbone.Model.extend({
      urlRoot: '/api/ftp_files'
    });

return {
    Library: Library,
    FolderAsModel : FolderAsModel,
    Libraries : Libraries,
    Item : Item,
    Ldda : Ldda,
    Folder : Folder,
    FolderContainer : FolderContainer,
    HistoryItem : HistoryItem,
    HistoryContents : HistoryContents,
    GalaxyHistory : GalaxyHistory,
    GalaxyHistories : GalaxyHistories,
    Jstree: Jstree
};

});
