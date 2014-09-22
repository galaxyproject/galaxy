// dependencies
define(['utils/utils'], function(Utils) {

// item view
return Backbone.View.extend({
    // options
    options: {
        class_check     : 'upload-icon-button fa fa-check-square-o',
        class_uncheck   : 'upload-icon-button fa fa-square-o'
    },
    
    // render
    initialize: function(app) {
        // link app
        this.app = app;
        
        // link this
        var self = this;
        
        // set template
        this.setElement(this._template());
        
        // link model
        this.model = this.app.model;
        
        // ui event: space to tabs
        this.$el.find('#upload-space-to-tabs').on('click', function() {
            self._switchState('#upload-space-to-tabs', 'space_to_tabs');
        });
        
        // ui event: to posix
        this.$el.find('#upload-to-posix-lines').on('click', function() {
            self._switchState('#upload-to-posix-lines', 'to_posix_lines');
        });
        
        // render
        this.render();
    },
    
    // events
    events: {
        'mousedown' : function(e) { e.preventDefault(); }
    },

    // render
    render: function() {
        // render states
        this._renderState('#upload-space-to-tabs', this.model.get('space_to_tabs'));
        this._renderState('#upload-to-posix-lines', this.model.get('to_posix_lines'));
        
        // disable options
        var $cover = this.$el.find('#upload-settings-cover');
        if (this.model.get('status') != 'init') {
            $cover.show();
        } else {
            $cover.hide();
        }
    },
    
    // switch state
    _switchState: function (element_id, parameter_id) {
        if (this.model.get('status') == 'init') {
            var checked = !this.model.get(parameter_id);
            this.model.set(parameter_id, checked);
            this._renderState(element_id, checked);
        }
    },
    
    // render state
    _renderState: function (element_id, checked) {
        // swith icon class
        var $it = this.$el.find(element_id);
        $it.removeClass();
        if (checked) {
            $it.addClass(this.options.class_check);
        } else {
            $it.addClass(this.options.class_uncheck);
        }
    },
    
    // load template
    _template: function() {
        return  '<div class="upload-settings" style="position: relative;">' +
                    '<div id="upload-settings-cover" class="upload-settings-cover"/>' +
                    '<table class="table table-striped">' +
                        '<tbody>' +
                            '<tr>' +
                                '<td><div id="upload-space-to-tabs"/></td>' +
                                '<td>Convert spaces to tabs</td>' +
                            '</tr>' +
                            '<tr>' +
                                '<td><div id="upload-to-posix-lines"/></td>' +
                                '<td>Use POSIX standard</td>' +
                            '</tr>' +
                        '</tbody>' +
                    '</table>' +
                '</div>';
    }
});

});
