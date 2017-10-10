/** Dataset edit attributes view */
define( [ 'utils/utils', 'mvc/ui/ui-tabs', 'mvc/ui/ui-misc', 'mvc/form/form-view' ], function( Utils, Tabs, Ui, Form ) {
    var View = Backbone.View.extend({
        initialize: function() {
            this.setElement( '<div/>' );
            this.model = new Backbone.Model( { 'dataset_id': Galaxy.params.dataset_id } );
            this.message = new Ui.Message( { 'persistent': true } );
            this.tabs = this._createTabs();
            this.$el.append( $( '<h4/>' ).append( 'Edit dataset attributes' ) )
                    .append( this.message.$el )
                    .append( '<p/>' )
                    .append( this.tabs.$el );
            this.render();
        },

        /** fetch data for the selected dataset and build forms */
        render: function() {
            var self = this;
            $.ajax({
                url     : Galaxy.root + 'dataset/get_edit?dataset_id=' + self.model.get( 'dataset_id' ),
                success : function( response ) {
                    self._render( response );
                },
                error   : function( response ) {
                    var err_msg = response.responseJSON && response.responseJSON.err_msg;
                    self.message.update({
                        'status'    : 'danger',
                        'message'   : err_msg || 'Error occured while loading the dataset.'
                    });
                }
            });
        },

        /** render page */
        _render: function( response ) {
            this.message.update( response );
            this.attribute_form.model.set( 'inputs', response.attribute_inputs );
            this.conversion_form.model.set( 'inputs', response.conversion_inputs );
            this.datatype_form.model.set( 'inputs', response.datatype_inputs );
            this.permission_form.model.set( 'inputs', response.permission_inputs );
            this.attribute_form.render();
            this.conversion_form.render();
            this.datatype_form.render();
            this.permission_form.render();
        },

        /** submit data to backend to update attributes */
        _submit: function( operation, form ) {
            var self = this;
            var data = form.data.create();
            data.dataset_id = this.model.get( 'dataset_id' );
            data.operation  = operation;
            $.ajax({
                type    : 'PUT',
                url     : Galaxy.root + 'dataset/set_edit',
                data    : data,
                success : function( response ) {
                    self.render();
                    self._reloadHistory();
                },
                error   : function( response ) {
                    var err_msg = response.responseJSON && response.responseJSON.err_msg;
                    self.message.update({
                        'status'    : 'danger',
                        'message'   : err_msg || 'Error occured while editing the dataset attributes.'
                    });
                }
            });
        },

        /** create tabs for different dataset attribute categories*/
        _createTabs: function() {
            var self = this;
            var tabs = new Tabs.View();
            this.attribute_form = this._getAttributeForm();
            this.conversion_form = this._getConversion();
            this.datatype_form = this._getDatatype();
            this.permission_form = this._getPermission();
            tabs.add({
                id      : 'attributes',
                title   : 'Attributes',
                icon    : 'fa fa-bars',
                tooltip : 'Edit dataset attributes',
                $el     : this.attribute_form.$el
            });
            tabs.add({
                id      : 'convert',
                title   : 'Convert',
                icon    : 'fa-gear',
                tooltip : 'Convert to new format',
                $el     :  this.conversion_form.$el
            });
            tabs.add({
                id      : 'datatype',
                title   : 'Datatypes',
                icon    : 'fa-database',
                tooltip : 'Change data type',
                $el     : this.datatype_form.$el
            });
            tabs.add({
                id      : 'permissions',
                title   : 'Permissions',
                icon    : 'fa-user',
                tooltip : 'Permissions',
                $el     : this.permission_form.$el
            });
            return tabs;
        },

        /** edit main attributes form */
        _getAttributeForm: function() {
            var self = this;
            var form = new Form({
                title  : 'Edit attributes',
                buttons: {
                    'submit_editattr' : new Ui.ButtonIcon({
                        cls      : 'btn btn-primary',
                        tooltip  : 'Save attributes of the dataset.',
                        icon     : 'fa-floppy-o ',
                        title    : 'Save',
                        onclick  : function() { self._submit( 'attributes', form ) }
                    }),
                    'submit_autocorrect' : new Ui.ButtonIcon({
                        cls      : 'btn btn-primary',
                        tooltip  : 'This will inspect the dataset and attempt to correct the values of fields if they are not accurate.',
                        icon     : 'fa-undo ',
                        title    : 'Auto-detect',
                        onclick  : function() { self._submit( 'autodetect', form ) }
                    })
                }
            });
            return form;
        },

        /** datatype conversion form */
        _getConversion: function() {
            var self = this;
            var form = new Form({
                title  : 'Convert to new format',
                buttons: {
                    'submit' : new Ui.ButtonIcon({
                        cls      : 'btn btn-primary',
                        tooltip  : 'Convert the datatype to a new format.',
                        title    : 'Convert datatype',
                        icon     : 'fa-exchange ',
                        onclick  : function() { self._submit( 'conversion', form ) }
                    })
                }
            });
            return form;
        },

        /** change datatype form */
        _getDatatype: function() {
            var self = this;
            var form = new Form({
                title  : 'Change datatype',
                buttons: {
                    'submit' : new Ui.ButtonIcon({
                        cls      : 'btn btn-primary',
                        tooltip  : 'Change the datatype to a new type.',
                        title    : 'Change datatype',
                        icon     : 'fa-exchange ',
                        onclick  : function() { self._submit( 'datatype', form ) }
                    })
                }
            });
            return form;
        },

        /** dataset permissions form */
        _getPermission: function() {
            var self = this;
            var form = new Form({
                title  : 'Manage dataset permissions',
                buttons: {
                    'submit': new Ui.ButtonIcon({
                        cls      : 'btn btn-primary',
                        tooltip  : 'Save permissions.',
                        title    : 'Save permissions',
                        icon     : 'fa-floppy-o ',
                        onclick  : function() { self._submit( 'permission', form ) }
                    })
                }
            });
            return form;
        },

        /** reload Galaxy's history after updating dataset's attributes */
        _reloadHistory: function() {
            if ( window.Galaxy ) {
                window.Galaxy.currHistoryPanel.loadCurrentHistory();
            }
        }
    });

    return {
        View  : View
    };
});
