define([
    "mvc/base-mvc",
    "utils/localization"
], function( baseMVC, _l ){
// =============================================================================
/** A view on any model that has a 'tags' attribute (a list of tag strings)
 *      Incorporates the select2 jQuery plugin for tags display/editing:
 *      http://ivaynberg.github.io/select2/
 */
var TagsEditor = Backbone.View
        .extend( baseMVC.LoggableMixin )
        .extend( baseMVC.HiddenUntilActivatedViewMixin ).extend({

    tagName     : 'div',
    className   : 'tags-display',

    /** Set up listeners, parse options */
    initialize : function( options ){
        //console.debug( this, options );
        // only listen to the model only for changes to tags - re-render
        if (options.usePrompt === false) {
            this.label = '';
        } else {
            this.label = '<label class="prompt">' + _l( 'Tags' ) + '</label>';
        }
        this.hiddenUntilActivated( options.$activator, options );
    },

    /** Build the DOM elements, call select to on the created input, and set up behaviors */
    render : function(){
        var self = this;
        this.$el.html( this._template() );

        this.$input().select2({
            placeholder : 'Add tags',
            width       : '100%',
            tags : function(){
                // initialize possible tags in the dropdown based on all the tags the user has used so far
                return self._getTagsUsed();
            }
        });

        this._setUpBehaviors();
        return this;
    },

    /** @returns {String} the html text used to build the view's DOM */
    _template : function(){
        return [
            this.label,
            // set up initial tags by adding as CSV to input vals (necc. to init select2)
            '<input class="tags-input" value="', this.tagsToCSV(), '" />'
        ].join( '' );
    },

    /** @returns {String} the sorted, comma-separated tags from the model */
    tagsToCSV : function(){
        var tagsArray = this.model.get( 'tags' );
        if( !_.isArray( tagsArray ) || _.isEmpty( tagsArray ) ){
            return '';
        }
        return tagsArray.map( function( tag ){
            return _.escape( tag );
        }).sort().join( ',' );
    },

    /** @returns {jQuery} the input for this view */
    $input : function(){
        return this.$el.find( 'input.tags-input' );
    },

    /** @returns {String[]} all tags used by the current user */
    _getTagsUsed : function(){
//TODO: global
        return Galaxy.user.get( 'tags_used' );
    },

    /** set up any event listeners on the view's DOM (mostly handled by select2) */
    _setUpBehaviors : function(){
        var view = this;
        this.$input().on( 'change', function( event ){
            // save the model's tags in either remove or added event
            view.model.save({ tags: event.val });
            // if it's new, add the tag to the users tags
            if( event.added ){
                //??: solve weird behavior in FF on test.galaxyproject.org where
                //  event.added.text is string object: 'String{ 0="o", 1="n", 2="e" }'
                view._addNewTagToTagsUsed( event.added.text + '' );
            }
        });
    },

    /** add a new tag (if not already there) to the list of all tags used by the user
     *  @param {String} newTag  the tag to add to the list of used
     */
    _addNewTagToTagsUsed : function( newTag ){
//TODO: global
        var tagsUsed = Galaxy.user.get( 'tags_used' );
        if( !_.contains( tagsUsed, newTag ) ){
            tagsUsed.push( newTag );
            tagsUsed.sort();
            Galaxy.user.set( 'tags_used', tagsUsed );
        }
    },

    /** shut down event listeners and remove this view's DOM */
    remove : function(){
        this.$input.off();
        this.stopListening( this.model );
        Backbone.View.prototype.remove.call( this );
    },

    /** string rep */
    toString : function(){ return [ 'TagsEditor(', this.model + '', ')' ].join(''); }
});

// =============================================================================
return {
    TagsEditor : TagsEditor
};
});
