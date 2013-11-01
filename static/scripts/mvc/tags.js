/** */
var TagsEditor = Backbone.View.extend( LoggableMixin ).extend({
    
    tagName     : 'div',
    className   : 'tags-display',

    /** */
    initialize : function( options ){
        //console.debug( this, options );
        this.listenTo( this.model, 'change:tags', function(){
            this.render();
        });
    },

    /** */
    render : function(){
        var view = this;

        this.$el.html( this.template() );
        this.$el.find( '.tags-input' ).select2({
            placeholder : 'Add tags',
            width       : '100%',
            tags : function(){
                // initialize possible tags in the dropdown based on all the tags the user has used so far
                return view.getTagsUsed();
            }
        });
        this._behaviors();
        return this;
    },

    /** */
    template : function(){
        return [
            //TODO: make prompt optional
            '<label class="prompt">', _l( 'Tags' ), '</label>',
            // set up initial tags by adding as CSV to input vals (necc. to init select2)
            '<input class="tags-input" value="', this.tagsToCSV( this.model.get( 'tags' ) ), '" />'
        ].join( '' );
    },

    /** */
    tagsToCSV : function( tagsArray ){
        if( !_.isArray( tagsArray ) || _.isEmpty( tagsArray ) ){
            return '';
        }
        return tagsArray.sort().join( ',' );
    },

    /** */
    getTagsUsed : function(){
        return _.map( Galaxy.currUser.get( 'tags_used' ), function( tag ){
            return { id: tag, text: tag };
        });
    },

    /** */
    _behaviors : function(){
        var view = this;
        this.$el.find( '.tags-input' ).on( 'change', function( event ){
            // save the model's tags in either remove or added event
            view.model.save({ tags: event.val }, { silent: true });
            // if it's new, add the tag to the users tags
            if( event.added ){
                view.addNewTagToTagsUsed( event.added.text );
            }
        });
    },

    /** */
    addNewTagToTagsUsed : function( newTag ){
        var tagsUsed = Galaxy.currUser.get( 'tags_used' );
        if( !_.contains( tagsUsed, newTag ) ){
            tagsUsed.push( newTag );
            tagsUsed.sort();
            Galaxy.currUser.set( 'tags_used', tagsUsed );
        }
    },

    /** */
    remove : function(){
        this.$el.off();
        Backbone.View.prototype.remove.call( this );
    },

    /** */
    toString : function(){ return [ 'TagSetView(', this.model + '', ')' ].join(''); }
});
