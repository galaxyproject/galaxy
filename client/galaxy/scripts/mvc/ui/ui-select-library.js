// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-table', 'mvc/ui/ui-list'],
        function(Utils, Ui, Table, List) {

// collection of libraries
var Libraries = Backbone.Collection.extend({
    url: Galaxy.root + 'api/libraries?deleted=false'
});

// collection of dataset
var LibraryDatasets = Backbone.Collection.extend({
    initialize: function() {
        var self = this;
        this.config = new Backbone.Model({ library_id: null });
        this.config.on('change', function() {
            self.fetch({ reset: true });
        });
    },
    url: function() {
        return Galaxy.root + 'api/libraries/' + this.config.get('library_id') + '/contents';
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
        // TODO: Remove this once the library API supports searching for library datasets
        this.library_select = new Ui.Select.View({
            onchange    : function(value) {
                self.datasets.config.set('library_id', value);
            }
        });

        // create ui-list view to keep track of selected data libraries
        this.dataset_list = new List.View({
            name        : 'dataset',
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
                            label   : model.get('name')
                        });
                    }
                });
            }
            self.dataset_list.update(data);
        });

        // add change event. fires on trigger
        this.on('change', function() {
            options.onchange && options.onchange(self.value());
        });

        // create elements
        this.setElement(this._template());
        this.$('.library-select').append(this.library_select.$el);
        this.$el.append(this.dataset_list.$el);

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
    value: function(val) {
        return this.dataset_list.value(val);
    },

    /** Template */
    _template: function() {
        return  '<div class="ui-select-library">' +
                    '<div class="library ui-margin-bottom">' +
                        '<span class="library-title">Select Library</span>' +
                        '<span class="library-select"/>' +
                    '</div>' +
                '</div>';
    }
});

return {
    View: View
}

});
