define( [ 'utils/utils', 'mvc/ui/ui-tabs', 'mvc/ui/ui-misc', 'mvc/form/form-view' ], function( Utils, Tabs, Ui, Form ) {

    /** Dataset edit attributes view */
    var View = Backbone.View.extend({
        initialize: function() {
            this.setElement( '<div/>' );
            this.model = new Backbone.Model( { 'dataset_id': Galaxy.params.dataset_id } );
            this.message = new Ui.Message();
            this.render();
        },

        // fetch data for the selected dataset and build forms
        render: function() {
            var self = this;
            $.ajax({
                url     : Galaxy.root + 'dataset/get_edit?dataset_id=' + self.model.get( 'dataset_id' ),
                success : function( response ) {
                    self._render( self, response );
                },
                error   : function( response ) {
                    self._error( response );
                }
            });
        },

        /** render page */
        _render: function( self, response ) {
            this.$el.empty()
                    .append( $( '<h4/>' ).append( 'Edit attributes of \'' + response.display_name + '\'' ) )
                    .append( this.message.$el )
                    .append( this._getAttributes( response ) )
                    .append( '<p/>' )
                    .append( this._getConversion( response ) )
                    .append( '<p/>' )
                    .append( this._getDatatype( response ) )
                    .append( '<p/>' )
                    .append( this._getPermission( response ) );
            this.message.update( response );
        },

        /** perform AJAX post call */
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
                    form.message.update( { message: response.message, status: 'success', persistent: false } );
                    self._reloadHistory();
                },
                error   : function( response ) {
                    form.message.update( response );
                }
            });
        },

        /** error message helper */
        _error: function( response ) {
            var err_msg = response.responseJSON && response.responseJSON.err_msg;
            this.message.update({
                'status'    : 'danger',
                'message'   : err_msg || 'Error occured while loading the dataset.',
                'persistent': true
            });
        },

        /** attributes tab template */
        _getAttributes: function( response ) {
            var self = this;
            var form = new Form({
                title  : 'Edit attributes',
                inputs : response.attribute_inputs,
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
                        onclick  : function() { self._submit( self, form, response, "auto-detect" ) }
                    })
                }
            });
            return form.$el;
        },

        /** convert tab template */
        _getConversion: function( response ) {
            var self = this;
            var form = new Form({
                title  : 'Convert to new format',
                inputs : response.datatype_inputs,
                buttons: {
                    'submit' : new Ui.ButtonIcon({
                        cls      : 'btn btn-primary',
                        tooltip  : 'Convert the datatype to a new format.',
                        title    : 'Convert datatype',
                        icon     : 'fa-exchange ',
                        onclick  : function() { self._submit( self, form, response, "convert" ) }
                    })
                }
            });
            return form.$el;
        },

        /** change datatype template */
        _getDatatype: function( response ) {
            var self = this;
            var form = new Form({
                title  : 'Change datatype',
                inputs : response.conversion_inputs,
                buttons: {
                    'submit' : new Ui.ButtonIcon({
                        cls      : 'btn btn-primary',
                        tooltip  : 'Change the datatype to a new type.',
                        title    : 'Change datatype',
                        icon     : 'fa-exchange ',
                        onclick  : function() { self._submit( self, form, response, "change" ) }
                    })
                }
            });
            return form.$el;
        },

        /** permissions template */
        _getPermission: function( response ) {
            var template = "",
                self = this;
            if( response.can_manage_dataset ) {
                var form = new Form({
                    title  : 'Manage dataset permissions',
                    inputs : response.permission_inputs,
                    buttons: {
                        'submit': new Ui.ButtonIcon({
                            cls      : 'btn btn-primary',
                            tooltip  : 'Save permissions.',
                            title    : 'Save permissions',
                            icon     : 'fa-floppy-o ',
                            onclick  : function() { self._submit( self, form, response, "permissions" ) }
                        })
                    }
                });
                return form.$el;
            }
            else {
                var form = new Form({
                    title  : 'View permissions',
                    inputs : response.permission_inputs
                });
                return form.$el;
            }
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
