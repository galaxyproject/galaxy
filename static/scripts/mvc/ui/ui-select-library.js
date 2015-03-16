// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-tabs', 'mvc/tools/tools-template'],
        function(Utils, Ui, Tabs, ToolTemplate) {

// collection of libraries
var Libraries = Backbone.Collection.extend({
    url: galaxy_config.root + 'api/libraries'
});

// collection of dataset
var LibraryDatasets = Backbone.Collection.extend({
    initialize: function() {
        var self = this;
        this.config = new Backbone.Model({ library_id: null });
        this.config.on('change', function() {
            self.fetch({reset: true});
        });
    },
    url: function() {
        return galaxy_config.root + 'api/libraries/' + this.config.get('library_id') + '/contents'
    }
});

// hda/hdca content selector ui element
var View = Backbone.View.extend({
    // initialize
    initialize : function(options) {
        // link this
        var self = this;

        // collections
        this.libraries  = new Libraries();
        this.datasets   = new LibraryDatasets();

        // link app and options
        this.options = options;

        // select field for the library
        this.library_select = new Ui.Select.View({
            optional    : options.optional,
            onchange    : function(value) {
                self.datasets.config.set('library_id', value);
            }
        });

        // select field for the library dataset
        this.dataset_select = new Ui.Select.View({
            optional    : options.optional,
            multiple    : options.multiple,
            onchange    : function() {
                self.trigger('change');
            }
        });

        // add reset handler for fetched libraries
        this.libraries.on('reset', function() {
            var data = [];
            self.libraries.each(function(model) {
                data.push({
                    value   : model.id,
                    label   : model.get('name')
                });
            });
            self.library_select.update(data);
            self.trigger('change');
        });

        // add reset handler for fetched library datasets
        this.datasets.on('reset', function() {
            var data = [];
            var library_current = self.library_select.text();
            if (library_current !== null) {
                self.datasets.each(function(model) {
                    if (model.get('type') === 'file') {
                        data.push({
                            value   : model.id,
                            label   : library_current + model.get('name')
                        });
                    }
                });
            }
            self.dataset_select.update(data);
            self.trigger('change');
        });

        // add change event. fires on trigger
        this.on('change', function() {
            options.onchange && options.onchange(self.value());
        });

        // create element
        this.setElement(this._template());
        this.$('.library-select').append(this.library_select.$el);
        this.$('.dataset-select').append(this.dataset_select.$el);

        // initial fetch of libraries
        this.libraries.fetch({
            reset: true,
            success: function() {
                self.library_select.trigger('change');
                if (self.options.value !== undefined) {
                    self.value(self.options.value);
                }
            }
        });
    },

    /** Return/Set currently selected library datasets */
    value: function(new_val) {
        return this.dataset_select.value();
    },

    /** Template */
    _template: function() {
        return  '<div class="ui-select-library">' +
                    '<div class="library ui-margin-bottom">' +
                        '<span class="library-title">Select Library</span>' +
                        '<span class="library-select"/>' +
                    '</div>' +
                    '<div class="dataset">' +
                        '<span class="dataset-title">Select Dataset</span>' +
                        '<span class="dataset-select"/>' +
                    '</div>' +
                '</div>';
    }
});

return {
    View: View
}

});
