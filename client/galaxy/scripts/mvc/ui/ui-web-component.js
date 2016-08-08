/**
 *  This class contains backbone wrappers for basic ui elements such as Images, Labels, Buttons, Input fields etc.
 */
define(['utils/utils',
    ],
    function( Utils ) {


    /** Renders an input element used e.g. in the tool form */
    var WebComponent = Backbone.View.extend({
        initialize: function( options ) {
            this.model = options && options.model || new Backbone.Model({
                component       : null,
                type            : 'text',
                placeholder     : '',
                disabled        : false,
                visible         : true,
                cls             : '',
                area            : false,
                color           : null,
                style           : null
            }).set( options );
            this.webcomponent = '<script src="/plugins/visualization/polymer/bower_components/webcomponentsjs/webcomponents-lite.js"></script><link rel="import" href="/plugins/visualization/polymer/test-app/'+this.model.get('component')+'.html"><'+this.model.get('component')+'></'+this.model.get('component')+'>';
            this.tagName = this.model.get( 'component' );
            this.setElement( $( '<' + this.tagName + '/>' ) );
            this.listenTo( this.model, 'change', this.render, this );
            this.render();
        },
        events: {
            'input': '_onchange'
        },
        value: function( new_val ) {
            new_val !== undefined && this.model.set( 'value', typeof new_val === 'string' ? new_val : '' );
            return this.model.get( 'value' );
        },
        render: function() {
            this.$el.removeClass()
                    .prepend('<script src="/static/polymer/bower_components/webcomponentsjs/webcomponents-lite.js"></script><link rel="import" href="/static/polymer/test-app/'+this.model.get('component')+'.html">')
                    .addClass( this.model.get( 'cls' ) )
                    .addClass( this.model.get( 'style' ) )
                    .attr( 'galaxyid', this.model.id )
                    .css( 'color', this.model.get( 'color' ) || '' )
                    .css( 'border-color', this.model.get( 'color' ) || '' );
            if ( this.model.get( 'value' ) !== this.$el.attr('galaxyvalue') ) {
                this.$el.attr( 'galaxyvalue', this.model.get( 'value' ) );
            }
            this.model.get( 'disabled' ) ? this.$el.attr( 'disabled', true ) : this.$el.removeAttr( 'disabled' );
            this.$el[ this.model.get( 'visible' ) ? 'show' : 'hide' ]();
            return this;
        },
        _onchange: function() {
            this.value( this.$("#"+this.model.id).val() );
            this.model.get( 'onchange' ) && this.model.get( 'onchange' )( this.model.get( 'value' ) );
        }
    });

    return {
        WebComponent       : WebComponent
    }
});
