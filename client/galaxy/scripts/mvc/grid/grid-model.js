// dependencies
define([], function() {

// grid model
return Backbone.Model.extend({
    defaults: {
        url_base: '',
        async: false,
        async_ops: [],
        categorical_filters: [],
        filters: {},
        sort_key: null,
        show_item_checkboxes: false,
        advanced_search: false,
        cur_page: 1,
        num_pages: 1,
        operation: undefined,
        item_ids: undefined
    },

    /**
     * Return true if operation can be done asynchronously.
     */
    can_async_op: function(op) {
        return _.indexOf(this.attributes.async_ops, op) !== -1;
    },

    /**
     * Add filtering criterion.
     */
    add_filter: function(key, value, append) {
        // Update URL arg with new condition.            
        if (append) {
            // Update or append value.
            var cur_val = this.attributes.filters[key],
                new_val;
            if (cur_val === null || cur_val === undefined) {
                new_val = value;
            } 
            else if (typeof(cur_val) == 'string') {
                if (cur_val == 'All') {
                    new_val = value;
                } else {
                    // Replace string with array.
                    var values = [];
                    values[0] = cur_val;
                    values[1] = value;
                    new_val = values;   
                }
            } 
            else {
                // Current value is an array.
                new_val = cur_val;
                new_val.push(value);
            }
            this.attributes.filters[key] = new_val;
        } 
        else {
            // Replace value.
            this.attributes.filters[key] = value;
        }
    },

    /**
     * Remove filtering criterion.
     */
    remove_filter: function(key, condition) {
        var cur_val = this.attributes.filters[key];
        if (cur_val === null || cur_val === undefined) {
            return false;            
        }

        if (typeof(cur_val) === 'string') {
            // overwrite/remove condition.
            this.attributes.filters[key] = '';
        } else {
            // filter contains an array of conditions.
            var condition_index = _.indexOf(cur_val, condition);
            if (condition_index !== -1) {
                cur_val[condition_index] = '';
            }
        }
    },

    /**
     * Returns URL data for obtaining a new grid.
     */
    get_url_data: function() {
        var url_data = {
            async: this.attributes.async,
            sort: this.attributes.sort_key,
            page: this.attributes.cur_page,
            show_item_checkboxes: this.attributes.show_item_checkboxes,
            advanced_search: this.attributes.advanced_search
        };

        // Add operation, item_ids only if they have values.
        if (this.attributes.operation) {
            url_data.operation = this.attributes.operation;
        }
        if (this.attributes.item_ids) {
            url_data.id = this.attributes.item_ids;
        }

        // Add filter arguments to data, placing "f-" in front of all arguments.
        var self = this;
        _.each(_.pairs(self.attributes.filters), function(k) {
            url_data['f-' + k[0]] = k[1];
        });

        return url_data;
    },
    
    // Return URL for obtaining a new grid
    get_url: function (args) {
        return this.get('url_base') + "?" + $.param(this.get_url_data()) + '&' + $.param(args);
    }
    
});

});
