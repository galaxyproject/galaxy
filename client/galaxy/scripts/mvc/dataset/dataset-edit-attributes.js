
define( [ 'utils/utils', 'mvc/ui/ui-tabs', 'mvc/ui/ui-misc' ], function( Utils, Tabs, Ui ) {

    /** Dataset edit attributes view */
    var View = Backbone.View.extend({

        initialize: function( dataset_id ) {
            this.setElement( '<div/>' );
            this.render( dataset_id );
        },

        render: function( dataset_id ) {
            var url = Galaxy.root + 'dataset/edit',
                self = this;
            Utils.get({
                url     : url,
                data    : { 'dataset_id': dataset_id },
                success : function( response ) {
                    self.create_tabs( self, response);
                },
                error   : function() {
                    var error_msg = "Error occurred while loading the resource.",
                        options = { 'message': error_msg, 'status': 'error', 'persistent': true, 'cls': 'errormessage' };
                    self.page.display( new Ui.Message( options ) );
                }
            });
        },

        /** Create tabs for different attributes of dataset*/
        create_tabs: function( self, response ) {
            self.tabs = new Tabs.View();
            self.tabs.add({
                id      : 'attributes',
                title   : 'Attributes',
                icon    : 'fa fa-bars',
                tooltip : 'Edit dataset attributes'
            });

            self.tabs.add({
                id      : 'convert',
                title   : 'Convert',
                icon    : 'fa-gear',
                tooltip : 'Convert to new format'
            });

            self.tabs.add({
                id      : 'datatype',
                title   : 'Datatypes',
                icon    : 'fa-database',
                tooltip : 'Change data type'
            });

            self.tabs.add({
                id      : 'permissions',
                title   : 'View Permissions',
                icon    : 'fa-user',
                tooltip : 'View permissions'
            });

            self.$el.empty().append( self.tabs.$el );
            self.tabs.showTab( 'attributes' );
        }
    });

    return {
        View  : View
    };
});
