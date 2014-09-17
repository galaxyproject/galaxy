// dependencies
define(['utils/utils'], function(Utils) {

// return
var View = Backbone.View.extend({
    // defaults options
    optionsDefault: {
        title_new       : '',
        operations      : null,
        onnew           : null,
        max             : null,
        onchange        : null
    },
    
    // initialize
    initialize : function(options) {
        // configure
        this.visible    = false;
        this.$nav       = null;
        this.$content   = null;
        this.first_tab  = null;
        this.current_id = null;
            
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create tabs
        var $tabs = $(this._template(this.options));
        
        // link elements
        this.$nav       = $tabs.find('.tab-navigation');
        this.$content   = $tabs.find('.tab-content');
        
        // create new element
        this.setElement($tabs);
        
        // clear list
        this.list = {};
        
        // link this
        var self = this;
            
        // append operations
        if (this.options.operations) {
            $.each(this.options.operations, function(name, item) {
                item.$el.prop('id', name);
                self.$nav.find('.operations').append(item.$el);
            });
        }
        
        // add built-in add-new-tab tab
        if (this.options.onnew) {
            // create tab object
            var $tab_new = $(this._template_tab_new(this.options));
            
            // append to navbar
            this.$nav.append($tab_new);
            
            // add tooltip
            $tab_new.tooltip({title: 'Add a new tab', placement: 'bottom', container: self.$el});
            
            // link click event
            $tab_new.on('click', function(e) {
                $tab_new.tooltip('hide');
                self.options.onnew();
            });
        }
    },
    
    // size
    size: function() {
        return _.size(this.list);
    },
    
    // front
    current: function() {
        return this.$el.find('.tab-pane.active').attr('id');
    },
    
    // append
    add: function(options) {
        // self
        var self = this;
            
        // get tab id
        var id = options.id;

        // create tab object
        var $tab_title      = $(this._template_tab(options));
        var $tab_content    = $(this._template_tab_content(options));
        
        // add to list
        this.list[id] = options.ondel ? true : false;
            
        // add a new tab either before the add-new-tab tab or behind the last tab
        if (this.options.onnew) {
            this.$nav.find('#new-tab').before($tab_title);
        } else {
            this.$nav.append($tab_title);
        }
        
        // add content
        $tab_content.append(options.$el);
        this.$content.append($tab_content);
        
        // activate this tab if this is the first tab
        if (this.size() == 1) {
            $tab_title.addClass('active');
            $tab_content.addClass('active');
            this.first_tab = id;
        }
        
        // hide add tab
        if (this.options.max && this.size() >= this.options.max) {
            this.$el.find('#new-tab').hide();
        }
        
        // add click event to remove tab
        if (options.ondel) {
            var $del_icon = $tab_title.find('#delete');
            $del_icon.tooltip({title: 'Delete this tab', placement: 'bottom', container: self.$el});
            $del_icon.on('click', function() {
                $del_icon.tooltip('destroy');
                self.$el.find('.tooltip').remove();
                options.ondel();
                return false;
            });
        }
        
        // add custom click event handler
        $tab_title.on('click', function(e) {
            // prevent default
            e.preventDefault();
            
            // click
            if (options.onclick) {
                options.onclick();
            } else {
                self.show(id);
            }
        });
        
        // initialize current id
        if (!this.current_id) {
            this.current_id = id;
        }
    },
    
    // delete tab
    del: function(id) {
        // delete tab from dom
        this.$el.find('#tab-' + id).remove();
        this.$el.find('#' + id).remove();
        
        // check if first tab has been deleted
        if (this.first_tab == id) {
            this.first_tab = null;
        }
        
        // show first tab
        if (this.first_tab != null) {
            this.show(this.first_tab);
        }
        
        // delete from list
        if (this.list[id]) {
            delete this.list[id];
        }
        
        // show add tab
        if (this.size() < this.options.max) {
            this.$el.find('#new-tab').show();
        }
    },
    
    // delete tab
    delRemovable: function() {
        for (var id in this.list) {
            this.del(id);
        }
    },
    
    // show
    show: function(id){
        // show tab view
        this.$el.fadeIn('fast');
        this.visible = true;
        
        // show selected tab
        if (id) {
            // reassign active class
            this.$el.find('#tab-' + this.current_id).removeClass('active');
            this.$el.find('#' + this.current_id).removeClass('active');
            this.$el.find('#tab-' + id).addClass('active');
            this.$el.find('#' + id).addClass('active');
            
            // update current id
            this.current_id = id;
        }
        
        // change
        if (this.options.onchange) {
            this.options.onchange(id);
        }
    },
    
    // hide
    hide: function(){
        this.$el.fadeOut('fast');
        this.visible = false;
    },

    // hide operation
    hideOperation: function(id) {
        this.$nav.find('#' + id).hide();
    },

    // show operation
    showOperation: function(id) {
        this.$nav.find('#' + id).show();
    },
    
    // set operation
    setOperation: function(id, callback) {
        var $el = this.$nav.find('#' + id);
        $el.off('click');
        $el.on('click', callback);
    },
    
    // title
    title: function(id, new_title) {
        var $el = this.$el.find('#tab-title-text-' + id);
        if (new_title) {
            $el.html(new_title);
        }
        return $el.html();
    },
    
    // retitle
    retitle: function(new_title) {
        var index = 0;
        for (var id in this.list) {
            this.title(id, ++index + ': ' + new_title);
        }
    },
    
    // fill template
    _template: function(options) {
        return  '<div class="ui-tabs tabbable tabs-left">' +
                    '<ul id="tab-navigation" class="tab-navigation nav nav-tabs">' +
                        '<div class="operations" style="float: right; margin-bottom: 4px;"></div>' +
                    '</ul>'+
                    '<div id="tab-content" class="tab-content"/>' +
                '</div>';
    },
    
    // fill template tab
    _template_tab_new: function(options) {
        return  '<li id="new-tab">' +
                    '<a href="javascript:void(0);">' +
                        '<i class="ui-tabs-add fa fa-plus-circle"/>' +
                            options.title_new +
                    '</a>' +
                '</li>';
    },
    
    // fill template tab
    _template_tab: function(options) {
        var tmpl =  '<li id="tab-' + options.id + '" class="tab-element">' +
                        '<a id="tab-title-link-' + options.id + '" title="" href="#' + options.id + '" data-original-title="">' +
                            '<span id="tab-title-text-' + options.id + '" class="tab-title-text">' + options.title + '</span>';
        
        if (options.ondel) {
            tmpl +=         '<i id="delete" class="ui-tabs-delete fa fa-minus-circle"/>';
        }
        
        tmpl +=         '</a>' +
                    '</li>';
        
        return tmpl;
    },
    
    // fill template tab content
    _template_tab_content: function(options) {
        return  '<div id="' + options.id + '" class="tab-pane"/>';
    }
});

return {
    View : View
}

});
