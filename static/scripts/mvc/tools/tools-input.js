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
            
            // link field
            this.field = options.field;
            
            // set element
            this.setElement(this._template(options));
            
            // link elements
            this.$field = this.$el.find('.ui-table-form-field');
            this.$title_optional = this.$el.find('.ui-table-form-title-optional');
            this.$error_text = this.$el.find('.ui-table-form-error-text');
            this.$error = this.$el.find('.ui-table-form-error');
            
            // add field element
            this.$field.prepend(this.field.$el);
            
            // hide optional field on initialization
            if (options.optional) {
                this.field.skip = true;
            } else {
                this.field.skip = false;
            }
            
            // refresh view
            this._refresh();
                
            // add optional hide/show
            var self = this;
            this.$title_optional.on('click', function() {
                // flip flag
                self.field.skip = !self.field.skip;
                
                // refresh view
                self._refresh();
            });
        },
        
        /** Set error text
        */
        error: function(text) {
            this.$error_text.html(text);
            this.$error.fadeIn();
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
                this.$title_optional.html('Disable');
                this.app.refresh();
            } else {
                this.$field.hide();
                this.$title_optional.html('Enable');
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
                tmp +=          'Optional: ' + options.label +
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
