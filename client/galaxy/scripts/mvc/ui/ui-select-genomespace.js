// dependencies
define(['utils/utils', 'mvc/ui/ui-misc', 'mvc/tool/tool-genomespace'],
        function(Utils, Ui, GenomespaceBrowser) {

/**
 * GenomeSpace file selector
 */
var View = Backbone.View.extend({
    // initialize
    initialize : function(options) {

        // link this
        var self = this;

        // create insert new list element button
        this.browse_button = new Ui.ButtonIcon({
            title       : 'Browse',
            icon        : 'fa fa-sign-in',
            tooltip     : 'Browse GenomeSpace',
            onclick     : function() {
                self.browseGenomeSpace();
            }
        });

        // create genomespace filepath textbox
        this.filename_textbox = new Ui.Input();

        // create genomespace token textbox
        this.token_textbox = new Ui.Input({
          type       : 'password'        
        });

        // create elements
        this.setElement(this._template(options));
        this.$('.ui-gs-browse-button').append(this.browse_button.$el);
        this.$('.ui-gs-filename-textbox').append(this.filename_textbox.$el);
        this.$('.ui-gs-token-textbox').append(this.token_textbox.$el);
    },

    /** Browse GenomeSpace */
    browseGenomeSpace: function(options) {
        var self = this;
        GenomespaceBrowser.openFileBrowser({
            successCallback: function(data) {
                self.value(data.destination + "^" + data.token);
            }
        });
    },
    
    /** Main Template */
    _template: function(options) {
        return  '<div class="ui-gs-select-file">' +
                    '<div class="ui-gs-browse-field">' +
                        '<span class="ui-gs-browse-button" />' +
                        '<span class="ui-gs-filename-textbox" />' +
                    '</div>' +
                    '<div class="ui-gs-token-field">' +
                        '<span class=ui-gs-label"><div class="ui-gs-token-label">Token</div></span>' +
                        '<span class="ui-gs-token-textbox" />' +
                    '</div>' +
                '</div>';
    },
    
    /** Return/Set currently selected genomespace filename/token */
    value : function (new_value) {
        // check if new_value is defined
        if (new_value !== undefined) {
            this._setValue(new_value);
        }
        else {
          return this._getValue();
        }
    },
    
    // get value
    _getValue: function() {
        return this.filename_textbox.value() +
            "^" + this.token_textbox.value();
    },
    
    // set value
    _setValue: function(new_value) {
        if (new_value) {
          values = new_value.split("^");
          this.filename_textbox.value(values[0]);
          this.token_textbox.value(values[1]);
        }
    },
    
});

return {
    View: View
}

});
