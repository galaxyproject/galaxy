// dependencies
define(['utils/utils'], function(Utils) {

/**
 *  This class creates a ui table element.
 */
var View = Backbone.View.extend({
    // current row
    row: null,
    
    // count rows
    row_count: 0,
    
    // defaults options
    optionsDefault: {
        content     : 'No content available.',
        onchange    : null,
        ondblclick  : null,
        onconfirm   : null,
        cls         : ''
    },
    
    // events
    events : {
        'click'     : '_onclick',
        'dblclick'  : '_ondblclick'
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        var $el = $(this._template(options));
        
        // link sub-elements
        this.$thead = $el.find('thead');
        this.$tbody = $el.find('tbody');
        this.$tmessage = $el.find('tmessage');
        
        // set element
        this.setElement($el);
                
        // initialize row
        this.row = $('<tr></tr>');
    },
    
    // add header cell
    addHeader: function($el) {
        var wrapper = $('<th></th>');
        wrapper.append($el);
        this.row.append(wrapper);
    },
    
    // header
    appendHeader: function() {
        // append header row
        this.$thead.append(this.row);

        // row
        this.row = $('<tr></tr>');
    },
    
    // add row cell
    add: function($el, width, align) {
        var wrapper = $('<td></td>');
        if (width) {
            wrapper.css('width', width);
        }
        if (align) {
            wrapper.css('text-align', align);
        }
        wrapper.append($el);
        this.row.append(wrapper);
    },
    
    // append
    append: function(id) {
        this._commit(id);
    },
    
    // prepend
    prepend: function(id) {
        this._commit(id, true);
    },
    
    // get element
    get: function(id) {
        return this.$el.find('#' + id);
    },
    
    // delete
    del: function(id) {
        var item = this.$tbody.find('#' + id);
        if (item.length > 0) {
            item.remove();
            this.row_count--;
            this._refresh();
        }
    },

    // delete all
    delAll: function() {
        this.$tbody.empty();
        this.row_count = 0;
        this._refresh();
    },
        
    // value
    value: function(new_value) {
        // get current id/value
        this.before = this.$tbody.find('.current').attr('id');
        
        // check if new_value is defined
        if (new_value !== undefined) {
            this.$tbody.find('tr').removeClass('current');
            if (new_value) {
                this.$tbody.find('#' + new_value).addClass('current');
            }
        }
        
        // get current id/value
        var after = this.$tbody.find('.current').attr('id');
        if(after === undefined) {
            return null;
        } else {
            // fire onchange
            if (after != this.before && this.options.onchange) {
                this.options.onchange(new_value);
            }
            
            // return current value
            return after;
        }
    },
    
    // size
    size: function() {
        return this.$tbody.find('tr').length;
    },
    
    // commit
    _commit: function(id, prepend) {
        // remove previous item with same id
        this.del(id);
        
        // add
        this.row.attr('id', id);
       
        // add row
        if (prepend) {
            this.$tbody.prepend(this.row);
        } else {
            this.$tbody.append(this.row);
        }
        
        // row
        this.row = $('<tr></tr>');
        
        // row count
        this.row_count++;
        this._refresh();
    },
    
    // onclick
    _onclick: function(e) {
        // get values
        var old_value = this.value();
        var new_value = $(e.target).closest('tr').attr('id');
        if (new_value != ''){
            // check equality
            if (new_value && old_value != new_value) {
                if (this.options.onconfirm) {
                    this.options.onconfirm(new_value);
                } else {
                    this.value(new_value);
                }
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
        
    // refresh
    _refresh: function() {
        if (this.row_count == 0) {
            this.$tmessage.show();
        } else {
            this.$tmessage.hide();
        }
    },
        
    // load html template
    _template: function(options)
    {
        return  '<div>' +
                    '<table class="ui-table ' + options.cls + '">' +
                        '<thead></thead>' +
                        '<tbody style="cursor: pointer;"></tbody>' +
                    '</table>' +
                    '<tmessage>' + options.content + '</tmessage>' +
                '<div>';
    }
});

return {
    View: View
}

});
