// dependencies
define(['utils/utils', 'mvc/ui/ui-list'],
        function(Utils, List) {

/**
 * FTP file selector
 */
var View = Backbone.View.extend({
    // initialize
    initialize : function(options) {
        // link this
        var self = this;

        // create ui-list view to keep track of selected ftp files
        this.ftpfile_list = new List.View({
            name        : 'file',
            optional    : options.optional,
            multiple    : options.multiple,
            onchange    : function() {
                options.onchange && options.onchange(self.value());
            }
        });

        // create elements
        this.setElement(this.ftpfile_list.$el);

        // initial fetch of ftps
        Utils.get({
            url     : Galaxy.root + 'api/remote_files',
            success : function(response) {
                var data = [];
                for (var i in response) {
                    data.push({
                        value   : response[i]['path'],
                        label   : response[i]['path']
                    });
                }
                self.ftpfile_list.update(data);
            }
        });
    },

    /** Return/Set currently selected ftp datasets */
    value: function(val) {
        return this.ftpfile_list.value(val);
    }
});

return {
    View: View
}

});
