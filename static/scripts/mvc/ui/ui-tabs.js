// dependencies
define(['utils/utils'], function(Utils) {

// return
var View = Backbone.View.extend(
{
    // visibility
    visible: false,
    
    // elements
    list: {},
    $nav: null,
    $content: null,
    
    // first
    first_tab: null,
    
    // defaults options
    optionsDefault: {
        title_new       : '',
        operations      : null,
        onnew           : null
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create tabs
        var $tabs = $(this._template(this.options));
        
        // link elements
        this.$nav       = $tabs.find('.tab-navigation');
        this.$content   = $tabs.find('.tab-content');
        
        // create new element
        this.setElement($tabs);
        
        // append operations
        if (this.options.operations) {
            var self = this;
            $.each(this.options.operations, function(name, item) {
                item.$el.prop('id', name);
                self.$nav.append(item.$el);
            });
        }
        
        // add built-in add-new-tab tab
        if (this.options.onnew) {
            // create tab object
            var $tab_new = $(this._template_tab_new(this.options));
            
            // append to navbar
            this.$nav.append($tab_new);
            
            // add tooltip
            $tab_new.tooltip({title: 'Add a new tab', placement: 'bottom'});
            
            // link click event
            $tab_new.on('click', function(e) {
                $tab_new.tooltip('hide');
                self.options.onnew();
            });
        }
    },
    
    // append
    add: function(options) {
        // get tab id
        var id = options.id;
        
        // create tab object
        var tab = {
            $title      : $(this._template_tab(options)),
            $content    : $(this._template_tab_content(options)),
            removable   : options.ondel ? true : false
        }
        
        // add to list
        this.list[id] = tab;
        
        // add a new tab either before the add-new-tab tab or behind the last tab
        if (this.options.onnew) {
            this.$nav.find('#new-tab').before(tab.$title);
        } else {
            this.$nav.append(tab.$title);
        }
        
        // add content
        tab.$content.append(options.$el);
        this.$content.append(tab.$content);
        
        // activate this tab if this is the first tab
        if (_.size(this.list) == 1) {
            tab.$title.addClass('active');
            tab.$content.addClass('active');
            this.first_tab = id;
        }
        
        // add click event to remove tab
        if (options.ondel) {
            var $del_icon = tab.$title.find('#delete');
            $del_icon.tooltip({title: 'Delete this tab', placement: 'bottom'});
            $del_icon.on('click', function(e) {
                $del_icon.tooltip('destroy');
                options.ondel();
                return false;
            });
        }
    },
    
    // delete tab
    del: function(id) {
        // delete tab from list/dom
        var tab = this.list[id];
        tab.$title.remove();
        tab.$content.remove();
        delete tab;
        
        // check if first tab has been deleted
        if (this.first_tab == id) {
            this.first_tab = null;
        }
        
        // show first tab
        if (this.first_tab != null) {
            this.show(this.first_tab);
        }
    },
    
    // delete tab
    delRemovable: function() {
        // delete tab from list/dom
        for (var id in this.list) {
            var tab = this.list[id];
            if (tab.removable) {
                this.del(id);
            }
        }
    },
    
    // show
    show: function(id){
        // show tab view
        this.$el.fadeIn('fast');
        this.visible = true;
        
        // show selected tab
        if (id) {
            this.list[id].$title.find('a').tab('show');
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
        var $el = this.list[id].$title.find('#text');
        if (new_title) {
            $el.html(new_title);
        }
        return $el.html();
    },
    
    // fill template
    _template: function(options) {
        return  '<div class="tabbable tabs-left">' +
                    '<ul class="tab-navigation nav nav-tabs"/>' +
                    '<div class="tab-content"/>' +
                '</div>';
    },
    
    // fill template tab
    _template_tab_new: function(options) {
        return  '<li id="new-tab">' +
                    '<a href="javascript:void(0);">' +
                        '<i style="font-size: 0.8em; margin-right: 5px;" class="fa fa-plus-circle"/>' +
                            options.title_new +
                    '</a>' +
                '</li>';
    },
    
    // fill template tab
    _template_tab: function(options) {
        var tmpl =  '<li id="title-' + options.id + '">' +
                        '<a title="" href="#tab-' + options.id + '" data-toggle="tab" data-original-title="">' +
                            '<span id="text">' + options.title + '</span>';
        
        if (options.ondel) {
            tmpl +=         '<i id="delete" style="font-size: 0.8em; margin-left: 5px; cursor: pointer;" class="fa fa-minus-circle"/>';
        }
        
        tmpl +=         '</a>' +
                    '</li>';
        
        return tmpl;
    },
    
    // fill template tab content
    _template_tab_content: function(options) {
        return  '<div id="tab-' + options.id + '" class="tab-pane"/>';
    }
});

return {
    View : View
}

});
