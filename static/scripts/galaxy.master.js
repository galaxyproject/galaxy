/*
    galaxy master
*/

// dependencies
define(["utils/galaxy.utils", "libs/backbone/backbone-relational"], function(mod_utils) {

// master
var GalaxyMaster = Backbone.View.extend(
{
    // base element
    el_master: '#everything',
    
    // options
    options : null,
    
    // item list
    list : {},
    
    // keeps track of the last element
    itemLast: null,
    
    // counter
    itemCounter: 0,
    
    // background
    $background: null,
    
    // flag indicating visibility of background
    backgroundVisible: false,
    
    // initialize
    initialize : function(options)
    {
        // update options
        this.options = options;
    
        // HACK: due to body events defined in galaxy.panels.js
        $("body").off();
    
        // define this element
        this.setElement($(this._template(options)));
        
        // append to master
        $(this.el_master).append($(this.el));
        
        // assign background
        this.$background = $(this.el).find('#master-background');
        
        // loop through item specific unload functions
        // and collect all there warning messages, regarding
        // the user's attempt to unload the page
        var self = this;
        window.onbeforeunload = function()
        {
            var text = "";
            for (key in self.list)
                if (self.list[key].options.on_unload)
                {
                    var q = self.list[key].options.on_unload();
                    if (q) text += q + " ";
                }
            if (text != "")
                return text;
        };
    },

    // configure events
    events:
    {
        'click'     : '_eventRefresh',
        'mousedown' : function(e) { e.preventDefault() }
    },

    // adds a new item to the master
    append : function(item)
    {
        return this._add(item, true);
    },
    
    // adds a new item to the master
    prepend : function(item)
    {
        return this._add(item, false);
    },
    
    // adds a new item to the master
    _add : function(item, append)
    {
        var $loc = $(this.el).find('#' + item.masterLocation);
        if ($loc)
        {
            // create frame for new item
            var itemId = 'master-item-' + this.itemCounter++;
            var $itemNew = $(item.el);
            
            // configure id and class in order to mark new items
            $itemNew.attr('id', itemId);
            $itemNew.addClass('master-item');
            
            // append to master
            if (append)
                $loc.append($itemNew);
            else
                $loc.prepend($itemNew);
            
            // add to list
            this.list[itemId] = item;
            
            // return item id
            return itemId;
        }
        
        // location not found
        return null;
    },

    // handle click event
    _eventRefresh: function(e)
    {
        // identify current item
        var itemCurrent = $(e.target).closest('.master-item');
        
        // get identifier
        if (itemCurrent.length)
            itemCurrent = itemCurrent.attr('id');
                
        // check last item
        if (this.itemLast && this.itemLast != itemCurrent)
        {
            var it = this.list[this.itemLast];
            if (it)
                if (it.masterReset)
                    it.masterReset();
        }
        
        // check if current item is in active state
        var useBackground = false;
        if (itemCurrent)
        {
            var it = this.list[itemCurrent];
            if (it)
                if (it.masterReset)
                {
                    if (this.itemLast == itemCurrent)
                        useBackground = this.backgroundVisible ? false : true;
                    else
                        useBackground = true;
                }
        }
        
        // decide wether to show/hide  background
        if (useBackground)
            this.$background.show();
        else
            this.$background.hide();
        
        // backup
        this.backgroundVisible = useBackground;
        this.itemLast = itemCurrent;
    },
    
    /*
        HTML TEMPLATES
    */
 
    // template item
    _templateItem: function(id)
    {
        return '<div id="' + id + '" class="master-item"></div>';
    },
    
    // fill template
    _template: function(options)
    {
        return  '<div><div id="masthead" class="navbar navbar-fixed-top navbar-inverse">' +
                    '<div style="position: relative; right: -50%; float: left;">' +
                        '<div id="navbar" style="display: block; position: relative; right: 50%;"></div>' +
                    '</div>' +
                   '<div class="navbar-brand">' +
                        '<a href="' + options.logo_url + '">' +
                            '<img border="0" src="' + galaxy_config.root + 'static/images/galaxyIcon_noText.png">' +
                            '<span id="brand"> Galaxy ' + options.brand + '</span>' +
                        '</a>' +
                    '</div>' +
                    '<div class="quota-meter-container"></div>' +
                    '<div id="iconbar" class="iconbar"></div>' +
                '</div>' +
                '<div id="master-background" style="display: none; position: absolute; top: 33px; width: 100%; height: 100%; z-index: 1010"></div>' +
                '</div>';
    }
});

// icon
var GalaxyMasterIcon = Backbone.View.extend(
{
    // icon options
    options:
    {
        id              : "galaxy-icon",
        icon            : "fa-cog",
        tooltip         : "galaxy-icon",
        with_number     : false,
        on_click        : function() { alert ('clicked') },
        on_unload       : null,
        visible         : true
    },
    
    // location identifier for master class
    masterLocation: 'iconbar',
    
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
        $(this.el).find('.icon').tooltip({title: this.options.tooltip})
                                .on('mouseup', self.options.on_click);
        
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
        var tmpl =  '<div id=' + options.id + ' class="symbol">' +
                        '<div class="icon fa fa-2x ' + options.icon + '"></div>';
        if (options.with_number)
            tmpl+=      '<div class="number"></div>';
        tmpl +=     '</div>';
        
        // return template
        return tmpl;
    }
});

// tab
var GalaxyMasterTab = Backbone.View.extend(
{
    // main options
    options:
    {
        id              : '',
        title           : 'Title',
        target          : '_parent',
        content         : '',
        type            : 'url',
        scratchbook     : false,
        on_unload       : null,
        visible         : true
    },
    
    // location
    masterLocation: 'navbar',
    
    // optional sub menu
    $menu: null,
    
    // flag if menu is visible
    menuVisible: false,
    
    // events
    events:
    {
        'click .head' : '_eventClickHead'
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
    addMenu: function (options)
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
            this.$menu = $(this.el).find('.menu');
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

            // check for menu options
            self._hideMenu();
        
            // no modifications if new tab is requested
            if (self.options.target === '_blank')
                return true;
            
            // load into frame
            Galaxy.frame_manager.frame_new(options);
        });
        
        // append divider
        if (menuOptions.divider)
            this.$menu.append($(this._templateDivider()));
    },
    
    // add reset function called by master
    masterReset: function()
    {
        this._hideMenu();
    },
    
    // hide menu
    _hideMenu: function()
    {
        if (this.$menu && this.menuVisible)
        {
            this.$menu.hide();
            this.menuVisible = false;
        }
    },
    
    // show menu on header click
    _eventClickHead: function(e)
    {
        // prevent default
        e.preventDefault();
        
        // check for menu options
        if (this.$menu)
        {
            // show/hide menu
            if (!this.menuVisible)
            {
                this.$menu.show();
                this.menuVisible = true;
            } else {
                this.$menu.hide();
                this.menuVisible = false;
            }
        } else {
            // open new frame
            Galaxy.frame_manager.frame_new(this.options);
        }
    },
    
    // fill template header
    _templateMenuItem: function (options)
    {
        return '<li><a href="' + options.content + '" target="' + options.target + '">' + options.title + '</a></li>';
    },
    
    // fill template header
    _templateMenu: function ()
    {
        return '<ul class="menu dropdown-menu"></ul>';
    },
    
    _templateDivider: function()
    {
        return '<li class="divider"></li>';
    },
    
    // fill template
    _template: function (options)
    {
        // start template
        var tmpl =  '<ul class="nav navbar-nav" border="0" cellspacing="0">' +
                        '<li class="root dropdown" style="">' +
                            '<a class="head dropdown-toggle" data-toggle="dropdown" target="' + options.target + '" href="' + options.content + '">' +
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
    GalaxyMaster: GalaxyMaster,
    GalaxyMasterTab: GalaxyMasterTab,
    GalaxyMasterIcon: GalaxyMasterIcon
};

});
