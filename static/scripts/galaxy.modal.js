/*
    galaxy modal
*/

// dependencies
define(["libs/backbone/backbone-relational"], function() {

// frame manager
var GalaxyModal = Backbone.View.extend(
{
    // base element
    elMain: '#everything',
    
    // defaults inputs
    optionsDefaults: {
        title   : "galaxy-modal",
        body    : "No content available."
    },
    
    // initialize
    initialize : function(options) {
        // create
        if (options)
            this.create(options);
    },

    // adds and displays a new frame/window
    show: function(options) {
        // create
        this.initialize(options);

        // fix height
        var body = (this.$el).find('.modal-body');
        body.css('max-height', $(document).height() / 2);
        
        // show
        if (this.visible)
            this.$el.show();
        else
            this.$el.fadeIn('fast');
        
        // set visibility flag
        this.visible = true;
    },
    
    // hide modal
    hide: function(){
        // fade out
        this.$el.fadeOut('fast');

        // set visibility flag
        this.visible = false;
    },
    
    // create
    create: function(options) {
        // configure options
        options = _.defaults(options, this.optionsDefault);

        // check for progress bar request
        if (options.body == 'progress')
            options.body = '<div class="progress progress-striped active"><div class="progress-bar progress-bar-info" style="width:100%"></div></div>';

        // remove former element
        if (this.$el)
            this.$el.remove();
        
        // create new element
        this.setElement(this.template(options.title));
        
        // link elements
        var body = (this.$el).find('.modal-body');
        var footer  = (this.$el).find('.modal-footer');
        var buttons = (this.$el).find('.buttons');
        
        // append body
        body.append($(options.body));
        
        // fix height if available
        if (options.height)
            body.css('height', options.height);
        
        // append buttons
        if (options.buttons) {
            // link functions
            $.each(options.buttons, function(name, value) {
                 buttons.append($('<button id="' + String(name).toLowerCase() + '"></button>').text(name).click(value)).append(" ");
            });
        } else
            // hide footer
            footer.hide();
        
        // append to main element
        $(this.elMain).append($(this.el));
    },
    
    // enable buttons
    enable: function(name) {
        $(this.el).find('#' + String(name).toLowerCase()).prop('disabled', false);
    },

    // disable buttons
    disable: function(name) {
        $(this.el).find('#' + String(name).toLowerCase()).prop('disabled', true);
    },
    
    // returns scroll top for body element
    scrollTop: function()
    {
        return $(this.el).find('.modal-body').scrollTop();
    },
        
    /*
        HTML TEMPLATES
    */
    
    // fill regular modal template
    template: function(title) {
        return  '<div class="modal in">' +
                    '<div class="modal-backdrop in" style="z-index: -1;"></div>' +
                    '<div class="modal-dialog">' +
                        '<div class="modal-content">' +
                            '<div class="modal-header">' +
                                '<span><h3 class="title">' + title + '</h3></span>' +
                            '</div>' +
                            '<div class="modal-body"></div>' +
                            '<div class="modal-footer">' +
                                '<div class="buttons" style="float: right;"></div>' +
                            '</div>' +
                        '</div' +
                    '</div>' +
                '</div>';
    }
});

// return
return {
    GalaxyModal: GalaxyModal
};

});
