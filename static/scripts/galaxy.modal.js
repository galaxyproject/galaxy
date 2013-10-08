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
    optionsDefault: {
        title       : "galaxy-modal",
        body        : "",
        backdrop    : true
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
        this.$body.css('max-height', $(document).height() / 2);
        
        // set max-height so that modal does not exceed window size and is in middle of page.
        /*/ TODO: this could perhaps be handled better using CSS.
        this.$body.css( "max-height",
                    $(window).height() -
                    this.$footer.outerHeight() -
                    this.$header.outerHeight() -
                    parseInt( this.$dialog.css( "padding-top" ), 10 ) -
                    parseInt( this.$dialog.css( "padding-bottom" ), 10 ));*/
        
        // show
        if (this.visible)
            this.$el.show();
        else
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
    
    // create
    create: function(options) {
        // configure options
        options = _.defaults(options, this.optionsDefault);
        
        // check for progress bar request
        if (options.body == 'progress')
            options.body = $('<div class="progress progress-striped active"><div class="progress-bar progress-bar-info" style="width:100%"></div></div>');
            
        // remove former element
        if (this.$el)
            this.$el.remove();
        
        // create new element
        this.setElement(this.template(options.title));
        
        // link elements
        this.$body = (this.$el).find('.modal-body');
        this.$footer  = (this.$el).find('.modal-footer');
        this.$buttons = (this.$el).find('.buttons');
        this.$backdrop = (this.$el).find('.modal-backdrop');
        
        // append body
        this.$body.html(options.body);

        // fix height if available
        if (options.height)
            this.$body.css('height', options.height);
        
        // fix min-width so that modal cannot shrink considerably if new content is loaded.
        this.$body.css('min-width', this.$body.width());

        // configure background
        if (!options.backdrop)
            this.$backdrop.removeClass('in');
                        
        // append buttons
        if (options.buttons) {
            // link functions
            var self = this;
            $.each(options.buttons, function(name, value) {
                 self.$buttons.append($('<button id="' + String(name).toLowerCase() + '"></button>').text(name).click(value)).append(" ");
            });
        } else
            // hide footer
            this.$footer.hide();
        
        // append to main element
        $(this.elMain).append($(this.el));
    },
    
    // enable buttons
    enableButton: function(name) {
        this.$buttons.find('#' + String(name).toLowerCase()).prop('disabled', false);
    },

    // disable buttons
    disableButton: function(name) {
        this.$buttons.find('#' + String(name).toLowerCase()).prop('disabled', true);
    },
    
    // returns scroll top for body element
    scrollTop: function()
    {
        return this.$body.scrollTop();
    },
        
    /*
        HTML TEMPLATES
    */
    
    // fill regular modal template
    template: function(title) {
        return  '<div class="modal">' +
                    '<div class="modal-backdrop fade in" style="z-index: -1;"></div>' +
                    '<div class="modal-dialog">' +
                        '<div class="modal-content">' +
                            '<div class="modal-header">' +
                                '<button type="button" class="close" style="display: none;">&times;</button>' +
                                '<h4 class="title">' + title + '</h4>' +
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
