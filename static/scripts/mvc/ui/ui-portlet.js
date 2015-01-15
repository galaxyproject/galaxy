// dependencies
define(['utils/utils'], function(Utils) {

// portlet view class
var View = Backbone.View.extend({
    // visibility
    visible: false,
    
    // defaults options
    optionsDefault: {
        title           : '',
        icon            : '',
        buttons         : null,
        body            : null,
        scrollable      : true,
        nopadding       : false,
        operations      : null,
        placement       : 'bottom',
        cls             : 'ui-portlet',
        operations_flt  : 'right'
    },
    
    // elements
    $title : null,
    $content : null,
    $buttons : null,
    $operations : null,
    $header : null,
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement(this._template(this.options));
        
        // link content
        this.$content = this.$el.find('.content');
        
        // link title
        this.$title = this.$el.find('.portlet-title-text');
        
        // link header
        this.$header = this.$el.find('.portlet-header');
        
        // link portlet content (wraps 'content')
        var $portlet_content = this.$el.find('.portlet-content');
        
        // set content padding
        if (this.options.nopadding) {
            $portlet_content.css('padding', '0px');
            this.$content.css('padding', '0px');
        }
        
        // append buttons
        this.$buttons = $(this.el).find('.buttons');
        if (this.options.buttons) {
            // link functions
            var self = this;
            $.each(this.options.buttons, function(name, item) {
                item.$el.prop('id', name);
                self.$buttons.append(item.$el);
            });
        } else {
            this.$buttons.remove();
        }
        
        // append operations
        this.$operations = $(this.el).find('.operations');
        if (this.options.operations) {
            // link functions
            var self = this;
            $.each(this.options.operations, function(name, item) {
                item.$el.prop('id', name);
                self.$operations.append(item.$el);
            });
        }
        
        // add body
        if(this.options.body) {
            this.append(this.options.body);
        }
    },
    
    // append
    append: function($el, unwrapped) {
        if (unwrapped) {
            this.$content.append($el);
        } else {
            this.$content.append(Utils.wrap($el));
        }
    },
        
    // content
    content: function() {
        return this.$content;
    },
    
    // show
    show: function(){
        // fade in
        this.$el.fadeIn('fast');
        
        // set flag
        this.visible = true;
    },
    
    // hide
    hide: function(){
        // fade out
        this.$el.fadeOut('fast');
        
        // set flag
        this.visible = false;
    },

    // enable buttons
    enableButton: function(id) {
        this.$buttons.find('#' + id).prop('disabled', false);
    },

    // disable buttons
    disableButton: function(id) {
        this.$buttons.find('#' + id).prop('disabled', true);
    },
    
    // hide operation
    hideOperation: function(id) {
        this.$operations.find('#' + id).hide();
    },

    // show operation
    showOperation: function(id) {
        this.$operations.find('#' + id).show();
    },
    
    // set operation
    setOperation: function(id, callback) {
        var $el = this.$operations.find('#' + id);
        $el.off('click');
        $el.on('click', callback);
    },
    
    // title
    title: function(new_title) {
        var $el = this.$title;
        if (new_title) {
            $el.html(new_title);
        }
        return $el.html();
    },
    
    // fill regular modal template
    _template: function(options) {
        var tmpl =  '<div id="' + options.id + '" class="' + options.cls + '">';
        
        if (options.title) {
            tmpl +=     '<div class="portlet-header">' +
                            '<div class="operations" style="float: ' + options.operations_flt + ';"></div>' +
                            '<div class="portlet-title">';
                            
            if (options.icon)
                tmpl +=         '<i class="icon fa ' + options.icon + '">&nbsp;</i>';
        
            tmpl +=             '<span class="portlet-title-text">' + options.title + '</span>' +
                            '</div>' +
                        '</div>';
        }
        tmpl +=         '<div class="portlet-content">';
        
        if (options.placement == 'top') {
            tmpl +=         '<div class="buttons"></div>';
        }
        
        tmpl +=             '<div class="content"></div>';
        
        if (options.placement == 'bottom') {
            tmpl +=         '<div class="buttons"></div>';
        }
        
        tmpl +=         '</div>' +
                    '</div>';
        return tmpl;
    }
});

return {
    View : View
}

});
