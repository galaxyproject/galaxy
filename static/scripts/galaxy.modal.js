/*
    galaxy modal v1.0
*/

// dependencies
define(["utils/galaxy.css", "libs/backbone/backbone-relational"], function(css) {

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
        // load required css files
        css.load_file("static/style/galaxy.modal.css");
        
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
        var footer = (this.$el).find('.footer');

        // append buttons
        var self = this;
        if (options.buttons)
        {
            // link functions
            $.each(options.buttons, function(name, value)
            {
                 footer.append($('<button></button>').text(name).click(value)).append(" ");
            });
        } else
            // default close button
            footer.append($('<button></button>').text('Close').click(function() { self.hide() })).append(" ");
            
        // hide
        $(this.el).hide();
    },

    /*
        EVENT HANDLING
    */
    
    // event
    events:
    {
        'mousedown .dialog'     : 'event_default',
        'mousedown .background' : 'hide'
    },
    
    // drag
    event_default: function (e)
    {
        e.preventDefault();
    },
    
    // adds and displays a new frame/window
    show: function()
    {
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
    destroy: function ()
    {
        // remove element
        this.$el.remove();
    },
    
    /*
        HTML TEMPLATES
    */
    
    // fill regular modal template
    template: function(title, body)
    {
        return  '<div class="galaxy-modal">' +
                    '<div class="background"></div>' +
                    '<div class="dialog galaxy-corner">' +
                        '<div class="header">' +
                            '<span><h3 class="title">' + title + '</h3></span>' +
                        '</div>' +
                        '<div class="body">' + body + '</div>' +
                        '<div class="footer"></div>' +
                    '</div>' +
                '</div>';
    }
});

// return
return {
    GalaxyModal: GalaxyModal
};

});
