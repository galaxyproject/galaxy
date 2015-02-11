/**
    This class creates a tool form input element wrapper
*/
define([], function() {

    // input field element wrapper
    return Backbone.View.extend({
        // initialize input wrapper
        initialize: function(app, options) {
            // link app
            this.app = app;
            
            // set text labels
            this.text_enable = app.options.text_enable || 'Enable';
            this.text_disable = app.options.text_disable || 'Disable';

            // link field
            this.field = options.field;
            this.default_value = options.default_value;
            
            // set element
            this.setElement(this._template(options));
            
            // link elements
            this.$field = this.$el.find('.ui-table-form-field');
            this.$title_optional = this.$el.find('.ui-table-form-title-optional');
            this.$error_text = this.$el.find('.ui-table-form-error-text');
            this.$error = this.$el.find('.ui-table-form-error');
            
            // add field element
            this.$field.prepend(this.field.$el);
            
            // decide wether to expand or collapse optional fields
            this.field.skip = false;
            var v = this.field.value && this.field.value();
            this.field.skip = Boolean(options.optional &&
                                        ((v === null || (v == this.default_value) ||
                                         (Number(v) == Number(this.default_value)) ||
                                         (JSON.stringify(v) == JSON.stringify(this.default_value)))));

            // refresh view
            this._refresh();
                
            // add optional hide/show
            var self = this;
            this.$title_optional.on('click', function() {
                // flip flag
                self.field.skip = !self.field.skip;
                
                // refresh view
                self._refresh();
                
                // refresh state
                self.app.trigger('refresh');
            });
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
            if (!this.field.skip) {
                this.$field.fadeIn('fast');
                this.$title_optional.html(this.text_disable);
            } else {
                this.reset();
                this.$field.hide();
                this.$title_optional.html(this.text_enable);
                this.field.value && this.field.value(this.default_value);
            }
        },
        
        /** Main Template
        */
        _template: function(options) {
            // create table element
            var tmp =   '<div class="ui-table-form-element">' +
                            '<div class="ui-table-form-error ui-error">' +
                                '<span class="fa fa-arrow-down"/><span class="ui-table-form-error-text"/>' +
                            '</div>' +
                            '<div class="ui-table-form-title-strong">';
            
            // is optional
            if (options.optional) {
                tmp +=          options.label +
                                '<span>&nbsp[<span class="ui-table-form-title-optional"/>]</span>';
            } else {
                tmp +=          options.label;
            }
            
            // finalize title
            tmp +=          '</div>' +
                            '<div class="ui-table-form-field">';
            // add help
            if (options.help) {
                tmp +=          '<div class="ui-table-form-info">' + options.help + '</div>';
            }
            
            // finalize
            tmp +=          '</div>' +
                        '</div>';
            
            // return input element
            return tmp;
        }
    });
});
