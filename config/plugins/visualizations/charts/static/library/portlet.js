// dependencies
define(['library/utils'], function(Utils) {

// return
return Backbone.View.extend(
{
    // visibility
    visible: false,
    
    // defaults options
    optionsDefault: {
        label       : '',
        icon        : 'fa-tasks',
        buttons     : null,
        body        : null,
        height      : null,
        operations  : null,
        placement   : 'bottom',
        overflow    : 'auto'
    },
    
    // content
    $content : null,
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement(this.template(this.options));
        
        // link content
        this.$content = this.$el.find('#content');
        
        // set content height
        if (this.options.height) {
            this.$el.find('#body').css('height', this.options.height);
            this.$el.find('#content').css('overflow', this.options.overflow);
        }
        
        // append buttons
        this.$buttons = $(this.el).find('#buttons');
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
        this.$operations = $(this.el).find('#operations');
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
    append: function($el) {
        this.$content.append(Utils.wrap($el));
    },
    
    // content
    content: function() {
        return this.$content;
    },
    
    // hide modal
    show: function(){
        // fade in
        this.$el.fadeIn('fast');
        
        // set flag
        this.visible = true;
    },
    
    // hide modal
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
    
    // enable operation
    hideOperation: function(id) {
        this.$operations.find('#' + id).hide();
    },

    // disable operation
    showOperation: function(id) {
        this.$operations.find('#' + id).show();
    },
    
    // set operation
    setOperation: function(id, callback) {
        var $el = this.$operations.find('#' + id);
        $el.off('click');
        $el.on('click', callback);
    },
    
    // label
    label: function(new_label) {
        var $el = this.$el.find('#label');
        if (new_label) {
            $el.html(new_label);
        }
        return $el.html();
    },
    
    // fill regular modal template
    template: function(options) {
        var tmpl =  '<div class="toolForm">';
        
        if (options.label || options.icon) {
            tmpl +=     '<div id="title" class="toolFormTitle" style="overflow:hidden;">' +
                            '<div id="operations" style="float: right;"></div>' +
                            '<div style="overflow: hidden">';
                            
            if (options.icon)
                tmpl +=         '<i style="padding-top: 3px; float: left; font-size: 1.2em" class="icon fa ' + options.icon + '">&nbsp;</i>';
        
            tmpl +=             '<div id="label" style="padding-top: 2px; float: left;">' + options.label + '</div>';
            
            tmpl +=         '</div>' +
                        '</div>';
        }
        tmpl +=         '<div id="body" class="toolFormBody">';
        
        if (options.placement == 'top') {
            tmpl +=         '<div id="buttons" class="buttons" style="height: 50px; padding: 10px;"></div>';
        }
        
        tmpl +=             '<div id="content" class="content" style="height: inherit; padding: 10px;"></div>';
        
        if (options.placement == 'bottom') {
            tmpl +=         '<div id="buttons" class="buttons" style="height: 50px; padding: 10px;"></div>';
        }
        
        tmpl +=         '</div>' +
                    '</div>';
        return tmpl;
    }
});

});
