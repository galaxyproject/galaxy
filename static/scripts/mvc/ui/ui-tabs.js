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
    
    // defaults options
    optionsDefault: {
        operations: null,
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create element
        var $tabs = $(this._template(this.options));
        this.$nav = $tabs.find('.tab-navigation');
        this.$content = $tabs.find('.tab-content');
        
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
    },
    
    // append
    add: function(options) {
        // collect parameters
        var $el = options.$el;
        var title = options.title;
        var id = options.id;
        
        // create tab object
        var tab = {
            $title : $(this._template_tab(options)),
            $content : $(this._template_tab_content(options))
        }
        
        // add nav element
        this.$nav.append(tab.$title);
        
        // add content
        tab.$content.append($el);
        this.$content.append(tab.$content);
        
        // add to list
        this.list[id] = tab;
        
        // check list size
        if (_.size(this.list) == 1) {
            tab.$title.addClass('active');
            tab.$content.addClass('active');
        }
    },
    
    // show
    show: function(){
        this.$el.fadeIn('fast');
        this.visible = true;
    },
    
    // hide
    hide: function(){
        this.$el.fadeOut('fast');
        this.visible = false;
    },

    // enable operation
    hideOperation: function(id) {
        this.$nav.find('#' + id).hide();
    },

    // disable operation
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
    title: function(id, new_label) {
        var $el = this.$el.find('#title-' + id + ' a');
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
    _template_tab: function(options) {
        return  '<li id="title-' + options.id + '">' +
                    '<a title="" href="#tab-' + options.id + '" data-toggle="tab" data-original-title="">' + options.title + '</a>' +
                '</li>';
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
