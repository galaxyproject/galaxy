/** Import history from archive view */
var View = Backbone.View.extend({
    initialize: function() {
        var self = this;
        this.setElement(this._mainTemplate());
        var $form = this.$('form');
        var $message = this.$('.ui-message');
        this.$('.btn-primary').on('click', () => {
            $.ajax({
                url: `${Galaxy.root}api/histories`,
                data: new FormData($form[0]),
                cache: false,
                contentType: false,
                processData: false,
                method: 'POST'
            })
            .done(response => {
                return;
                window.location = `${Galaxy.root}histories/list?message=${response.message}&status=success`
            })
            .fail(response => {
                let message = response.responseJSON && response.responseJSON.err_msg;
                $message.removeClass()
                        .addClass('ui-message alert alert-danger')
                        .text(message || 'Import failed for unkown reason.')
                        .show();
            });
        });
    },

    /** Template */
    _mainTemplate: function() {
        return `<div class='ui-portlet-limited'>
            <div class='portlet-header'>
                <div class='portlet-title'>
                    <i class='portlet-title-icon fa fa-upload'></i>
                    <span class='portlet-title-text'><b>Import a History from an Archive</b></span>
                </div>
            </div>
            <div class='portlet-content'>
                <div class='portlet-body'>
                    <div class='ui-message'/>
                    <form>
                        <div class='ui-form-element'>
                            <div class='ui-form-title'>Archived History URL</div>
                            <input class='ui-input' type='text' name='archive_source'/>
                        </div>
                        <div class='ui-form-element'>
                            <div class='ui-form-title'>Archived History file</div>
                            <input type='file' name='archive_file'/>
                        </div>
                    </form>
                </div>
                <div class='portlet-buttons'>
                    <input class='btn btn-primary' type='button' value='Import History'/>
                </div>
            </div>
        </div>`;
    }
});

export default {
    View: View
};
