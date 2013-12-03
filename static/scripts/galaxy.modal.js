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
        self = this;
        // create
        if (options)
            this.create(options);
            // bind the ESC key to hide() function
            $(document).on('keyup', function(event){
                if (event.keyCode == 27) { self.hide(); }
            })
            // bind the click anywhere to hide() function...
            $('html').on('click', function(event){
                self.hide();
            })
            // ...but don't hide if the click is on modal content
            $('.modal-content').on('click', function(event){
                event.stopPropagation();
            })
    },

    // destroy
    destroy : function(){
        this.hide();
        $('.modal').html('');
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
        this.$notification = (this.$el).find('.notification-modal');
        
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
    
    // hide buttons
    hideButton: function(name) {
        this.$buttons.find('#' + String(name).toLowerCase()).hide();
    },
    // show buttons
    showButton: function(name) {
        this.$buttons.find('#' + String(name).toLowerCase()).show();
    },

    // show notification
    showNotification : function(message, duration, bgColor, txtColor) {
        // defaults
        var duration = typeof duration !== 'undefined' ? duration : 1500;
        var bgColor = typeof bgColor !== 'undefined' ? bgColor : "#F4E0E1";
        var txtColor = typeof txtColor !== 'undefined' ? txtColor : "#A42732";

        var HTMLmessage = "<div class='notification-message' style='text-align:center; line-height:16px; '> " + message + " </div>";
        this.$notification.html("<div id='notification-bar' style='display:none; float: right; height: 16px; width:100%; background-color: " + bgColor + "; z-index: 100; color: " + txtColor + ";border-bottom: 1px solid " + txtColor + ";'>" + HTMLmessage + "</div>");

        var self = this;
        /*animate the bar*/
        $('#notification-bar').slideDown(function() {
            setTimeout(function() {
                $('#notification-bar').slideUp(function() {self.$notification.html('');});
            }, duration);
        });

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
                        '<div class="modal-content"">' +
                            '<div class="modal-header">' +
                                '<button type="button" class="close" style="display: none;">&times;</button>' +
                                '<h4 class="title">' + title + '</h4>' +
                                '<span class="notification-modal"></span>' + 
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
