/**
    This class creates a form input element wrapper
*/
define([], function() {
    return Backbone.View.extend({
        initialize: function(app, options) {
            this.app = app;
            this.field = options.field;

            // set text labels and icons for collapsible button
            this.text_enable    = app.options.text_enable || 'Enable';
            this.text_disable   = app.options.text_disable || 'Disable';
            this.cls_enable     = app.options.cls_enable || 'fa fa-caret-square-o-down';
            this.cls_disable    = app.options.cls_disable || 'fa fa-caret-square-o-up';

            // set element
            this.setElement(this._template(options));

            // link elements
            this.$field = this.$('.ui-form-field');
            this.$preview = this.$('.ui-form-preview');
            this.$collapsible = this.$('.ui-form-collapsible');
            this.$collapsible_icon = this.$('.ui-form-collapsible').find('.icon');
            this.$error_text = this.$('.ui-form-error-text');
            this.$error = this.$('.ui-form-error');
            this.$backdrop = this.$('.ui-form-backdrop');

            // add field element
            this.$field.prepend(this.field.$el);

            // decide wether to expand or collapse fields
            this.field.collapsed = options.collapsible_value !== undefined && JSON.stringify( options.value ) == JSON.stringify( options.collapsible_value );

            // refresh view
            this._refresh();

            // add collapsible hide/show
            var self = this;
            this.$collapsible.on('click', function() {
                self.field.collapsed = !self.field.collapsed;
                self._refresh();
            });
        },

        /** Disable input element
        */
        disable: function( silent ) {
            this.$backdrop.show();
            silent && this.$backdrop.css({ 'opacity': 0, 'cursor': 'default' } );
        },

        /** Set error text
        */
        error: function(text) {
            this.$error_text.html(text);
            this.$error.show();
            this.$el.addClass('ui-error');
        },

        /** Reset this view
        */
        reset: function() {
            this.$error.hide();
            this.$el.removeClass('ui-error');
        },

        /** Refresh element
        */
        _refresh: function() {
            this.$collapsible_icon.removeClass().addClass('icon');
            if (!this.field.collapsed) {
                this.$field.fadeIn('fast');
                this.$preview.hide();
                this._tooltip(this.text_disable, this.cls_disable);
            } else {
                this.$field.hide();
                this.$preview.show();
                this._tooltip(this.text_enable, this.cls_enable);
            }
            this.app.trigger('change');
        },

        /** Set tooltip text
        */
        _tooltip: function(title, cls) {
            this.$collapsible_icon.addClass(cls)
                               .tooltip({ placement: 'bottom' })
                               .attr('data-original-title', title)
                               .tooltip('fixTitle').tooltip('hide');
        },

        /** Main Template
        */
        _template: function(options) {
            var tmp =   '<div class="ui-form-element">' +
                            '<div class="ui-form-error ui-error">' +
                                '<span class="fa fa-arrow-down"/><span class="ui-form-error-text"/>' +
                            '</div>' +
                            '<div class="ui-form-title">';
            if ( !options.disabled && options.collapsible_value !== undefined ) {
                tmp +=          '<div class="ui-form-collapsible">' +
                                    '<i class="icon"/>' + options.label +
                                '</div>';
            } else {
                tmp += options.label;
            }
            tmp +=          '</div>' +
                            '<div class="ui-form-field">';
            tmp +=              '<div class="ui-form-info">';
            if (options.help) {
                tmp +=              options.help;
            }
            if (options.argument && options.help.indexOf('(' + options.argument + ')') == -1) {
                tmp +=              ' (' + options.argument + ')';
            }
            tmp +=              '</div>' +
                                '<div class="ui-form-backdrop"/>' +
                            '</div>';
            if ( options.collapsible_preview ) {
                tmp +=      '<div class="ui-form-preview">' + options.text_value + '</div>';
            }
            tmp += '</div>';
            return tmp;
        }
    });
});