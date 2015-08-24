// dependencies
define([], function() {

// model for upload/progress bar button
var Model = Backbone.Model.extend({
    defaults: {
        icon        : 'fa-upload',
        tooltip     : 'Download from URL or upload files from disk',
        label       : 'Load Data',
        percentage  : 0,
        status      : ''
    }
});

// view for upload/progress bar button
var View = Backbone.View.extend({
    // model
    model : null,

    // initialize
    initialize : function(options) {
        // link this
        var self = this;

        // create model
        var model = options.model;

        // create new element
        this.setElement(this._template());

        // add event
        $(this.el).on('click', function(e) { options.onclick(e); });

        // add tooltip
        $(this.el).tooltip({title: model.get('tooltip'), placement: 'bottom'});

        // events
        model.on('change:percentage', function() {
            self._percentage(model.get('percentage'));
        });
        model.on('change:status', function() {
            self._status(model.get('status'));
        });

        // unload event
        var self = this;
        $(window).on('beforeunload', function() {
            var text = "";
            if (options.onunload) {
                text = options.onunload();
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
    _template: function() {
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
    Model   : Model,
    View    : View
};

});
