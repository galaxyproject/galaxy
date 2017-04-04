/** This class renders the chart configuration form. */
define( [ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/form/form-view', 'mvc/ui/ui-table' ], function( Utils, Ui, Form, Table ) {
    var Collection = Backbone.Collection.extend({
        comparator: function( a, b ) {
            a = a.get( 'name' );
            b = b.get( 'name' );
            return a > b ?  1 : a < b ? -1 : 0;
        }
    });

    var View = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            var history_id = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
            this.model = new Backbone.Model();
            this.model.url = Galaxy.root + 'api/histories/' + history_id + '/custom_builds_metadata';
            this.collection = new Collection();
            this.collection.url = Galaxy.root + 'api/users/' + Galaxy.user.id + '/custom_builds';
            this.message = new Ui.Message({});
            this.installed_builds = new Ui.Select.View({
                optional    : true,
                onchange    : function() { self.installed_builds.value( null ) },
                empty_text  : 'List of available builds:',
                error_text  : 'No system installed builds available.'
            });
            this.table = new Table.View( { cls: 'grid', selectable: false } );
            this.table.addHeader( 'Name' );
            this.table.addHeader( 'Key' );
            this.table.addHeader( 'Number of chroms/contigs' );
            this.table.addHeader( '' );
            this.table.appendHeader();
            this.setElement( $( '<div/>' ).append( $( '<h4/>' ).text( 'Current Custom Builds' ) )
                                          .append( this.table.$el )
                                          .append( this.$installed = $( '<div/>' ).append( $( '<h4/>' ).text( 'System Installed Builds' ).addClass( 'ui-margin-top' ) )
                                                                                  .append( this.installed_builds.$el ) )
                                          .append( $( '<h4/>' ).text( 'Add a Custom Build' ).addClass( 'ui-margin-top' ) )
                                          .append( $( '<span/>').addClass( 'ui-column' )
                                                                .append( $( '<div/>' ).addClass( 'ui-column-left' )
                                                                                      .append( this.message.$el )
                                                                                      .append( this.$form = $( '<div/>' ).addClass( 'ui-margin-top' ) ) )
                                                                .append( this.$help = $( '<div/>' ).addClass( 'ui-column-right' ) ) ) );
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
            this.collection.sort();
            this.collection.each( function( model ) {
                self.table.add( model.id );
                self.table.add( model.get( 'name' ) );
                self.table.add( model.get( 'count' ) !== undefined ? model.get( 'count' ) : 'Processing...' );
                self.table.add( ( new Ui.ButtonIcon({
                    icon    : 'fa-trash-o',
                    cls     : 'ui-button-icon-plain',
                    tooltip : 'Delete custom build.',
                    onclick : function() { model.destroy() }
                } ) ).$el );
                self.table.append( model.id );
            });
        },

        _renderForm: function() {
            var self = this;
            var initial_type = 'fasta';
            var form = new Form({
                inputs  : [{
                    type    : 'text',
                    name    : 'name',
                    label   : 'Name',
                    help    : 'Specify a build name e.g. Hamster.'
                },{
                    type    : 'text',
                    name    : 'id',
                    label   : 'Key',
                    help    : 'Specify a build key e.g. hamster_v1.'
                },{
                    name        : 'len',
                    type        : 'conditional',
                    test_param  : {
                        name    : 'type',
                        label   : 'Definition',
                        help    : 'Provide the data source.',
                        type    : 'select',
                        value   : initial_type,
                        data    : [ { value : 'fasta',  label : 'FASTA-file from history' },
                                    { value : 'file',   label : 'Len-file from disk' },
                                    { value : 'text',   label : 'Len-file by copy/paste' } ]
                    },
                    cases       : [ {
                        value   : 'fasta',
                        inputs  : [ {
                            type   : 'select',
                            name   : 'value',
                            label  : 'FASTA-file',
                            data   : this.model.get( 'fasta_hdas' )
                        } ]
                    },{
                        value   : 'file',
                        inputs  : [ {
                            type   : 'upload',
                            name   : 'value',
                            label  : 'Len-file',
                            data   : this.model.get( 'len_hdas' )
                        } ]
                    },{
                        value   : 'text',
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
                            var data = form.data.create();
                            if ( !data.id || !data.name ) {
                                self.message.update( { message: 'All inputs are required.', status: 'danger' } );
                            } else {
                                self.collection.create( data, {
                                    wait    : true,
                                    success : function( response ) {
                                        if ( response.get( 'message' ) ) {
                                            self.message.update( { message: response.get( 'message' ), status: 'warning' } );
                                        } else {
                                            self.message.update( { message: 'Successfully added a new custom build.', status: 'success' } );
                                        }
                                    },
                                    error   : function( response, err ) {
                                        var message = err && err.responseJSON && err.responseJSON.err_msg;
                                        self.message.update( { message: message || 'Failed to create custom build.', status: 'danger' } );
                                    }
                                });
                            }
                        }
                    })
                },
                onchange: function() {
                    var input_id = form.data.match( 'len|type' );
                    if ( input_id ) {
                        var input_field = form.field_list[ input_id ];
                        self._renderHelp( input_field.value() );
                    }
                }
            });
            this.$form.empty().append( form.$el );
            var installed_builds = this.model.get( 'installed_builds' );
            if ( installed_builds && installed_builds.length ) {
                this.$installed.show();
                this.installed_builds.update( this.model.get( 'installed_builds' ) );
            } else {
                this.$installed.hide();
            }
            this._renderHelp( initial_type );
        },

        _renderHelp: function( len_type ) {
            this.$help.empty()
                      .addClass( 'alert alert-info' )
                      .html( len_type == 'fasta' ? this._templateFasta() : this._templateLen() );
        },

        _templateLen: function() {
            return  '<h4>Length Format</h4>' +
                    '<p>' +
                        'The length format is two-column, separated by whitespace, of the form:' +
                        '<pre>chrom/contig   length of chrom/contig</pre>' +
                    '</p>' +
                    '<p>' +
                        'For example, the first few entries of <em>mm9.len</em> are as follows:' +
                        '<pre>' +
                            'chr1    197195432\n' +
                            'chr2    181748087\n' +
                            'chr3    159599783\n' +
                            'chr4    155630120\n' +
                            'chr5    152537259' +
                        '</pre>' +
                    '</p>' +
                    '<p>Trackster uses this information to populate the select box for chrom/contig, and' +
                    'to set the maximum basepair of the track browser. You may either upload a .len file' +
                    'of this format (Len File option), or directly enter the information into the box ' +
                    '(Len Entry option).</p>';
        },

        _templateFasta: function() {
            return  '<h4>FASTA format</h4>' +
                    '<p>' +
                        'This is a multi-fasta file from your current history that provides the genome' +
                        'sequences for each chromosome/contig in your build.' +
                    '</p>' +
                    '<p>' +
                        'Here is a snippet from an example multi-fasta file:' +
                        '<pre>' +
                            '>chr1\n' +
                            'ATTATATATAAGACCACAGAGAGAATATTTTGCCCGG...\n\n' +
                            '>chr2\n' +
                            'GGCGGCCGCGGCGATATAGAACTACTCATTATATATA...\n\n' +
                            '...' +
                        '</pre>' +
                    '</p>';
        }
    });

    return {
        View: View
    }
});