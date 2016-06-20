/**
 *  This class takes a dictionary as input an creates an input form. It uses the Ui.Table element to organize and format the form elements.
 */
define( [ 'mvc/ui/ui-table', 'mvc/ui/ui-misc', 'mvc/form/form-parameters', 'utils/utils' ], function( Table, Ui, Parameters, Utils ) {
var View = Backbone.View.extend({
    optionsDefault: {
        title       : '',
        content     : '',
        mode        : ''
    },

    initialize: function( app, options ) {
        this.app = app;
        this.list = [];
        this.options = Utils.merge( options, this.optionsDefault );
        this.table_title = new Ui.Label( { title: this.options.title } );
        this.table = new Table.View( { content: this.options.content } );
        this.parameters = new Parameters();
        var $view = $( '<div/>' ).addClass( 'ui-form' );
        this.options.title && $view.append( this.table_title.$el );
        $view.append( this.table.$el );
        this.setElement( $view );
    },

    /** Set title */
    title: function( new_title ) {
        this.table_title.title( new_title );
    },

    /** Update form */
    update: function( settings, model ) {
        this.table.delAll();
        this.list = [];
        for ( var id in settings ) {
            this._add( settings[ id ].id || id, settings[ id ], model );
        }
        for ( var id in this.list ) {
            this.list[ id ].trigger('change');
        }
    },

    /** Add table row */
    _add: function( id, settings_def, model ) {
        var self = this;
        if ( settings_def.type !== 'separator' ) {
            switch( settings_def.type ) {
                case 'select':
                    settings_def.onchange = function( new_value ) {
                        model.set( id, new_value );
                        var dict = _.findWhere( settings_def.data, { value: new_value } );
                        if ( dict && dict.operations ) {
                            var operations = dict.operations;
                            for ( var i in operations.show ) {
                                self.table.get( operations.show[ i ] ).show();
                            }
                            for ( var i in operations.hide ) {
                                self.table.get( operations.hide[ i ] ).hide();
                            }
                        }
                    };
                    break;
                default:
                    settings_def.onchange = function( new_value ) { model.set( id, new_value ) };
            }
            settings_def.id = id;
            settings_def.value = model.get( id, settings_def.init );
            model.set( id, settings_def.value );
            var field = this.parameters.create( settings_def );
            var $input = $( '<div/>' ).append( field.$el );
            if ( settings_def.info ) {
                $input.append( '<div class="ui-form-info">' + settings_def.info + '</div>' );
            }
            if ( this.options.style == 'bold' ) {
                this.table.add( new Ui.Label( { title: settings_def.title, cls: 'form-label' } ).$el );
                this.table.add( $input );
            } else {
                this.table.add( '<span class="ui-form-title">' + settings_def.title + '</span>', '25%' );
                this.table.add( $input );
            }
            this.list[ id ] = field;
        } else {
            this.table.add( '<div class="ui-form-separator">' + settings_def.title + ':<div/>' );
            this.table.add( $( '<div/>' ) );
        }
        this.table.append( id );
        settings_def.hide && this.table.get( id ).hide();
    }
});

return {
    View : View
}

});