/**
 *  This class contains backbone wrappers for basic ui elements such as Images, Labels, Buttons, Input fields etc.
 */
define(['utils/utils',
    'mvc/ui/ui-select-default',
    'mvc/ui/ui-slider',
    'mvc/ui/ui-options',
    'mvc/ui/ui-drilldown',
    'mvc/ui/ui-buttons',
    'mvc/ui/ui-modal'],
    function( Utils, Select, Slider, Options, Drilldown, Buttons, Modal ) {

    /** Image wrapper */
    var Image = Backbone.View.extend({
        initialize : function(options) {
            this.options = Utils.merge(options, {
                url  : '',
                cls  : ''
            });
            this.setElement(this._template(this.options));
        },
        _template: function(options) {
            return '<img class="ui-image ' + options.cls + '" src="' + options.url + '"/>';
        }
    });

    /** Label wrapper */
    var Label = Backbone.View.extend({
        initialize : function(options) {
            this.options = Utils.merge(options, {
                title  : '',
                cls    : ''
            });
            this.setElement(this._template(this.options));
        },
        title: function(new_title) {
            this.$el.html(new_title);
        },
        value: function() {
            return options.title;
        },
        _template: function(options) {
            return '<label class="ui-label ' + options.cls + '">' + options.title + '</label>';
        }
    });

    /** Displays an icon with title */
    var Icon = Backbone.View.extend({
        initialize : function(options) {
            this.options = Utils.merge(options, {
                floating    : 'right',
                icon        : '',
                tooltip     : '',
                placement   : 'bottom',
                title       : '',
                cls         : ''
            });
            this.setElement(this._template(this.options));
            $(this.el).tooltip({title: options.tooltip, placement: 'bottom'});
        },
        _template: function(options) {
            return  '<div>' +
                        '<span class="fa ' + options.icon + '" class="ui-icon"/>&nbsp;' +
                        options.title +
                    '</div>';
        }
    });

    /** Renders an anchor element */
    var Anchor = Backbone.View.extend({
        initialize : function(options) {
            this.options = Utils.merge(options, {
                title  : '',
                cls    : ''
            });
            this.setElement(this._template(this.options));
            $(this.el).on('click', options.onclick);
        },
        _template: function(options) {
            return '<div><a href="javascript:void(0)" class="ui-anchor ' + options.cls + '">' + options.title + '</a></div>';
        }
    });

    /** Displays messages used e.g. in the tool form */
    var Message = Backbone.View.extend({
        initialize : function(options) {
            this.options = Utils.merge(options, {
                message     : null,
                status      : 'info',
                cls         : '',
                persistent  : false
            });
            this.setElement('<div class="' + this.options.cls + '"/>');
            this.options.message && this.update(this.options);
        },

        // update
        update: function(options) {
            // get options
            this.options = Utils.merge(options, this.options);

            // show message
            if (options.message != '') {
                this.$el.html(this._template(this.options));
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

        // template
        _template: function(options) {
            var cls_status = 'ui-message alert alert-' + options.status;
            if (options.large) {
                cls_status = ( ( options.status == 'success' && 'done' ) ||
                               ( options.status == 'danger' && 'error' ) ||
                                 options.status ) + 'messagelarge';
            }
            return  '<div class="' + cls_status + '" >' +
                        options.message +
                    '</div>';
        }
    });

    /** Render a search box */
    var Searchbox = Backbone.View.extend({
        initialize : function(options) {
            this.options = Utils.merge(options, {
                onclick : null,
                searchword : ''
            });
            this.setElement(this._template(this.options));
            var self = this;
            if (this.options.onclick) {
                this.$el.on('submit', function(e) {
                    var search_field = self.$el.find('#search');
                    self.options.onclick(search_field.val());
                });
            }
        },
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

    /** Renders an input element used e.g. in the tool form */
    var Input = Backbone.View.extend({
        initialize : function(options) {
            // configure options
            this.options = Utils.merge(options, {
                type            : 'text',
                placeholder     : '',
                disabled        : false,
                visible         : true,
                cls             : '',
                area            : false
            });

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

        // template
        _template: function(options) {
            if (options.area) {
                return '<textarea id="' + options.id + '" class="ui-textarea ' + options.cls + '"></textarea>';
            } else {
                return '<input id="' + options.id + '" type="' + options.type + '" value="' + options.value + '" placeholder="' + options.placeholder + '" class="ui-input ' + options.cls + '">';
            }
        }
    });

    /** Creates a hidden element input field used e.g. in the tool form */
    var Hidden = Backbone.View.extend({
        initialize : function(options) {
            this.options = options;
            this.setElement(this._template(this.options));
            if (this.options.value !== undefined) {
                this.value(this.options.value);
            }
        },
        value : function (new_val) {
            if (new_val !== undefined) {
                this.$('hidden').val(new_val);
            }
            return this.$('hidden').val();
        },
        _template: function(options) {
            var tmpl =  '<div id="' + options.id + '" >';
            if (options.info) {
                tmpl +=     '<div>' + options.info + '</div>';
            }
            tmpl +=         '<hidden value="' + options.value + '"/>' +
                        '</div>';
            return tmpl;
        }
    });

    return {
        Anchor      : Anchor,
        Button      : Buttons.ButtonDefault,
        ButtonIcon  : Buttons.ButtonIcon,
        ButtonCheck : Buttons.ButtonCheck,
        ButtonMenu  : Buttons.ButtonMenu,
        ButtonLink  : Buttons.ButtonLink,
        Icon        : Icon,
        Image       : Image,
        Input       : Input,
        Label       : Label,
        Message     : Message,
        Modal       : Modal,
        RadioButton : Options.RadioButton,
        Checkbox    : Options.Checkbox,
        Radio       : Options.Radio,
        Searchbox   : Searchbox,
        Select      : Select,
        Hidden      : Hidden,
        Slider      : Slider,
        Drilldown   : Drilldown
    }
});
