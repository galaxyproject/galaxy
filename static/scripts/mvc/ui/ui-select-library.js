define("mvc/ui/ui-select-library", ["exports", "utils/utils", "mvc/ui/ui-misc", "mvc/ui/ui-table", "mvc/ui/ui-list"], function(exports, _utils, _uiMisc, _uiTable, _uiList) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    var _uiTable2 = _interopRequireDefault(_uiTable);

    var _uiList2 = _interopRequireDefault(_uiList);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    // collection of libraries
    // dependencies
    var Libraries = Backbone.Collection.extend({
        url: Galaxy.root + "api/libraries?deleted=false"
    });

    // collection of dataset
    var LibraryDatasets = Backbone.Collection.extend({
        initialize: function initialize() {
            var self = this;
            this.config = new Backbone.Model({
                library_id: null
            });
            this.config.on("change", function() {
                self.fetch({
                    reset: true
                });
            });
        },
        url: function url() {
            return Galaxy.root + "api/libraries/" + this.config.get("library_id") + "/contents";
        }
    });

    // hda/hdca content selector ui element
    var View = Backbone.View.extend({
        // initialize
        initialize: function initialize(options) {
            // link this
            var self = this;

            // collections
            this.libraries = new Libraries();
            this.datasets = new LibraryDatasets();

            // link app and options
            this.options = options;

            // select field for the library
            // TODO: Remove this once the library API supports searching for library datasets
            this.library_select = new _uiMisc2.default.Select.View({
                onchange: function onchange(value) {
                    self.datasets.config.set("library_id", value);
                }
            });

            // create ui-list view to keep track of selected data libraries
            this.dataset_list = new _uiList2.default.View({
                name: "dataset",
                optional: options.optional,
                multiple: options.multiple,
                onchange: function onchange() {
                    self.trigger("change");
                }
            });

            // add reset handler for fetched libraries
            this.libraries.on("reset", function() {
                var data = [];
                self.libraries.each(function(model) {
                    data.push({
                        value: model.id,
                        label: model.get("name")
                    });
                });
                self.library_select.update(data);
            });

            // add reset handler for fetched library datasets
            this.datasets.on("reset", function() {
                var data = [];
                var library_current = self.library_select.text();
                if (library_current !== null) {
                    self.datasets.each(function(model) {
                        if (model.get("type") === "file") {
                            data.push({
                                value: model.id,
                                label: model.get("name")
                            });
                        }
                    });
                }
                self.dataset_list.update(data);
            });

            // add change event. fires on trigger
            this.on("change", function() {
                options.onchange && options.onchange(self.value());
            });

            // create elements
            this.setElement(this._template());
            this.$(".library-select").append(this.library_select.$el);
            this.$el.append(this.dataset_list.$el);

            // initial fetch of libraries
            this.libraries.fetch({
                reset: true,
                success: function success() {
                    self.library_select.trigger("change");
                    if (self.options.value !== undefined) {
                        self.value(self.options.value);
                    }
                }
            });
        },

        /** Return/Set currently selected library datasets */
        value: function value(val) {
            return this.dataset_list.value(val);
        },

        /** Template */
        _template: function _template() {
            return '<div class="ui-select-library">' + '<div class="library ui-margin-bottom">' + '<span class="library-title">Select Library</span>' + '<span class="library-select"/>' + "</div>" + "</div>";
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/ui/ui-select-library.js.map
