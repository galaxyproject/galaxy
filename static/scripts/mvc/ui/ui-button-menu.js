// dependencies
define(['utils/utils'], function(Utils) {

/**
 *  This class creates a button with dropdown menu. It extends the functionality of the Ui.ButtonIcon class.
 */
return Backbone.View.extend({
    // main options
    optionsDefault: {
        // same as Ui.ButtonIcon
        id              : '',
        title           : '',
        floating        : 'right',
        icon            : null,
        onclick         : null,
        cls             : 'icon-btn',
        tooltip         : '',
        
        // additional options
        target          : '',
        href            : '',
        onunload        : null,
        visible         : true,
        tag             : ''
    },
    
    // optional sub menu
    $menu: null,
    
    // initialize
    initialize: function (options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // add template for tab
        this.setElement($(this._template(this.options)));
        
        // find root
        var $root = $(this.el).find('.root');
        
        // link head
        var self = this;
        $root.on('click', function(e) {
            // hide all tooltips
            $('.tooltip').hide();
        
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
            
        // add tooltip
        $root.tooltip({title: options.tooltip, placement: 'bottom'});
    },
    
    // show
    show: function() {
        $(this.el).show();
    },
        
    // hide
    hide: function() {
        $(this.el).hide();
    },
    
    // add menu item
    addMenu: function (options) {
        // menu option defaults
        var menuOptions = {
            title       : '',
            target      : '',
            href        : '',
            onclick     : null,
            divider     : false,
            icon        : null,
            cls         : 'button-menu btn-group'
        }
    
        // get options
        menuOptions = Utils.merge(options, menuOptions);
        
        // check if submenu element is available
        if (!this.$menu) {
            // insert submenu element into root
            $(this.el).append(this._templateMenu());
            
            // update element link
            this.$menu = $(this.el).find('.menu');
        }
        
        // create
        var $item = $(this._templateMenuItem(menuOptions));
        
        // add events
        $item.on('click', function(e) {
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
    _templateMenuItem: function (options) {
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
    _templateMenu: function () {
        return '<ul class="menu dropdown-menu pull-right" role="menu"></ul>';
    },
    
    _templateDivider: function() {
        return '<li class="divider"></li>';
    },
    
    // element
    _template: function(options) {
        // width
        var width = '';
        if (options.title) {
            width = 'width: auto;';
        }
        
        // string
        var str =   '<div id="' + options.id + '" style="float: ' + options.floating + '; ' + width + '" class="ui-button-icon dropdown ' + options.cls + '">';
    
        // title
        if (options.title) {
            str +=      '<div class="root button dropdown-toggle" data-toggle="dropdown">' +
                            '<i class="icon fa ' + options.icon + '"/>&nbsp;' +
                            '<span class="title">' + options.title + '</span>' +
                        '</div>';
        } else {
            str +=      '<i class="icon fa ' + options.icon + '"/>';
        }
        str +=      '</div>';
        return str;
    }
});

});
