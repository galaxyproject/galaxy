/*
    galaxy modal v1.0
*/

// dependencies
define(["libs/backbone/backbone-relational"], function() {

// frame manager
var GalaxyModal = Backbone.View.extend(
{
    // base element
    el_main: '#everything',
    
    // defaults inputs
    options:
    {
        title   : "galaxy-modal",
        body    : "No content available."
    },
    
    // initialize
    initialize : function(options)
    {        
        // create
        if (options)
        {
            this.create(options);
            
            // hide
            $(this.el).hide();
        }
    },

    // adds and displays a new frame/window
    show: function(options)
    {
        // create
        if (options)
            this.create(options);
    
        // fade out
        this.$el.fadeIn('fast');
    },
    
    // hide modal
    hide: function()
    {
        // fade out
        this.$el.fadeOut('fast');
    },
    
    // destroy modal
    create: function (options)
    {
        // remove element
        this.$el.remove();
        
        // read in defaults
        if (!options)
            options = this.options;
        else
            options = _.defaults(options, this.options);

        // create element
        this.setElement(this.template(options.title, options.body));

        // append template
        $(this.el_main).append($(this.el));
        
        // link elements
        var footer = (this.$el).find('.buttons');

        // append buttons
        var self = this;
        if (options.buttons)
        {
            // link functions
            $.each(options.buttons, function(name, value)
            {
                 footer.append($('<button id="' + String(name).toLowerCase() + '"></button>').text(name).click(value)).append(" ");
            });
        } else
            // default close button
            footer.append($('<button></button>').text('Close').click(function() { self.hide() })).append(" ");
    },
    
    // enable buttons
    enable: function(name)
    {
        $(this.el).find('#' + String(name).toLowerCase()).prop('disabled', false);
    },

    // disable buttons
    disable: function(name)
    {
        $(this.el).find('#' + String(name).toLowerCase()).prop('disabled', true);
    },
        
    /*
        HTML TEMPLATES
    */
    
    // fill regular modal template
    template: function(title, body)
    {
        return  '<div class="modal in">' +
                    '<div class="modal-backdrop in" style="z-index: -1;"></div>' +
                    '<div class="modal-dialog">' +
                        '<div class="modal-content">' +
                            '<div class="modal-header">' +
                                '<span><h3 class="title">' + title + '</h3></span>' +
                            '</div>' +
                            '<div class="modal-body style="min-width: 540px; max-height: 445px;">' + body + '</div>' +
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
