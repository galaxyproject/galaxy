// dependencies
define(['utils/utils', 'plugin/library/ui-select'], function(Utils, Select) {

// plugin
var Label = Backbone.View.extend(
{
    // options
    optionsDefault: {
        title  : ''
    },
    
    // initialize
    initialize : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
    },
    
    // title
    title: function(new_title) {
        this.$el.find('b').html(new_title);
    },
    
    // template
    _template: function(options) {
        return '<label><b>' + options.title + '</b></label>';
    },
    
    // value
    value: function() {
        return options.title;
    }
});

// plugin
var Button = Backbone.View.extend(
{
    // options
    optionsDefault: {
        id    : null,
        title : '',
        float : 'right',
        cls   : 'btn-default',
        icon  : ''
    },
    
    // initialize
    initialize : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // add event
        $(this.el).on('click', options.onclick);
        
        // add tooltip
        $(this.el).tooltip({title: options.tooltip, placement: 'bottom'});
    },
    
    // element
    _template: function(options) {
        var str =   '<button id="' + options.id + '" type="submit" style="margin-right: 5px; float: ' + options.float + ';" type="button" class="btn ' + options.cls + '">';
        if (options.icon) {
            str +=      '<i class="icon fa ' + options.icon + '"></i>&nbsp;' ;
        }
        str +=          options.title +
                    '</button>';
        return str;
    }
});

// plugin
var Icon = Backbone.View.extend(
{
    // options
    optionsDefault: {
        float       : 'right',
        icon        : '',
        tooltip     : '',
        placement   : 'bottom',
        title       : ''
    },
    
    // initialize
    initialize : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // add tooltip
        $(this.el).tooltip({title: options.tooltip, placement: 'bottom'});
    },
    
    // element
    _template: function(options) {
        return  '<div>' +
                    '<span class="fa ' + options.icon + '" style="font-size: 1.2em;"/>&nbsp;' +
                    options.title +
                '</div>';
    }
});

// plugin
var ButtonIcon = Backbone.View.extend(
{
    // options
    optionsDefault: {
        title   : '',
        id      : null,
        float   : 'right',
        cls     : 'icon-btn',
        icon    : '',
        tooltip : ''
    },
    
    // initialize
    initialize : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // add event
        $(this.el).on('click', options.onclick);
        
        // add tooltip
        $(this.el).tooltip({title: options.tooltip, placement: 'bottom'});
    },
    
    // element
    _template: function(options) {
        // width
        var width = '';
        if (options.title) {
            width = 'width: auto;';
        }
        
        // string
        var str =   '<div id="' + options.id + '" style="margin-right: 5px; float: ' + options.float + '; ' + width + '" class="' + options.cls + '">';
    
        // title
        if (options.title) {
            str +=      '<div style="margin-right: 5px; margin-left: 5px;">' +
                            '<i class="icon fa ' + options.icon + '"/>&nbsp;' +
                            '<span style="position: relative; font-size: 0.8em; font-weight: normal; top: -1px;">' + options.title + '</span>' +
                        '</div>';
        } else {
            str +=      '<i class="icon fa ' + options.icon + '"/>';
        }
        str +=      '</div>';
        return str;
    }
});

// plugin
var Anchor = Backbone.View.extend(
{
    // options
    optionsDefault: {
        title  : ''
    },
    
    // initialize
    initialize : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // add event
        $(this.el).on('click', options.onclick);
    },
    
    // element
    _template: function(options) {
        return '<div><a href="javascript:void(0)">' + options.title + '</a></div>';
    }
});

// plugin
var Message = Backbone.View.extend(
{
    // options
    optionsDefault: {
        message : '',
        status : 'info',
        persistent : false
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement('<div></div>');
    },
    
    // update
    update : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // show message
        if (options.message != '') {
            this.$el.html(this._template(this.options));
            this.$el.fadeIn();
            
            // check if message is persistent
            if (!options.persistent) {
                // set timer
                var self = this;
                window.setTimeout(function() {
                    if (self.$el.is(':visible')) {
                        self.$el.fadeOut();
                    } else {
                        self.$el.hide();
                    }
                }, 3000);
            }
        } else {
            this.$el.fadeOut();
        }
    },
    
    // element
    _template: function(options) {
        return '<div class="alert alert-' + options.status + '" style="padding: 2px 2px 2px 10px;">' + options.message + '</div>';
    }
});

// plugin
var Searchbox = Backbone.View.extend(
{
    // options
    optionsDefault: {
        onclick : null,
        searchword : ''
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement(this._template(this.options));
        
        // add click event
        var self = this;
        if (this.options.onclick) {
            this.$el.on('submit', function(e) {
                var search_field = self.$el.find('#search');
                self.options.onclick(search_field.val());
            });
        }
    },
    
    // element
    _template: function(options) {
        return  '<div class="search">' +
                    '<form onsubmit="return false;">' +
                        '<input id="search" class="form-control input-sm" type="text" name="search" placeholder="Search..." value="' + options.searchword + '">' +
                        '<button type="submit" class="btn search-btn">' +
                            '<i class="fa fa-search"></i>' +
                        '</button>' +
                    '</form>' +
                '</div>';
    }
});

// plugin
var Title = Backbone.View.extend(
{
    // options
    optionsDefault: {
        title   : 'Unlabeled',
        body    : null
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement(this._template(this.options));
        
        if (this.options.body) {
            this.$el.find('.body').append(this.options.body);
        }
    },
    
    // element
    _template: function(options) {
        return  '<div id="title" class="title">' +
                    options.title + ':' +
                '</div>';
    }
});

// tab
var ButtonMenu = Backbone.View.extend(
{
    // main options
    optionsDefault:
    {
        id              : '',
        title           : '',
        target          : '',
        href            : '',
        onunload        : null,
        onclick         : null,
        visible         : true,
        icon            : null,
        tag             : ''
    },
    
    // optional sub menu
    $menu: null,
    
    // initialize
    initialize: function (options)
    {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // add template for tab
        this.setElement($(this._template(this.options)));
        
        // find root
        var $root = $(this.el).find('.root');
        
        // link head
        var self = this;
        $root.on('click', function(e)
        {
            // prevent default
            e.preventDefault();
            
            // add click event
            if(self.options.onclick) {
                self.options.onclick();
            }
        });
        
        // visiblity
        if (!this.options.visible)
            this.hide();
    },
    
    // show
    show: function()
    {
        $(this.el).show();
    },
        
    // hide
    hide: function()
    {
        $(this.el).hide();
    },
    
    // add menu item
    addMenu: function (options)
    {
        // menu option defaults
        var menuOptions = {
            title       : '',
            target      : '',
            href        : '',
            onclick     : null,
            divider     : false,
            icon        : null
        }
    
        // get options
        menuOptions = Utils.merge(options, menuOptions);
        
        // check if submenu element is available
        if (!this.$menu)
        {
            // insert submenu element into root
            $(this.el).append(this._templateMenu());
            
            // update element link
            this.$menu = $(this.el).find('.menu');
        }
        
        // create
        var $item = $(this._templateMenuItem(menuOptions));
        
        // add events
        $item.on('click', function(e)
        {
            // prevent default
            e.preventDefault();
            
            // add click event
            if(menuOptions.onclick) {
                menuOptions.onclick();
            }
        });
        
        // append menu
        this.$menu.append($item);
        
        // append divider
        if (menuOptions.divider)
            this.$menu.append($(this._templateDivider()));
    },
    
    // fill template header
    _templateMenuItem: function (options)
    {
        var tmpl =  '<li>' +
                        '<a href="' + options.href + '" target="' + options.target + '">';
                
        if (options.icon)
            tmpl +=         '<i class="fa ' + options.icon + '"></i>';
        
        tmpl +=             ' ' + options.title +
                        '</a>' +
                    '</li>';
        return tmpl;
    },
    
    // fill template header
    _templateMenu: function ()
    {
        return '<ul class="menu dropdown-menu pull-right" role="menu"></ul>';
    },
    
    _templateDivider: function()
    {
        return '<li class="divider"></li>';
    },
    
    // fill template
    _template: function (options)
    {
        // start template
        var tmpl =  '<div id="' + options.id + '" class="button-menu btn-group">' +
                        '<button type="button" class="root btn btn-default dropdown-toggle" data-toggle="dropdown">';
        
        if (options.icon)
            tmpl +=         '<i class="fa ' + options.icon + '"></i>';
         
                        '</button>' +
                    '</div>';
        
        // return template
        return tmpl;
    }
});

// plugin
var Input = Backbone.View.extend(
{
    // options
    optionsDefault: {
        value           : '',
        type            : 'text',
        placeholder     : '',
        disabled        : false,
        visible         : true
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // disable input field
        if (this.options.disabled) {
            this.$el.prop('disabled', true);
        }
        
        // hide input field
        if (!this.options.visible) {
            this.$el.hide();
        }
        
        // onchange event handler
        var self = this;
        if (this.options.onchange) {
            this.$el.on('input', function() {
                self.options.onchange();
            });
        }
    },
    
    // value
    value : function (new_val) {
        if (new_val !== undefined) {
            this.$el.val(new_val);
        }
        return this.$el.val();
    },
    
    // element
    _template: function(options) {
        return '<input id="' + options.id + '" type="' + options.type + '" value="' + options.value + '" placeholder="' + options.placeholder + '" class="form-control">';
    }
});

// return
return {
    Label   : Label,
    Button  : Button,
    Icon  : Icon,
    ButtonIcon : ButtonIcon,
    Input : Input,
    Anchor  : Anchor,
    Message : Message,
    Searchbox : Searchbox,
    Title : Title,
    Select : Select,
    ButtonMenu : ButtonMenu
}
});
