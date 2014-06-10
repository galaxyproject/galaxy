define(['utils/utils', 'plugin/library/ui'], function(Utils, Ui) {

return Backbone.View.extend(
{
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
        
        // construct chart type subset selection buttons
        this.library = new Ui.RadioButton({
            data    : [ { label: 'Default', value: 'default' },
                        { label: 'Small (<1k lines)', value: 'small' },
                        { label: 'Medium (<10k lines)', value: 'medium' },
                        { label: 'Large (>10k lines)', value: 'large' }],
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
        this.library.value('default');
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
        var types = this.app.types.attributes;
        for (var id in types) {
            var type = types[id];
            var $el = this.$el.find('#' + id);
            var keywords = type.keywords || '';
            if (keywords.indexOf(value) == -1 && value != 'all') {
                $el.hide();
            } else {
                $el.show();
            }
        }
    },
    
    // render
    _render: function() {
        // load chart types into categories
        var categories = {};
        var types = this.app.types.attributes;
        for (var id in types) {
            // add category
            var type = types[id];
            var category = type.category;
            if (!categories[category]) {
                categories[category] = {};
            }
            categories[category][id] = type;
        }
        
        // add categories and charts to screen
        for (var category in categories) {
            // create empty element
            var $el = $('<div style="clear: both;"/>')
            
            // add header label
            $el.append(Utils.wrap(this._template_header({title: category})));
            
            // add chart types
            for (var id in categories[category]) {
                var type = categories[category][id];
                $el.append(Utils.wrap(this._template_item({
                    id      : id,
                    title   : type.title + ' (' + type.library + ')',
                    url     : config.app_root + 'charts/' + this.app.chartPath(id) + '/logo.png'
                })));
            }
            
            // add to view
            this.$el.append(Utils.wrap($el));
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
        return  '<div class="header">' +
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
