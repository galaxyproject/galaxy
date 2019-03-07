// dependencies
import Backbone from "backbone";
import Ui from "mvc/ui/ui-misc";
import List from "mvc/ui/ui-list";
import { getAppRoot } from "onload/loadConfig";

// collection of libraries
var Libraries = Backbone.Collection.extend({
    url: `${getAppRoot()}api/libraries?deleted=false`
});

// collection of dataset
var LibraryDatasets = Backbone.Collection.extend({
    initialize: function() {
        var self = this;
        this.config = new Backbone.Model({ library_id: null });
        this.config.on("change", () => {
            self.fetch({ reset: true });
        });
    },
    url: function() {
        return `${getAppRoot()}api/libraries/${this.config.get("library_id")}/contents`;
    }
});

// hda/hdca content selector ui element
var View = Backbone.View.extend({
    // initialize
    initialize: function(options) {
        // link this
        var self = this;

        // collections
        this.libraries = new Libraries();
        this.datasets = new LibraryDatasets();

        // link app and options
        this.options = options;

        // select field for the library
        // TODO: Remove this once the library API supports searching for library datasets
        this.library_select = new Ui.Select.View({
            onchange: function(value) {
                self.datasets.config.set("library_id", value);
            }
        });

        // create ui-list view to keep track of selected data libraries
        this.dataset_list = new List.View({
            name: "dataset",
            optional: options.optional,
            multiple: options.multiple,
            onchange: function() {
                self.trigger("change");
            }
        });

        // add reset handler for fetched libraries
        this.libraries.on("reset", () => {
            var data = [];
            self.libraries.each(model => {
                data.push({
                    value: model.id,
                    label: model.get("name")
                });
            });
            self.library_select.update({ data: data });
        });

        // add reset handler for fetched library datasets
        this.datasets.on("reset", () => {
            var data = [];
            var library_current = self.library_select.text();
            if (library_current !== null) {
                self.datasets.each(model => {
                    if (model.get("type") === "file") {
                        data.push({
                            value: model.id,
                            label: model.get("name")
                        });
                    }
                });
            }
            self.dataset_list.update({ data: data });
        });

        // add change event. fires on trigger
        this.on("change", () => {
            if (options.onchange) {
                options.onchange(self.value());
            }
        });

        // create elements
        this.setElement(this._template());
        this.$(".library-select").append(this.library_select.$el);
        this.$el.append(this.dataset_list.$el);

        // initial fetch of libraries
        this.libraries.fetch({
            reset: true,
            success: function() {
                self.library_select.trigger("change");
                if (self.options.value !== undefined) {
                    self.value(self.options.value);
                }
            }
        });
    },

    /** Return/Set currently selected library datasets */
    value: function(val) {
        return this.dataset_list.value(val);
    },

    /** Template */
    _template: function() {
        return `<div class="ui-select-library">
                    <div class="library-select mb-2"/>
                </div>`;
    }
});

export default {
    View: View
};
