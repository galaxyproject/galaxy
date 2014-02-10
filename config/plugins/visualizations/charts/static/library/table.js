// dependencies
define(['library/utils'], function(Utils) {

// return
return Backbone.View.extend(
{
    // current row
    row: null,
    
    // count rows
    row_count: 0,
    
    // defaults options
    optionsDefault: {
        content     : 'No content available.',
        onchange    : null,
        ondblclick  : null,
        onconfirm   : null
    },
    
    // events
    events : {
        'click'     : 'onclick',
        'dblclick'  : 'ondblclick'
    },
    
    // first
    first: true,
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement(this.template(options));
                
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
        $(this.el).find('thead').append(this.row);

        // row
        this.row = $('<tr></tr>');
    },
    
    // add row cell
    add: function($el) {
        var wrapper = $('<td></td>');
        wrapper.append($el);
        this.row.append(wrapper);
    },
    
    // append
    append: function(id) {
        this.commit(id);
    },
    
    // prepend
    prepend: function(id) {
        this.commit(id, true);
    },
    
    // commit
    commit: function(id, prepend) {
        // add
        this.row.attr('id', id);
       
        // add row
        if (prepend) {
            $(this.el).find('tbody').prepend(this.row);
        } else {
            $(this.el).find('tbody').append(this.row);
        }
        
        // row
        this.row = $('<tr></tr>');
        
        // row count
        this.row_count++;
        this.refresh();
    },
    
    // remove
    remove: function(id) {
        $(this.el).find('#' + id).remove();
        this.row_count--;
        this.refresh();
    },

    // remove
    removeAll: function() {
        $(this.el).find('tbody').html('');
        this.row_count = 0;
        this.refresh();
    },
        
    // value
    value: function(new_value) {
        // get current id/value
        this.before = this.$el.find('.current').attr('id');
        
        // check if new_value is defined
        if (new_value !== undefined) {
            this.$el.find('tr').removeClass('current');
            if (new_value) {
                this.$el.find('#' + new_value).addClass('current');
            }
        }
        
        // get current id/value
        var after = this.$el.find('.current').attr('id');
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
    
    // confirm new value
    confirm: function(new_value) {
        this.value(new_value);
    },
    
    // onclick
    onclick: function(e) {
        // get values
        var old_value = this.value();
        var new_value = $(e.target).closest('tr').attr('id');
        
        // check equality
        if (new_value && old_value != new_value) {
            if (this.options.onconfirm) {
                this.options.onconfirm(new_value);
            } else {
                this.confirm(new_value);
            }
        }
    },

    // onclick
    ondblclick: function(e) {
        var value = this.value();
        if (value && this.options.ondblclick) {
            this.options.ondblclick(value);
        }
    },
        
    // refresh
    refresh: function() {
        if (this.row_count == 0) {
            this.$el.find('tmessage').show();
        } else {
            this.$el.find('tmessage').hide();
        }
    },
        
    // load html template
    template: function(options)
    {
        return  '<div>' +
                    '<table class="grid">' +
                        '<thead></thead>' +
                        '<tbody style="cursor: pointer;"></tbody>' +
                    '</table>' +
                    '<tmessage>' + options.content + '</tmessage>' +
                '<div>';
    }
});

});
