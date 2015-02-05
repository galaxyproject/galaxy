// dependencies
define(['utils/utils', 'mvc/ui/ui-select-default', 'mvc/ui/ui-slider', 'mvc/ui/ui-options', 'mvc/ui/ui-drilldown', 'mvc/ui/ui-button-menu', 'mvc/ui/ui-modal'],
        function(Utils, Select, Slider, Options, Drilldown, ButtonMenu, Modal) {

/**
 *  This class contains backbone wrappers for basic ui elements such as Images, Labels, Buttons, Input fields etc.
 */
 
// plugin
var Image = Backbone.View.extend({
    // options
    optionsDefault: {
        url  : '',
        cls  : ''
    },
    
    // initialize
    initialize : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
    },
    
    // template
    _template: function(options) {
        return '<img class="ui-image ' + options.cls + '" src="' + options.url + '"/>';
    }
});

// plugin
var Label = Backbone.View.extend({
    // options
    optionsDefault: {
        title  : '',
        cls    : ''
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
        this.$el.html(new_title);
    },
    
    // template
    _template: function(options) {
        return '<label class="ui-label ' + options.cls + '">' + options.title + '</label>';
    },
    
    // value
    value: function() {
        return options.title;
    }
});

// plugin
var Icon = Backbone.View.extend({
    // options
    optionsDefault: {
        floating    : 'right',
        icon        : '',
        tooltip     : '',
        placement   : 'bottom',
        title       : '',
        cls         : ''
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
                    '<span class="fa ' + options.icon + '" class="ui-icon"/>&nbsp;' +
                    options.title +
                '</div>';
    }
});

// plugin
var Button = Backbone.View.extend({
    // options
    optionsDefault: {
        id          : null,
        title       : '',
        floating    : 'right',
        cls         : 'ui-button btn btn-default',
        icon        : ''
    },
    
    // initialize
    initialize : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // add event
        $(this.el).on('click', function() {
            // hide all tooltips
            $('.tooltip').hide();
            
            // execute onclick callback
            if (options.onclick) {
                options.onclick();
            }
        });
        
        // add tooltip
        $(this.el).tooltip({title: options.tooltip, placement: 'bottom'});
    },
    
    // element
    _template: function(options) {
        var str =   '<button id="' + options.id + '" type="submit" style="float: ' + options.floating + ';" type="button" class="' + options.cls + '">';
        if (options.icon) {
            str +=      '<i class="icon fa ' + options.icon + '"></i>&nbsp;' ;
        }
        str +=          options.title +
                    '</button>';
        return str;
    }
});

// plugin
var ButtonIcon = Backbone.View.extend({
    // options
    optionsDefault: {
        id          : null,
        title       : '',
        floating    : 'right',
        cls         : 'ui-button-icon',
        icon        : '',
        tooltip     : '',
        onclick     : null
    },
    
    // initialize
    initialize : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // link button element
        this.$button = this.$el.find('.button');
        
        // add event
        var self = this;
        $(this.el).on('click', function() {
            // hide all tooltips
            $('.tooltip').hide();
            
            // execute onclick callback
            if (options.onclick && !self.disabled) {
                options.onclick();
            }
        });
        
        // add tooltip
        $(this.el).tooltip({title: options.tooltip, placement: 'bottom'});
    },
    
    // disable
    disable: function() {
        this.$button.addClass('disabled');
        this.disabled = true;
    },
    
    // enable
    enable: function() {
        this.$button.removeClass('disabled');
        this.disabled = false;
    },
    
    // change icon
    setIcon: function(icon_cls) {
        this.$('i').removeClass(this.options.icon).addClass(icon_cls);
        this.options.icon = icon_cls;
    },
    
    // template
    _template: function(options) {
        // width
        var width = '';
        if (options.title) {
            width = 'width: auto;';
        }
        
        // string
        var str =   '<div id="' + options.id + '" style="float: ' + options.floating + '; ' + width + '" class="' + options.cls + '">';
    
        // title
        if (options.title) {
            str +=      '<div class="button">' +
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

// plugin
var Anchor = Backbone.View.extend({
    // options
    optionsDefault: {
        title  : '',
        cls    : ''
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
        return '<div><a href="javascript:void(0)" class="ui-anchor ' + options.cls + '">' + options.title + '</a></div>';
    }
});

// plugin
var Message = Backbone.View.extend({
    // options
    optionsDefault: {
        message     : null,
        status      : 'info',
        persistent  : false
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // create new element
        this.setElement('<div></div>');
        
        // show initial message
        if (this.options.message) {
            this.update(this.options);
        }
    },
    
    // update
    update : function(options) {
        // get options
        this.options = Utils.merge(options, this.optionsDefault);
        
        // show message
        if (options.message != '') {
            this.$el.html(this._template(this.options));
            this.$el.find('.alert').append(options.message);
            this.$el.fadeIn();
            
            // clear previous timeouts
            if (this.timeout) {
                window.clearTimeout(this.timeout);
            }
            
            // set timeout if message is not persistent
            if (!options.persistent) {
                var self = this;
                this.timeout = window.setTimeout(function() {
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
        return '<div class="ui-message alert alert-' + options.status + '"/>';
    }
});

// plugin
var Searchbox = Backbone.View.extend({
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
        return  '<div class="ui-search">' +
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
var Input = Backbone.View.extend({
    // options
    optionsDefault: {
        type            : 'text',
        placeholder     : '',
        disabled        : false,
        visible         : true,
        cls             : '',
        area            : false
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // set initial value
        if (this.options.value !== undefined) {
            this.value(this.options.value);
        }
        
        // disable input field
        if (this.options.disabled) {
            this.$el.prop('disabled', true);
        }
        
        // hide input field
        if (!this.options.visible) {
            this.$el.hide();
        }
        
        // onchange event handler. fires on user activity.
        var self = this;
        this.$el.on('input', function() {
            if (self.options.onchange) {
                self.options.onchange(self.$el.val());
            }
        });
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
        if (options.area) {
            return '<textarea id="' + options.id + '" class="ui-textarea ' + options.cls + '"></textarea>';
        } else {
            return '<input id="' + options.id + '" type="' + options.type + '" value="' + options.value + '" placeholder="' + options.placeholder + '" class="ui-input ' + options.cls + '">';
        }
    }
});

// plugin
var Hidden = Backbone.View.extend({
    // initialize
    initialize : function(options) {
        // configure options
        this.options = options;
        
        // create new element
        this.setElement(this._template(this.options));
        
        // set initial value
        if (this.options.value !== undefined) {
            this.value(this.options.value);
        }
    },
    
    // value
    value : function (new_val) {
        if (new_val !== undefined) {
            this.$('hidden').val(new_val);
        }
        return this.$('hidden').val();
    },
    
    // element
    _template: function(options) {
        var tmpl =  '<div id="' + options.id + '" >';
        if (options.info) {
            tmpl +=     '<label>' + options.info + '</label>';
        }
        tmpl +=         '<hidden value="' + options.value + '"/>' +
                    '</div>';
        return tmpl;
    }
});

// plugin
var CheckButton = Backbone.View.extend({

    // default options
    optionsDefault: {
        class_add       : 'fa fa-square-o',
        class_remove    : 'fa fa-check-square-o',
        class_partial   : 'fa fa-minus-square-o',
        value           : false
    },

    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);

        // create new element
        this.setElement($('<div/>'));

        // set initial value
        this.value(Boolean(this.options.value));

        // add event handler
        var self = this;
        this.$el.on('click', function() {
            self.value(!self.current);
        });
    },

    // value
    value : function (new_val) {
        if (new_val !== undefined) {
            this.current = new_val;
            if (new_val) {
                this.$el.removeClass()
                        .addClass('ui-checkbutton')
                        .addClass(this.options.class_remove);
            } else {
                this.$el.removeClass()
                        .addClass('ui-checkbutton')
                        .addClass(this.options.class_add);
            }
            this.options.onchange && this.options.onchange(new_val);
        }
        return this.current;
    }
});

// return
return {
    Anchor      : Anchor,
    Button      : Button,
    ButtonIcon  : ButtonIcon,
    ButtonMenu  : ButtonMenu,
    Icon        : Icon,
    Image       : Image,
    Input       : Input,
    Label       : Label,
    Message     : Message,
    Modal       : Modal,
    RadioButton : Options.RadioButton,
    Checkbox    : Options.Checkbox,
    Radio       : Options.Radio,
    CheckButton : CheckButton,
    Searchbox   : Searchbox,
    Select      : Select,
    Hidden      : Hidden,
    Slider      : Slider,
    Drilldown   : Drilldown
}
});
