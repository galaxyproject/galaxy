define("mvc/library/library-model", ["exports", "mvc/library/library-util"], function(exports, _libraryUtil) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _libraryUtil2 = _interopRequireDefault(_libraryUtil);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    // ============================================================================
    // LIBRARY RELATED MODELS

    var Library = Backbone.Model.extend({
        urlRoot: Galaxy.root + "api/libraries/",

        /** based on show_deleted would this lib show in the list of lib's?
         *  @param {Boolean} show_deleted are we including deleted libraries?
         */
        isVisible: function isVisible(show_deleted) {
            var isVisible = true;
            if (!show_deleted && this.get("deleted")) {
                isVisible = false;
            }
            return isVisible;
        }
    });

    var Libraries = Backbone.Collection.extend({
        urlRoot: Galaxy.root + "api/libraries",

        model: Library,

        initialize: function initialize(options) {
            options = options || {};
        },

        search: function search(search_term) {
            /**
             * Search the collection and return only the models that have
             * the search term in their names.
             * [the term to search]
             * @type {string}
             */
            if (search_term == "") return this;
            var lowercase_term = search_term.toLowerCase();
            return this.filter(function(data) {
                var lowercase_name = data.get("name").toLowerCase();
                return lowercase_name.indexOf(lowercase_term) !== -1;
            });
        },

        /** Get every 'shown' library in this collection based on deleted filter
         *  @param {Boolean} show_deleted are we including deleted libraries?
         *  @returns array of library models
         */
        getVisible: function getVisible(show_deleted, filters) {
            filters = filters || [];
            var filteredLibraries = new Libraries(this.filter(function(item) {
                return item.isVisible(show_deleted);
            }));

            return filteredLibraries;
        },

        sortLibraries: function sortLibraries(sort_key, sort_order) {
            this.comparator = _libraryUtil2.default.generateLibraryComparator(sort_key, sort_order);
            this.sort();
        }
    });

    // ============================================================================
    // FOLDER RELATED MODELS

    var LibraryItem = Backbone.Model.extend({});

    var Ldda = LibraryItem.extend({
        urlRoot: Galaxy.root + "api/libraries/datasets/"
    });

    var FolderAsModel = LibraryItem.extend({
        urlRoot: Galaxy.root + "api/folders/"
    });

    var Folder = Backbone.Collection.extend({
        model: LibraryItem,

        sortFolder: function sortFolder(sort_key, sort_order) {
            this.comparator = _libraryUtil2.default.generateFolderComparator(sort_key, sort_order);
            this.sort();
        }
    });

    var FolderContainer = Backbone.Model.extend({
        defaults: {
            folder: new Folder(),
            urlRoot: Galaxy.root + "api/folders/",
            id: "unknown"
        },
        parse: function parse(obj) {
            // empty the collection
            this.get("folder").reset();
            // response is not a simple array, it contains metadata
            // this will update the inner collection
            for (var i = 0; i < obj.folder_contents.length; i++) {
                if (obj.folder_contents[i].type === "folder") {
                    var folder_item = new FolderAsModel(obj.folder_contents[i]);
                    this.get("folder").add(folder_item);
                } else if (obj.folder_contents[i].type === "file") {
                    var file_item = new Ldda(obj.folder_contents[i]);
                    this.get("folder").add(file_item);
                } else {
                    Galaxy.emit.error("Unknown folder item type encountered while parsing response.");
                }
            }
            return obj;
        }
    });

    // ============================================================================
    // HISTORY RELATED MODELS
    // TODO UNITE

    var HistoryItem = Backbone.Model.extend({
        urlRoot: Galaxy.root + "api/histories/"
    });

    var HistoryContents = Backbone.Collection.extend({
        urlRoot: Galaxy.root + "api/histories/",
        initialize: function initialize(options) {
            this.id = options.id;
        },
        url: function url() {
            return this.urlRoot + this.id + "/contents";
        },
        model: HistoryItem
    });

    var GalaxyHistory = Backbone.Model.extend({
        urlRoot: Galaxy.root + "api/histories/"
    });

    var GalaxyHistories = Backbone.Collection.extend({
        url: Galaxy.root + "api/histories",
        model: GalaxyHistory
    });

    // ============================================================================
    // JSTREE MODEL
    /** Represents folder structure parsable by the jstree component.
     *
     */

    var Jstree = Backbone.Model.extend({
        urlRoot: Galaxy.root + "api/remote_files"
    });

    exports.default = {
        Library: Library,
        Libraries: Libraries,
        Item: Ldda,
        Ldda: Ldda,
        FolderAsModel: FolderAsModel,
        Folder: Folder,
        FolderContainer: FolderContainer,
        HistoryItem: HistoryItem,
        HistoryContents: HistoryContents,
        GalaxyHistory: GalaxyHistory,
        GalaxyHistories: GalaxyHistories,
        Jstree: Jstree
    };
});
//# sourceMappingURL=../../../maps/mvc/library/library-model.js.map
