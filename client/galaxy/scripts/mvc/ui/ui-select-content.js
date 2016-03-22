define([ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/ui/ui-select-default' ], function( Utils, Ui, Select ) {

/** List of available content selectors options */
var Configurations = {
    'data': [
        { name: 'single',       src: 'hda',  icon: 'fa-file-o',   tooltip: 'Single dataset',     batchmode: false, multiple: false },
        { name: 'multiple',     src: 'hda',  icon: 'fa-files-o',  tooltip: 'Multiple datasets',  batchmode: true,  multiple: true  },
        { name: 'collection',   src: 'hdca', icon: 'fa-folder-o', tooltip: 'Dataset collection', batchmode: true,  multiple: false } ],
    'data_collection': [
        { name: 'collection',   src: 'hdca', icon: 'fa-folder-o', tooltip: 'Dataset collection', batchmode: false, multiple: false } ],
    'data_multiple': [
        { name: 'multiple',     src: 'hda',  icon: 'fa-files-o',  tooltip: 'Multiple datasets',  batchmode: false, multiple: true  },
        { name: 'collection',   src: 'hdca', icon: 'fa-folder-o', tooltip: 'Dataset collection', batchmode: false, multiple: false } ]
};

/** View for hda and hdca content selector ui elements */
var View = Backbone.View.extend({
    initialize : function( options ) {
        var self = this;
        this.model = options && options.model || new Backbone.Model( options );
        this.setElement( $( '<div/>' ).addClass( 'ui-select-content' ) );
        this.$batch = $( '<div/>' ).addClass( 'ui-form-info' )
                        .append( $( '<i/>' ).addClass( 'fa fa-sitemap' ) )
                        .append( $( '<span/>' ).html( 'This is a batch mode input field. A separate job will be triggered for each dataset.' ) );

        // track current history elements
        this.history = {};

        // add listeners
        this.listenTo( this.model, 'change', this.render, this );
        this.listenTo( this.model, 'change:type change:multiple', this._changeType, this );
        this.listenTo( this.model, 'change:value', this._changeValue, this );
        this.listenTo( this.model, 'change:data', this._changeData, this );
        this.listenTo( this.model, 'change:wait', this._changeWait, this );
        this.render();

        // update selectable data and initial value
        this.model.get( 'value' ) !== undefined && this.model.trigger( 'change:value' );
        this.model.trigger( 'change:type' );
        this.model.trigger( 'change:value' );

        // add change event. fires on trigger
        this.on( 'change', function() { options.onchange && options.onchange( self.value() ) } );
    },

    render: function() {
        var self = this;
        _.each( this.fields, function( field, i ) {
            if ( self.model.get( 'current' ) == i ) {
                field.$el.show();
                self.$batch[ self.config[ i ].batchmode && 'show' || 'hide' ]();
                self.button_type.value( i );
            } else {
                field.$el.hide();
            }
        });
    },

    /** Indicate that select fields are being updated */
    wait: function() {
        this.model.set( 'wait', true );
    },

    /** Indicate that the options update has been completed */
    unwait: function() {
        this.model.set( 'wait', false );
    },

    /** Update data representing selectable options */
    update: function( options ) {
        this.model.set( 'data', options );
    },

    /** Return the currently selected dataset values */
    value: function ( new_value ) {
        new_value !== undefined && this.model.set( 'value', new_value );
        var current = this.model.get( 'current' );
        if ( this.config[ current ] ) {
            var id_list = this.fields[ current ].value();
            if (id_list !== null) {
                id_list = $.isArray( id_list ) ? id_list : [ id_list ];
                if ( id_list.length > 0 ) {
                    var result = { batch: this._batch(), values: [] };
                    for ( var i in id_list ) {
                        var details = this.history[ id_list[ i ] + '_' + this.config[ current ].src ];
                        if ( details ) {
                            result.values.push( details );
                        } else {
                            Galaxy.emit.debug( 'tools-select-content::_changeValue()', 'Requested details not found for \'' + id_list[ i ] + '\'.'  );
                            return null;
                        }
                    }
                    result.values.sort( function( a, b ) { return a.hid - b.hid } );
                    return result;
                }
            }
        } else {
            Galaxy.emit.debug( 'tools-select-content::_changeValue()', 'Invalid value/source \'' + new_value + '\'.'  );
        }
        return null;
    },

    /** Change of type */
    _changeType: function() {
        var self = this;
        this.model.set( 'current', 0 );

        // identify selector type
        var config_id = String( this.model.get( 'type' ) ) + ( this.model.get( 'multiple' ) ? '_multiple' : '' );
        if ( Configurations[ config_id ] ) {
            this.config = Configurations[ config_id ];
        } else {
            this.config = Configurations[ 'data' ];
            Galaxy.emit.debug( 'tools-select-content::_changeType()', 'Invalid configuration/type id \'' + config_id + '\'.'  );
        }

        // prepare error messages
        var extensions = Utils.textify( this.model.get( 'extensions' ) );
        var hda_error  = extensions ? 'No ' + extensions + ' dataset available.'            : 'No dataset available.';
        var hdca_error = extensions ? 'No ' + extensions + ' dataset collection available.' : 'No dataset collection available.';

        // build views
        this.fields = [];
        this.button_data = [];
        _.each( this.config, function( c, i ) {
            self.button_data.push({
                value   : i,
                icon    : c.icon,
                tooltip : c.label
            });
            self.fields.push(
                new Select.View({
                    optional    : self.model.get( 'optional' ),
                    multiple    : c.multiple,
                    searchable  : !c.multiple,
                    error_text  : c.type === 'hda' ? hda_error : hdca_error,
                    onchange    : function() {
                        self.trigger( 'change' );
                    }
                })
            );
        });
        this.button_type = new Ui.RadioButton.View({
            value   : this.model.get( 'current' ),
            data    : this.button_data,
            onchange: function( value ) {
                self.model.set( 'current', value );
                self.trigger('change');
            }
        });

        // append views
        this.$el.empty();
        var button_width = 0;
        if ( this.fields.length > 1 ) {
            this.$el.append( this.button_type.$el );
            button_width = Math.max( 0, this.fields.length * 35 ) + 'px';
        }
        _.each( this.fields, function( field ) {
            self.$el.append( field.$el.css( { 'margin-left': button_width } ) );
        });
        this.$el.append( this.$batch.css( { 'margin-left': button_width } ) );
        this.model.trigger( 'change:data' );
    },

    /** Change of wait flag */
    _changeWait: function() {
        var self = this;
        _.each( this.fields, function( field ) { field[ self.model.get( 'wait' ) ? 'wait' : 'unwait' ]() } );
    },

    /** Change of available options */
    _changeData: function() {
        var options = this.model.get( 'data' );
        var self = this;
        var select_options = {};
        _.each( options, function( items, src ) {
            select_options[ src ] = [];
            _.each( items, function( item ) {
                select_options[ src ].push({
                    hid  : item.hid,
                    label: item.hid + ': ' + item.name,
                    value: item.id
                });
                self.history[ item.id + '_' + src ] = item;
            });
        });
        _.each( this.config, function( c, i ) {
            self.fields[ i ].add( select_options[  c.src ], function( a, b ) { return b.hid - a.hid } );
        });
    },

    /** Change of incoming value */
    _changeValue: function () {
        var new_value = this.model.get( 'value' );
        if ( new_value && new_value.values && new_value.values.length > 0 ) {
            // create list with content ids
            var list = [];
            _.each( new_value.values, function( value ) {
                list.push( value.id );
            });
            // sniff first suitable field type from config list
            var src = new_value.values[ 0 ].src;
            var multiple = new_value.values.length > 1;
            var current = -1;
            for( var i = 0; i < this.config.length; i++ ) {
                var field = this.fields[ i ];
                var c = this.config[ i ];
                if ( current === -1 && c.src == src && [ multiple, true ].indexOf( c.multiple ) !== -1 ) {
                    this.model.set( 'current', current = i );
                    field.value( list );
                }
            }
        } else {
            _.each( this.fields, function( field ) {
                field.value( null );
            });
        }
    },

    /** Assists in identifying the batch mode */
    _batch: function() {
        var current = this.model.get( 'current' );
        var config = this.config[ current ];
        if ( config.src == 'hdca' && !config.multiple ) {
            var hdca = this.history[ this.fields[ current ].value() + '_hdca' ];
            if ( hdca && hdca.map_over_type ) {
                return true;
            }
        }
        return config.batchmode;
    }
});

return {
    View: View
}

});
