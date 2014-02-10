// dependencies
define([], function() {

// masthead
var GalaxyMasthead = Backbone.View.extend(
{
    // base element
    el_masthead: '#everything',
    
    // options
    options : null,
    
    // background
    $background: null,
    
    // list
    list: [],
    
    // initialize
    initialize : function(options)
    {
        // update options
        this.options = options;
    
        // HACK: due to body events defined in galaxy.panels.js
        $("body").off();
    
        // define this element
        this.setElement($(this._template(options)));
        
        // append to masthead
        $(this.el_masthead).append($(this.el));
        
        // assign background
        this.$background = $(this.el).find('#masthead-background');
        
        // loop through unload functions if the user attempts to unload the page
        var self = this;
        $(window).on('beforeunload', function() {
            var text = "";
            for (key in self.list) {
                if (self.list[key].options.onunload) {
                    var q = self.list[key].options.onunload();
                    if (q) text += q + " ";
                }
            }
            if (text != "") {
                return text;
            }
        });
    },

    // configure events
    events:
    {
        'click'     : '_click',
        'mousedown' : function(e) { e.preventDefault() }
    },

    // adds a new item to the masthead
    append : function(item)
    {
        return this._add(item, true);
    },
    
    // adds a new item to the masthead
    prepend : function(item)
    {
        return this._add(item, false);
    },
    
    // activate
    highlight: function(id)
    {
        var current = $(this.el).find('#' + id + '> li');
        if (current) {
            current.addClass('active');
        }
    },
    
    // adds a new item to the masthead
    _add : function(item, append)
    {
        var $loc = $(this.el).find('#' + item.location);
        if ($loc)
        {
            // create frame for new item
            var $current = $(item.el);
            
            // configure class in order to mark new items
            $current.addClass('masthead-item');
            
            // append to masthead
            if (append) {
                $loc.append($current);
            } else {
                $loc.prepend($current);
            }
            
            // add to list
            this.list.push(item);
        }
        
        // location not found
        return null;
    },

    // handle click event
    _click: function(e)
    {
        // close all popups
        var $all = $(this.el).find('.popup');
        if ($all) {
            $all.hide();
        }
        
        // open current item
        var $current = $(e.target).closest('.masthead-item').find('.popup');
        if ($(e.target).hasClass('head')) {
            $current.show();
            this.$background.show();
        } else {
            this.$background.hide();
        }
    },
    
    /*
        HTML TEMPLATES
    */
    
    // fill template
    _template: function(options)
    {
        var brand_text = options.brand ? ("/ " + options.brand) : "" ;
        return  '<div><div id="masthead" class="navbar navbar-fixed-top navbar-inverse">' +
                    '<div style="position: relative; right: -50%; float: left;">' +
                        '<div id="navbar" style="display: block; position: relative; right: 50%;"></div>' +
                    '</div>' +
                   '<div class="navbar-brand">' +
                        '<a href="' + options.logo_url + '">' +
                            '<img border="0" src="' + galaxy_config.root + 'static/images/galaxyIcon_noText.png">' +
                            '<span id="brand"> Galaxy ' + brand_text + '</span>' +
                        '</a>' +
                    '</div>' +
                    '<div class="quota-meter-container"></div>' +
                    '<div id="iconbar" class="iconbar"></div>' +
                '</div>' +
                '<div id="masthead-background" style="display: none; position: absolute; top: 33px; width: 100%; height: 100%; z-index: 1010"></div>' +
                '</div>';
    }
});

// icon
var GalaxyMastheadIcon = Backbone.View.extend(
{
    // icon options
    options:
    {
        id              : '',
        icon            : 'fa-cog',
        tooltip         : '',
        with_number     : false,
        onclick         : function() { alert ('clicked') },
        onunload        : null,
        visible         : true
    },
    
    // location identifier for masthead class
    location: 'iconbar',
    
    // initialize
    initialize: function (options)
    {
        // read in defaults
        if (options)
            this.options = _.defaults(options, this.options);
        
        // add template for icon
        this.setElement($(this._template(this.options)));
        
        // configure icon
        var self = this;
        $(this.el).find('.icon').tooltip({title: this.options.tooltip, placement: 'bottom'})
                                .on('mouseup', self.options.onclick);
        
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
    _template: function (options)
    {
        var tmpl =  '<div id="' + options.id + '" class="symbol">' +
                        '<div class="icon fa fa-2x ' + options.icon + '"></div>';
        if (options.with_number)
            tmpl+=      '<div class="number"></div>';
        tmpl +=     '</div>';
        
        // return template
        return tmpl;
    }
});

// tab
var GalaxyMastheadTab = Backbone.View.extend(
{
    // main options
    options:
    {
        id              : '',
        title           : '',
        target          : '_parent',
        content         : '',
        type            : 'url',
        scratchbook     : false,
        onunload        : null,
        visible         : true,
        disabled        : false,
        title_attribute : ''
    },
    
    // location
    location: 'navbar',
    
    // optional sub menu
    $menu: null,
    
    // events
    events:
    {
        'click .head' : '_head'
    },
    
    // initialize
    initialize: function (options)
    {
        // read in defaults
        if (options)
            this.options = _.defaults(options, this.options);
        
        // update url
        if (this.options.content && this.options.content.indexOf('//') === -1)
            this.options.content = galaxy_config.root + this.options.content;
        
        // add template for tab
        this.setElement($(this._template(this.options)));
        
        // disable menu items that are not available to anonymous user
        // also show title to explain why they are disabled
        if (this.options.disabled){
            $(this.el).find('.root').addClass('disabled');
            this._attachPopover();
        }

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
    
    // add menu item
    add: function (options)
    {
        // menu option defaults
        var menuOptions = {
            title       : 'Title',
            content     : '',
            type        : 'url',
            target      : '_parent',
            scratchbook : false,
            divider     : false
        }
    
        // read in defaults
        if (options)
            menuOptions = _.defaults(options, menuOptions);
        
        // update url
        if (menuOptions.content && menuOptions.content.indexOf('//') === -1)
            menuOptions.content = galaxy_config.root + menuOptions.content;
        
        // check if submenu element is available
        if (!this.$menu)
        {
            // insert submenu element into root
            $(this.el).find('.root').append(this._templateMenu());
            
            // show caret
            $(this.el).find('.symbol').addClass('caret');
            
            // update element link
            this.$menu = $(this.el).find('.popup');
        }
        
        // create
        var $item = $(this._templateMenuItem(menuOptions));
        
        // append menu
        this.$menu.append($item);
        
        // add events
        var self = this;
        $item.on('click', function(e)
        {
            // prevent default
            e.preventDefault();
        
            // no modifications if new tab is requested
            if (self.options.target === '_blank')
                return true;
            
            // load into frame
            Galaxy.frame.add(options);
        });
        
        // append divider
        if (menuOptions.divider)
            this.$menu.append($(this._templateDivider()));
    },
    
    // show menu on header click
    _head: function(e)
    {
        // prevent default
        e.preventDefault();
        
        if (this.options.disabled){
            return // prevent link following if menu item is disabled
        }

        // check for menu options
        if (!this.$menu) {
            Galaxy.frame.add(this.options); 
        }
    },

    _attachPopover : function()
     {
        var $popover_element = $(this.el).find('.head');
        $popover_element.popover({
            html: true,
            content: 'Please <a href="/user/login">log in</a> or <a href="/user/create">register</a> to use this feature.',
            placement: 'bottom'
        }).on('shown.bs.popover', function() { // hooking on bootstrap event to automatically hide popovers after delay
            setTimeout(function() {
                $popover_element.popover('hide');
            }, 5000);
        });
     },

    // fill template header
    _templateMenuItem: function (options)
    {
        return '<li><a href="' + options.content + '" target="' + options.target + '">' + options.title + '</a></li>';
    },
    
    // fill template header
    _templateMenu: function ()
    {
        return '<ul class="popup dropdown-menu"></ul>';
    },
    
    _templateDivider: function()
    {
        return '<li class="divider"></li>';
    },
    
    // fill template
    _template: function (options)
    {
        // start template
        var tmpl =  '<ul id="' + options.id + '" class="nav navbar-nav" border="0" cellspacing="0">' +
                        '<li class="root dropdown" style="">' +
                            '<a class="head dropdown-toggle" data-toggle="dropdown" target="' + options.target + '" href="' + options.content + '" title="' + options.title_attribute + '">' +
                                options.title + '<b class="symbol"></b>' +
                            '</a>' +
                        '</li>' +
                    '</ul>';
        
        // return template
        return tmpl;
    }
});

// return
return {
    GalaxyMasthead: GalaxyMasthead,
    GalaxyMastheadTab: GalaxyMastheadTab,
    GalaxyMastheadIcon: GalaxyMastheadIcon
};

});
