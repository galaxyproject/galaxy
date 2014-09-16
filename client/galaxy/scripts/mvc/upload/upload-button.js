// dependencies
define([], function() {

// create model
var Model = Backbone.Model.extend({
    defaults: {
        percentage  : 0,
        icon        : 'fa-circle',
        label       : '',
        status      : ''
    }
});

// progress bar button on ui
var View = Backbone.View.extend({
    // model
    model : null,

    // initialize
    initialize : function(model) {
        // link this
        var self = this;
        
        // create model
        this.model = model;
        
        // get options
        this.options = this.model.attributes;
            
        // create new element
        this.setElement(this._template(this.options));
        
        // add event
        $(this.el).on('click', this.options.onclick);
        
        // add tooltip
        if (this.options.tooltip) {
            $(this.el).tooltip({title: this.options.tooltip, placement: 'bottom'});
        }
        
        // events
        this.model.on('change:percentage', function() {
            self._percentage(self.model.get('percentage'));
        });
        this.model.on('change:status', function() {
            self._status(self.model.get('status'));
        });
        
        // unload event
        var self = this;
        $(window).on('beforeunload', function() {
            var text = "";
            if (self.options.onunload) {
                text = self.options.onunload();
            }
            if (text != "") {
                return text;
            }
        });
    },
    
    // set status
    _status: function(value) {
        var $el = this.$el.find('.progress-bar');
        $el.removeClass();
        $el.addClass('progress-bar');
        $el.addClass('progress-bar-notransition');
        if (value != '') {
            $el.addClass('progress-bar-' + value);
        }
    },
    
    // set percentage
    _percentage: function(value) {
        var $el = this.$el.find('.progress-bar');
        $el.css({ width : value + '%' });
    },
    
    // template
    _template: function(options) {
        return  '<div style="float: right">' +
                    '<div class="upload-button">' +
                        '<div class="progress">' +
                            '<div class="progress-bar"></div>' +
                        '</div>' +
                        '<div id="label" class="label">' +
                            '<a class="panel-header-button" href="javascript:void(0)">' +
                                '<span class="fa fa-upload"></span>' +
                            '</a>' +
                        '</div>' +
                    '</div>' +
                '</div>';
    }
});

return {
    Model: Model,
    View: View
};

});
