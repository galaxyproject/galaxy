define(['libs/underscore', 'viz/trackster/util', 'utils/config'], function(_, util_mod, config_mod) {

/**
 * A configuration setting. Currently key is used as id.
 */
var ExportSetting = Backbone.Model.extend({

    initialize: function() {
        // Use key as id for now.
        var key = this.get('key');
        this.set('id', key);

        // Set defaults based on key.
        var defaults = _.find(ExportSetting.known_settings_defaults, function(s) { return s.key === key; });
        if (defaults) {
            this.set(defaults);
        }
    },

    /**
     * Cast and set value. This should be instead of
     *  setting.set('value', new_value)
     */
    set_value: function(value, options) {
        var type = this.get('type');

        if (type === 'float') {
            value = parseFloat(value);
        }
        else if (type === 'int') {
            value = parseInt(value, 10);
        }
        // TODO: handle casting from string to bool?

        this.set({value: value}, options);
    }
}, {
    // This is a master list of default settings for known settings.
    known_settings_defaults: [
        { key: 'format', label: 'Format', type: 'select', 'default_value': 'pdf', options:
            [{'label': 'PDF', 'value': 'pdf'}, {'label': 'SVG', 'value': 'svg'}, {'label': 'PNG', 'value': 'png'}]},
        { key: 'names', label: 'Track names', type: 'bool', value: true },
        { key: 'yaxis', label: 'Y-axis labels', type: 'bool', value: true },
        { key: 'coordinates', label: 'Coordinate labels', type: 'bool', value: true }
    ]
});

/**
 * Collection of config settings.
 */
var ExportSettingCollection = Backbone.Collection.extend({
    model: ExportSetting,
    initialize: function() {
        var self = this,
            values = ['format', 'names', 'yaxis', 'coordinates'];
        _.each(values, function(k){
            self.add(new ExportSetting({'key':k}));
        });
    },
    /**
     * Save settings as a dictionary of key-value pairs.
     * This function is needed for backwards compatibility.
     */
    to_key_value_dict: function() {
        var rval = {};
        this.each(function(setting) {
            rval[setting.get('key')] = setting.get('value');
        });

        return rval;
    },

    /**
     * Returns value for a given key. Returns undefined if there is no setting with the specified key.
     */
    get_value: function(key) {
        var s = this.get(key);
        if (s) {
            return s.get('value');
        }

        return undefined;
    },

    /**
     * Set value for a setting.
     */
    set_value: function(key, value, options) {
        var s = this.get(key);
        if (s) {
            return s.set_value(value, options);
        }

        return undefined;
     },

     /**
      * Set default value for a setting.
      */
     set_default_value: function(key, default_value) {
        var s = this.get(key);
        if (s) {
            return s.set('default_value', default_value);
        }

        return undefined;
     }
},
{
    /**
     * Utility function that creates a ExportSettingCollection from a set of models
     * and a saved_values dictionary.
     */
    from_models_and_saved_values: function(models, saved_values) {
        // If there are saved values, copy models and update with saved values.
        if (saved_values) {
            models = _.map(models, function(m) {
                return _.extend({}, m, { value: saved_values[m.key] });
            });
        }

        return new ExportSettingCollection(models);
    }
});

/**
 * Viewer for config settings collection.
 */
var ExportSettingCollectionView = Backbone.View.extend({
    className: 'export-settings-view',
    initialize: function() {
        this.collection = new ExportSettingCollection();
    },

    /**
     * Renders form for editing configuration settings.
     */
    render: function() {
        var container = this.$el;

        this.collection.each(function(param, index) {
            // Hidden params have no representation in the form
            if (param.get('hidden')) { return; }

            // Build row for param.
            var id = 'param_' + index,
                type = param.get('type'),
                value = param.get('value');
            var row = $("<div class='form-row' />").appendTo(container);
            row.append($('<label />').attr("for", id ).text(param.get('label') + ":" ));
            // Draw parameter as checkbox
            if ( type === 'bool' ) {
                row.append( $('<input type="checkbox" />').attr("id", id ).attr("name", id ).attr( 'checked', value ) );
            }
            // Draw parameter as select area
            else if ( type === 'select' ) {
                var select = $('<select />').attr("id", id);
                _.each(param.get('options'), function(option) {
                    $("<option/>").text( option.label ).attr( "value", option.value ).appendTo( select );
                });
                select.val( param.get('default_value') );
                row.append( select );

            }
            else {
                row.append( $('<input />').attr("id", id ).attr("name", id ).val( value ) );
            }
            // Help text
            if ( param.help ) {
                row.append( $("<div class='help'/>").text( param.help ) );
            }
        });

        return this;
    },

    /**
     * Render view in modal.
     */
    render_in_modal: function(title, trackster_view) {
        // Set up handlers for cancel, ok button and for handling esc key.
        var self = this,
            cancel_fn = function() { Galaxy.modal.hide(); $(window).unbind("keypress.check_enter_esc"); },
            ok_fn = function() {
                Galaxy.modal.hide();
                $(window).unbind("keypress.check_enter_esc");
                self.update_from_form();
                var options = {};
                _.each(self.collection.models, function(e){
                    options[e.attributes.key] = e.attributes.value;
                })
                trackster_view.export_pdf(options);
            },
            check_enter_esc = function(e) {
                if ((e.keyCode || e.which) === 27) { // Escape key
                    cancel_fn();
                } else if ((e.keyCode || e.which) === 13) { // Enter key
                    ok_fn();
                }
            };

        // Set keypress handler.
        $(window).bind("keypress.check_enter_esc", check_enter_esc);

        // Show modal.
        if (this.$el.children().length === 0) {
            this.render();
        }
        Galaxy.modal.show({
            title: title || "Export",
            body: this.$el,
            buttons: {
                "Cancel": cancel_fn,
                "OK": ok_fn
            }
        });
    },

    /**
     * Update settings with new values entered via form.
     */
    update_from_form: function() {
        var self = this;
        this.collection.each(function(setting, index) {
            if ( !setting.get('hidden') ) {
                // Set value from view.
                var id = 'param_' + index;
                var value = self.$el.find( '#' + id ).val();
                if ( setting.get('type') === 'bool' ) {
                    value = self.$el.find( '#' + id ).is( ':checked' );
                }
                setting.set_value(value);
            }
        });
    }

});

return {
    ExportSetting: ExportSetting,
    ExportSettingCollection: ExportSettingCollection,
    ExportSettingCollectionView: ExportSettingCollectionView
};

});