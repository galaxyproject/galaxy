// dependencies
define(["galaxy.masthead", "mvc/ui/ui-frames"], function(mod_masthead, Frames) {

// frame manager
var GalaxyFrame = Backbone.View.extend(
{
    // base element
    el_main: 'body',
        
    // frame active/disabled
    active: false,
    
    // button active
    button_active: null,
    
    // button load
    button_load  : null,
    
    // initialize
    initialize : function(options)
    {
        // add to masthead menu
        var self = this;
        
        // create frames
        this.frames = new Frames.View({
            visible: false,
        });

        // add activate icon
        this.button_active = new mod_masthead.GalaxyMastheadIcon (
        {
            icon        : 'fa-th',
            tooltip     : 'Enable/Disable Scratchbook',
            onclick     : function() { self._activate(); },
            onunload    : function() {
                if (self.frames.length() > 0) {
                    return "You opened " + self.frames.length() + " frame(s) which will be lost.";
                }
            }
        });
        
        // add to masthead
        Galaxy.masthead.append(this.button_active);

        // add load icon
        this.button_load = new mod_masthead.GalaxyMastheadIcon (
        {
            icon        : 'fa-eye',
            tooltip     : 'Show/Hide Scratchbook',
            onclick     : function(e) {
                if (self.frames.visible) {
                    self.frames.hide();
                } else {
                    self.frames.show();
                }
            },
            with_number : true
        });

        // add to masthead
        Galaxy.masthead.append(this.button_load);
        
        // create
        this.setElement(this.frames.$el);
        
        // append to main
        $(this.el_main).append(this.$el);
        
        // refresh menu
        this.frames.setOnChange(function() {
            self._refresh();
        });
        this._refresh();
    },
    
    // adds and displays a new frame/window
    add: function(options)
    {
        // open new tab
        if (options.target == '_blank')
        {
            window.open(options.content);
            return;
        }
        
        // reload entire window
        if (options.target == '_top' || options.target == '_parent' || options.target == '_self')
        {
            window.location = options.content;
            return;
        }
        
        // validate
        if (!this.active)
        {
            // fix url if main frame is unavailable
            var $galaxy_main = $(window.parent.document).find('#galaxy_main');
            if (options.target == 'galaxy_main' || options.target == 'center')
            {
                if ($galaxy_main.length === 0)
                {
                    var href = options.content;
                    if (href.indexOf('?') == -1)
                        href += '?';
                    else
                        href += '&';
                    href += 'use_panels=True';
                    window.location = href;
                } else {
                    $galaxy_main.attr('src', options.content);
                }
            } else
                window.location = options.content;
                
            // stop
            return;
        }

        // add to frames view
        this.frames.add(options);
    },
    
    // activate/disable panel
    _activate: function ()
    {
        // check
        if (this.active)
        {
            // disable
            this.active = false;

            // toggle
            this.button_active.untoggle();
    
            // hide panel
            this.frames.hide();
        } else {
            // activate
            this.active = true;
        
            // untoggle
            this.button_active.toggle();
        }
    },
    
    // update frame counter
    _refresh: function()
    {
        // update on screen counter
        this.button_load.number(this.frames.length());
        
        // check
        if(this.frames.length() === 0)
            this.button_load.hide();
        else
            this.button_load.show();
            
        // check
        if (this.frames.visible) {
            this.button_load.toggle();
        } else {
            this.button_load.untoggle();
        }
    }
});

// return
return {
    GalaxyFrame: GalaxyFrame
};

});
