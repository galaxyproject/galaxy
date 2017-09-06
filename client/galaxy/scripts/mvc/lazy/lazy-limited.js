/** Contains helpers to limit/lazy load views for backbone views */
define([], function() {
    return Backbone.View.extend({
        initialize: function( options ) {
            var self = this;
            this.$container   = options.$container;
            this.collection   = options.collection;
            this.new_content  = options.new_content;
            this.max          = options.max || 50;
            this.content_list = {}
            this.$message     = $( '<div/>' ).addClass( 'ui-limitloader' ).append( '...only the first ' + this.max + ' entries are visible.' );
            this.$container.append( this.$message );
        },

        /** Checks if the limit has been reached */
        _done: function() {
            var done = _.size( this.content_list ) > this.max;
            this.$message[ done ? 'show' : 'hide' ]();
            return done;
        },

        /** Remove all content */
        reset: function() {
            _.each( this.content_list, function( content ) {
                content.remove();
            });
            this.content_list = {};
            this.$message.hide();
        },

        /** Remove content */
        remove: function( model_id ) {
            var content = this.content_list[ model_id ];
            if ( content ) {
                content.remove();
                delete this.content_list[ model_id ];
            }
            this.refresh();
        },

        /** Refreshes container content by adding new views if visible */
        refresh: function() {
            if ( !this._done() ) {
                for ( var i in this.collection.models ) {
                    var model = this.collection.models[ i ];
                    var view = this.content_list[ model.id ];
                    if ( !this.content_list[ model.id ] ) {
                        var content = this.new_content( model );
                        this.content_list[ model.id ] = content;
                        if ( this._done() ) {
                            break;
                        }
                    }
                }
            }
        }
    });
});
