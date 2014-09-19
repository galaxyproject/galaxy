// dependencies
define(['utils/utils', 'mvc/ui/ui-misc'], function(Utils, Ui) {

/**
 *  This class renders the chart type selection grid.
 */
return Backbone.View.extend({
    // defaults options
    optionsDefault: {
        onchange    : null,
        ondblclick  : null
    },
    
    // events
    events : {
        'click'     : '_onclick',
        'dblclick'  : '_ondblclick'
    },
    
    // initialize
    initialize : function(app, options) {
        // link this
        var self = this;
        
        // link app
        this.app = app;
        
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        var $el = $('<div class="charts-grid"/>');
        
        // add label
        $el.append(Utils.wrap((new Ui.Label({ title : 'How many data points would you like to analyze?'})).$el));
        
        // construct chart type subset selection buttons
        this.library = new Ui.RadioButton.View({
            data    : [ { label: 'Few (<500)', value: 'small' },
                        { label: 'Some (<10k)', value: 'medium' },
                        { label: 'Many (>10k)', value: 'large' }],
            onchange: function(value) {
                    self._filter(value);
            }
        });
        $el.append(Utils.wrap(this.library.$el));
        
        // set element
        this.setElement($el);
        
        // render
        this._render();
        
        // set
        this.library.value('small');
        this.library.trigger('change');
    },
    
    // value
    value: function(new_value) {
        // get current element
        var before = this.$el.find('.current').attr('id');
        
        // check if new_value is defined
        if (new_value !== undefined) {
            
            // remove current class
            this.$el.find('.current').removeClass('current');
            
            // add current class
            this.$el.find('#' + new_value).addClass('current');
        }
        
        // get current id/value
        var after = this.$el.find('.current').attr('id');
        if(after === undefined) {
            return null;
        } else {
            // fire onchange
            if (after != before && this.options.onchange) {
                this.options.onchange(new_value);
            }
            
            // return current value
            return after;
        }
    },
    
    // filter
    _filter: function(value) {
        // hide all category headers
        this.$el.find('.header').hide();
        
        // show chart types
        var types = this.app.types.attributes;
        for (var id in types) {
            var type = types[id];
            var $el = this.$el.find('#' + id);
            var $header = this.$el.find('#types-header-' + this.categories_index[type.category]);
            var keywords = type.keywords || '';
            if (keywords.indexOf(value) >= 0) {
                $el.show();
                $header.show();
            } else {
                $el.hide();
            }
        }
    },
    
    // render
    _render: function() {
        // load chart types into categories
        this.categories = {};
        this.categories_index = {};
        
        // counter
        var category_index = 0;
        
        // identify categories
        var types = this.app.types.attributes;
        for (var id in types) {
            var type = types[id];
            var category = type.category;
            if (!this.categories[category]) {
                this.categories[category] = {};
                this.categories_index[category] = category_index++;
            }
            this.categories[category][id] = type;
        }
        
        // add categories and charts to screen
        for (var category in this.categories) {
            // create empty element
            var $el = $('<div style="clear: both;"/>')
            
            // add header label
            $el.append(this._template_header({
                id      : 'types-header-' + this.categories_index[category],
                title   : category
            }));
            
            // add chart types
            for (var id in this.categories[category]) {
                // get type
                var type = this.categories[category][id];
                
                // make title
                var title = type.title + ' (' + type.library + ')';
                if (type.zoomable) {
                    title = '<span class="fa fa-search-plus"/>' + title;
                }
            
                // append type to screen
                $el.append(this._template_item({
                    id      : id,
                    title   : title,
                    url     : config.app_root + 'charts/' + this.app.chartPath(id) + '/logo.png'
                }));
            }
            
            // add to view
            this.$el.append($el);
        }
    },
    
    // onclick
    _onclick: function(e) {
        var old_value = this.value();
        var new_value = $(e.target).closest('.item').attr('id');
        if (new_value != '') {
            if (new_value && old_value != new_value) {
                this.value(new_value);
            }
        }
    },

    // ondblclick
    _ondblclick: function(e) {
        var value = this.value();
        if (value && this.options.ondblclick) {
            this.options.ondblclick(value);
        }
    },

    // template
    _template_header: function(options) {
        return  '<div id="' + options.id + '" class="header">' +
                    '&bull; ' + options.title +
                '<div>';
    },
    
    // template
    _template_item: function(options) {
        return  '<div id="' + options.id + '" class="item">' +
                    '<img class="image" src="' + options.url + '">' +
                    '<div class="title">' + options.title + '</div>' +
                '<div>';
    }

});

});
