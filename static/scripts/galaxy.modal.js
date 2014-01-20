
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

    // flag whether the closing events are bound
    eventsBound: false,
    
    // options
    options : {
        // by default the modal cannot be removed by the self.destroy() method 
        // but only hidden through self.hide()
        destructible: false,

        // by default don't bind the events
        bindClosingEvents: false,
        // set false to ommit binding ESC key
        bindEscKey: true,
    },
    
    // initialize
    initialize : function(options) {
        self = this;
        if (options){
            this.create(options);
        }
    },

    hideOrDestroy: function(){
        self.visible = false;

        //unbinds event for ALL modals?
        self.unbindEvents();

        if (self.options.destructible){
            self.$el.remove(); // destroy
        } else {
            self.hide();
        }
    },

    // hide modal, shouldn't be called directly but through hideOrDestroy()
    // however hide() remains for backwards compatibility
    hide: function(){
        this.visible = false;
        this.$el.fadeOut('fast');
    },    

    bindEvents: function() {
        if (self.options.bindEscKey){
            // bind the ESC key to hideOrDestroy() function
            $(document).on('keyup', function(event){
                if (event.keyCode == 27) { 
                    self.hideOrDestroy() 
                }
            })
        }
        // bind the 'click anywhere' to hideOrDestroy() function...
        $('html').on('click', self.hideOrDestroy)
        // ...but don't hide if the click is on modal content
        $('.modal-content').on('click', function(event){
            event.stopPropagation();
        })

        self.eventsBound = true;
    },

    unbindEvents: function(){
        // unbind the ESC key to hideOrDestroy() function
        $(document).off('keyup', function(event){
            if (event.keyCode == 27) { 
                self.hideOrDestroy() 
            }
        })
        // unbind the 'click anywhere' to hideOrDestroy() function...
        $('html').off('click', function(event){
            self.hideOrDestroy()
        })
        $('.modal-content').off('click', function(event){
            event.stopPropagation();
        })

        self.eventsBound = false;
    },

    // adds and displays a new frame/window
    show: function(options) {
        // create
        this.initialize(options);
        
        // fix height
        if (this.options.height){
            this.$body.css('height', this.options.height);
            this.$body.css('overflow', 'hidden');
        } else{
            this.$body.css('max-height', $(window).height() / 2);
        }

        // fix width
        if (this.options.width){
            this.$dialog.css('width', this.options.width);
        }
        
        // show
        if (this.visible){
            this.$el.show();
        } else {
            this.$el.fadeIn('fast');
        }
        
        // set flag
        this.visible = true;
    },
    
    // create
    create: function(options) {
        // configure options
        this.options = _.defaults(options, this.optionsDefault);
        
        // check for progress bar request
        if (this.options.body == 'progress'){
            this.options.body = $('<div class="progress progress-striped active"><div class="progress-bar progress-bar-info" style="width:100%"></div></div>');
        }
            
        // remove former element
        if (this.$el){
            this.$el.remove();
        }
        
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
        if (!this.options.backdrop){
            this.$backdrop.removeClass('in');
        }
                        
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

        if (this.options.bindClosingEvents && !this.eventsBound){
            this.bindEvents();
        }
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
