/*
    galaxy master v1.0
*/

// dependencies
define(["libs/backbone/backbone-relational"], function() {

// master
var GalaxyMaster = Backbone.View.extend(
{
    // base element
    el_master: '#masthead',
    
    // initialize
    initialize : function(options)
    {
        // define this element
        this.setElement($(this.template()));
        
        // append to master
        $(this.el_master).append($(this.el));
    },

    // prevent default
    events:
    {
        'mousedown' : function(e) {e.preventDefault()}
    },

    // adds and displays a new frame/window
    append : function(item)
    {
        $(this.el).append($(item.el));
    },
    
    // adds and displays a new frame/window
    prepend : function(item)
    {
        $(this.el).prepend($(item.el));
    },
    
    /*
        HTML TEMPLATES
    */
    
    // fill regular modal template
    template: function()
    {
        return  '<div class="iconbar"></div>';
    }
});

// frame manager
var GalaxyMasterIcon = Backbone.View.extend(
{
    // icon options
    options:
    {
        id              : "galaxy-icon",
        icon            : "fa-icon-cog",
        tooltip         : "galaxy-icon",
        with_number     : false,
        on_click        : function() { alert ('clicked') },
        visible         : true
    },
    
    // initialize
    initialize: function (options)
    {
        // read in defaults
        if (options)
            this.options = _.defaults(options, this.options);
        
        // add template for icon
        this.setElement($(this.template(this.options)));
        
        // configure icon
        var self = this;
        $(this.el).find('.icon').tooltip({title: this.options.tooltip})
                                .on('click', self.options.on_click);
        
        // visiblity
        if (!this.options.visible)
            this.hide();
    },
    
    // show
    show: function()
    {
        $(this.el).css({visibility : 'visible'});
    },
        
    // show
    hide: function()
    {
        $(this.el).css({visibility : 'hidden'});
    },
    
    // switch icon
    icon: function (new_icon)
    {
        // update icon class
        $(this.el).find('.icon').removeClass(this.options.icon)
                                .addClass(new_icon);
                                
        // update icon
        this.options.icon = new_icon;
    },
    
    // toggle
    toggle: function()
    {
        $(this.el).addClass('toggle');
    },
    
    // untoggle
    untoggle: function()
    {
        $(this.el).removeClass('toggle');
    },
    
    // set/get number
    number: function(new_number)
    {
        $(this.el).find('.number').text(new_number);
    },
    
    // fill template icon
    template: function (options)
    {
        var tmpl =  '<div id=' + options.id + ' class="symbol">' +
                        '<div class="icon fa-icon-2x ' + options.icon + '"></div>';
        if (options.with_number)
            tmpl+=      '<div class="number"></div>';
        tmpl +=     '</div>';
        
        // return template
        return tmpl;
    }
});

// return
return {
    GalaxyMaster: GalaxyMaster,
    GalaxyMasterIcon : GalaxyMasterIcon
};

});
