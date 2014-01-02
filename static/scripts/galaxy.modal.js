
// dependencies
define([], function() {

// frame manager
var GalaxyModal = Backbone.View.extend(
{
    // base element
    elMain: '#everything',
    
    // defaults options
    optionsDefault: {
        title       : "galaxy-modal",
        body        : "",
        backdrop    : true,
        height      : null,
        width       : null
    },
    
    // options
    options : {},
    
    // initialize
    initialize : function(options) {
        self = this;
        if (options)
            this.create(options);

        // Bind the hiding events
        // this.bindEvents(event, self);
    },

    // bind the click-to-hide function
    bindEvents: function(event, that) {
        // bind the ESC key to hide() function
        $(document).on('keyup', function(event){
            if (event.keyCode == 27) { self.hide(); }
        })
        // bind the 'click anywhere' to hide() function...
        $('html').on('click', function(event){
            self.hide();
        })
        // ...but don't hide if the click is on modal content
        $('.modal-content').on('click', function(event){
            event.stopPropagation();
        })
    },

    // unbind the click-to-hide function
    unbindEvents: function(event){
        // bind the ESC key to hide() function
        $(document).off('keyup', function(event){
            if (event.keyCode == 27) { self.hide(); }
        })
        // unbind the 'click anywhere' to hide() function...
        $('html').off('click', function(event){
            self.hide();
        })
        $('.modal-content').off('click', function(event){
            event.stopPropagation();
        })
    },

    // destroy
    destroy : function(){
        this.hide();
        this.unbindEvents();
        $('.modal').remove();
    },

    // adds and displays a new frame/window
    show: function(options) {
        // create
        this.initialize(options);
        
        // fix height
        if (this.options.height)
        {
            this.$body.css('height', this.options.height);
            this.$body.css('overflow', 'hidden');
        } else
            this.$body.css('max-height', $(window).height() / 2);

        // fix width
        if (this.options.width)
            this.$dialog.css('width', this.options.width);
        
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
        this.unbindEvents();
    },
    
    // create
    create: function(options) {
        // configure options
        this.options = _.defaults(options, this.optionsDefault);
        
        // check for progress bar request
        if (this.options.body == 'progress')
            this.options.body = $('<div class="progress progress-striped active"><div class="progress-bar progress-bar-info" style="width:100%"></div></div>');
            
        // remove former element
        if (this.$el)
            this.$el.remove();
        
        // create new element
        this.setElement(this.template(this.options.title));
        
        // link elements
        this.$dialog = (this.$el).find('.modal-dialog');
        this.$body = (this.$el).find('.modal-body');
        this.$footer  = (this.$el).find('.modal-footer');
        this.$buttons = (this.$el).find('.buttons');
        this.$backdrop = (this.$el).find('.modal-backdrop');
        
        // append body
        this.$body.html(this.options.body);
        
        // configure background
        if (!this.options.backdrop)
            this.$backdrop.removeClass('in');
                        
        // append buttons
        if (this.options.buttons) {
            // link functions
            var self = this;
            $.each(this.options.buttons, function(name, value) {
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
