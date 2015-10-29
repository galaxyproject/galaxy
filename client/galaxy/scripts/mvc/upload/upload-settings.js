/** This renders the content of the settings popup, allowing users to specify flags i.e. for space-to-tab conversion **/
define(['utils/utils'], function(Utils) {
return Backbone.View.extend({
    // options
    options: {
        class_check     : 'upload-icon-button fa fa-check-square-o',
        class_uncheck   : 'upload-icon-button fa fa-square-o'
    },

    // initialize
    initialize: function(app) {
        // link app
        this.app = app;

        // link this
        var self = this;

        // set template
        this.setElement(this._template());

        // link model
        this.model = this.app.model;

        // ui event: space-to-tab
        this.$('#upload-space-to-tab').on('click', function() {
            self._switchState('#upload-space-to-tab', 'space_to_tab');
        });

        // ui event: to-posix-lines
        this.$('#upload-to-posix-lines').on('click', function() {
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
        this._renderState('#upload-space-to-tab', this.model.get('space_to_tab'));
        this._renderState('#upload-to-posix-lines', this.model.get('to_posix_lines'));

        // disable options
        var $cover = this.$('#upload-settings-cover');
        if (!this.model.get('enabled')) {
            $cover.show();
        } else {
            $cover.hide();
        }
    },

    // switch state
    _switchState: function (element_id, parameter_id) {
        if (this.model.get('enabled')) {
            var checked = !this.model.get(parameter_id);
            this.model.set(parameter_id, checked);
            this._renderState(element_id, checked);
        }
    },

    // render state
    _renderState: function (element_id, checked) {
        var $it = this.$(element_id);
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
                    '<table class="ui-table-striped">' +
                        '<tbody>' +
                            '<tr>' +
                                '<td><div id="upload-space-to-tab"/></td>' +
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
