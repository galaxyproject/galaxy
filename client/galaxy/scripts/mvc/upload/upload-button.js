/** View for upload/progress bar button */
define( [], function() {
    var View = Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.model = options && options.model || new Backbone.Model({
                icon        : 'fa-upload',
                tooltip     : 'Download from URL or upload files from disk',
                label       : 'Load Data',
                percentage  : 0,
                status      : '',
                onunload    : function(){},
                onclick     : function(){}
            }).set( options );
            this.setElement( this._template() );
            this.$progress = this.$( '.progress-bar' );
            this.listenTo( this.model, 'change', this.render, this );
            this.render();
            $( window ).on( 'beforeunload', function() {
                return self.model.get( 'onunload' )();
            });
        },

        render: function() {
            var self = this;
            var options = this.model.attributes;
            this.$el.off( 'click' ).on( 'click', function( e ) { options.onclick( e ) } )
                    .tooltip( { title: this.model.get('tooltip'), placement: 'bottom' } );
            this.$progress.removeClass()
                          .addClass( 'progress-bar' )
                          .addClass( 'progress-bar-notransition' )
                          .addClass( options.status != '' && 'progress-bar-' + options.status )
                          .css( { width : options.percentage + '%' } );
        },

        /** Template */
        _template: function() {
            return  '<div class="upload-button">' +
                        '<div class="progress">' +
                            '<div class="progress-bar"/>' +
                            '<a class="panel-header-button" href="javascript:void(0)" id="tool-panel-upload-button">' +
                                '<span class="fa fa-upload"/>' +
                            '</a>' +
                        '</div>' +
                    '</div>';
        }
    });
    return { View : View };
});
