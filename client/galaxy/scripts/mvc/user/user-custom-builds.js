/** This class renders the chart configuration form. */
define( [ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/form/form-view', 'mvc/ui/ui-table' ], function( Utils, Ui, Form, Table ) {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.model = new Backbone.Model();
            this.model.url = Galaxy.root + 'api/users/' + Galaxy.user.id + '/custom_builds_metadata';
            this.collection = new Backbone.Collection();
            this.collection.url = Galaxy.root + 'api/users/' + Galaxy.user.id + '/custom_builds';
            this.message = new Ui.Message({});
            this.table = new Table.View( { cls: 'grid' } );
            this.table.addHeader( 'Name' );
            this.table.addHeader( 'Key' );
            this.table.addHeader( 'Number of chroms/contigs' );
            this.table.addHeader( '' );
            this.table.appendHeader();
            this.setElement( $( '<div/>' ).append( this.message.$el.addClass( 'ui-margin-bottom' ) )
                                          .append( $( '<h4/>' ).text( 'Current Custom Builds' ) )
                                          .append( this.table.$el )
                                          .append( $( '<h4/>' ).text( 'Add a Custom Build' ).addClass( 'ui-margin-top' ) )
                                          .append( this.$form = $( '<div/>' ).addClass( 'ui-margin-bottom' ) ) );
            this.listenTo( this.collection, 'add remove reset', function() { self._renderTable() } );
            this.listenTo( this.model, 'change', function() { self._renderForm() } );
            this.collection.fetch();
            this.model.fetch();
        },

        render: function() {
            this._renderTable();
            this._renderForm();
        },

        _renderTable: function() {
            var self = this;
            this.table.delAll();
            this.collection.each( function( model ) {
                self.table.add( model.id );
                self.table.add( model.get( 'name' ) );
                self.table.add( model.get( 'count' ) );
                self.table.add( ( new Ui.ButtonIcon({
                    icon    : 'fa-trash-o',
                    cls     : 'ui-button-icon-plain',
                    tooltip : 'Delete custom build.',
                    onclick : function() { alert( model.id ); }
                } ) ).$el );
                self.table.append( model.id );
            });
        },

        _renderForm: function() {
            var form = new Form({
                inputs  : [{
                    type    : 'text',
                    name    : 'id',
                    label   : 'Name',
                    help    : 'Specify a build name e.g. Hamster.'
                },{
                    type    : 'text',
                    name    : 'id',
                    label   : 'Key',
                    help    : 'Specify a build key e.g. hamster_v1.'
                },{
                    name        : 'definition',
                    type        : 'conditional',
                    test_param  : {
                        name    : 'type',
                        label   : 'Definition',
                        help    : 'Provide the data source.',
                        type    : 'select',
                        value   : 'len',
                        data    : [ { value : 'fasta',  label : 'FASTA' },
                                    { value : 'len',    label : 'Len File' },
                                    { value : 'entry',  label : 'Len Entry' } ]
                    },
                    cases       : [ { value   : 'fasta' },
                                    { value   : 'len' },
                                    { value   : 'entry',
                                      inputs  : [ {
                                         type   : 'text',
                                         area   : true,
                                         name   : 'value',
                                         label  : 'Edit/Paste'
                                      } ]
                                    } ]
                }],
                buttons : {
                    save    : new Ui.Button({
                        icon     : 'fa-save',
                        tooltip  : 'Create new Build',
                        title    : 'Save',
                        cls      : 'ui-button btn btn-primary',
                        floating : 'clear',
                        onclick  : function() {
                            alert( 'new' );
                        }
                    })
                }
            });
            this.$form.empty().append( form.$el );
        }
    });

    return {
        View: View
    }
});