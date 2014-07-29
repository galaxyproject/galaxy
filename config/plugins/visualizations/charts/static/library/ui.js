// dependencies
define(['utils/utils', 'plugin/library/ui-select', 'plugin/library/ui-button-menu', 'mvc/ui/ui-modal'],
        function(Utils, Select, ButtonMenu, Modal) {

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
        float       : 'right',
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
        id    : null,
        title : '',
        float : 'right',
        cls   : 'btn btn-default',
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
        var str =   '<button id="' + options.id + '" type="submit" style="float: ' + options.float + ';" type="button" class="ui-button ' + options.cls + '">';
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
        id      : null,
        title   : '',
        float   : 'right',
        cls     : 'icon-btn',
        icon    : '',
        tooltip : '',
        onclick : null
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
        var str =   '<div id="' + options.id + '" style="float: ' + options.float + '; ' + width + '" class="ui-button-icon ' + options.cls + '">';
    
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
            this.$el.find('.alert').append(options.message);
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
        value           : '',
        type            : 'text',
        placeholder     : '',
        disabled        : false,
        visible         : true,
        cls             : ''
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
        return '<input id="' + options.id + '" type="' + options.type + '" value="' + options.value + '" placeholder="' + options.placeholder + '" class="ui-input ' + options.cls + '">';
    }
});

// plugin
var Textarea = Backbone.View.extend({
    // options
    optionsDefault: {
        value           : '',
        type            : 'text',
        placeholder     : '',
        disabled        : false,
        visible         : true,
        cls             : ''
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
        return '<textarea id="' + options.id + '" class="ui-textarea ' + options.cls + '" rows="5"></textarea>';
    }
});

// plugin
var RadioButton = Backbone.View.extend({
    // options
    optionsDefault: {
        value           : '',
        visible         : true,
        cls             : '',
        data            : [],
        id              : Utils.uuid()
    },
    
    // initialize
    initialize : function(options) {
        // configure options
        this.options = Utils.merge(options, this.optionsDefault);
            
        // create new element
        this.setElement(this._template(this.options));
        
        // hide input field
        if (!this.options.visible) {
            this.$el.hide();
        }
        
        // set initial value
        if (this.options.value) {
            this.value(this.options.value);
        }
        
        // current value
        this.current = this.options.value;
        
        // onchange event handler. fires on user activity.
        var self = this;
        this.$el.find('input').on('change', function() {        
            self.value(self._getValue());
        });
    },
    
    // value
    value : function (new_val) {
        // get current value
        var before = this.current;
        
        // set new value
        if (new_val !== undefined) {
            this.$el.find('label').removeClass('active');
            this.$el.find('[value="' + new_val + '"]').closest('label').addClass('active');
            this.current = new_val;
        }

        // check value
        var after = this.current;
        if (after != before && this.options.onchange) {
            this.options.onchange(this.current);
        }

        // get and return value
        return this.current;
    },
    
    // get value
    _getValue: function() {
        var selected = this.$el.find(':checked');
        var value = null;
        if (selected.length > 0) {
            value = selected.val();
        }
        return value;
    },
    
    // element
    _template: function(options) {
        var tmpl =  '<div class="btn-group ui-radiobutton" data-toggle="buttons">';
        for (key in options.data) {
            var pair = options.data[key];
            tmpl +=     '<label class="btn btn-default">' +
                            '<input type="radio" name="' + options.id + '" value="' + pair.value + '" selected>' + pair.label +
                        '</label>';
        }
        tmpl +=     '</div>';
        return tmpl;
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
    RadioButton : RadioButton,
    Searchbox   : Searchbox,
    Select      : Select,
    Textarea    : Textarea
}
});
