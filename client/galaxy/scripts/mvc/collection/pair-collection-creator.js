define([
    "mvc/collection/list-collection-creator",
    "mvc/history/hdca-model",
    "mvc/ui/error-modal",
    "mvc/base-mvc",
    "utils/localization"
], function( LIST_CREATOR, HDCA, errorModal, BASE_MVC, _l ){
/*==============================================================================

==============================================================================*/
/**  */
var PairedDatasetCollectionElementView = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({
//TODO: use proper class (DatasetDCE or NestedDCDCE (or the union of both))
    tagName     : 'li',
    className   : 'collection-element',

    initialize : function( attributes ){
        this.element = attributes.element || {};
        this.identifier = attributes.identifier;
    },

    render : function(){
        this.$el
            .attr( 'data-element-id', this.element.id )
            .html( this.template({ identifier: this.identifier, element: this.element }) );
        return this;
    },

    //TODO: lots of unused space in the element - possibly load details and display them horiz.
    template : _.template([
        '<span class="identifier"><%= identifier %></span>',
        '<span class="name"><%= element.name %></span>',
    ].join('')),

    /** remove the DOM and any listeners */
    destroy : function(){
        this.off();
        this.$el.remove();
    },

    /** string rep */
    toString : function(){
        return 'DatasetCollectionElementView()';
    }
});


// ============================================================================
var _super = LIST_CREATOR.ListCollectionCreator;

/** An interface for building collections.
 */
var PairCollectionCreator = _super.extend({

    /** the class used to display individual elements */
    elementViewClass : PairedDatasetCollectionElementView,
    /** the class this creator will create and save */
    collectionClass : HDCA.HistoryPairDatasetCollection,
    className : 'pair-collection-creator collection-creator flex-row-container',

    /** mangle duplicate names using a mac-like '(counter)' addition to any duplicates */
    _mangleDuplicateNames : function(){
    },

    // ------------------------------------------------------------------------ rendering elements
    /** render the elements in order (or a warning if no elements found) */
    _renderList : function( speed, callback ){
        //this.debug( '-- _renderList' );
        var creator = this,
            $tmp = jQuery( '<div/>' );

        _.each( this.elementViews, function( view ){
            view.destroy();
            creator.removeElementView( view );
        });

        if( this.workingElements.length < 2 ){
            this._renderNoValidElements();
            return;
        }
        $tmp.append( creator._createForwardElementView().$el );
        $tmp.append( creator._createReverseElementView().$el );
        creator.$list().empty().append( $tmp.children() );
        _.invoke( creator.elementViews, 'render' );
    },

    _createForwardElementView : function(){
        var element = this.workingElements[0],
            view = this._createElementView( element );
        view.identifier = _l( 'Forward' );
        return view;
    },

    _createReverseElementView : function(){
        var element = this.workingElements[1],
            view = this._createElementView( element );
        view.identifier = _l( 'Reverse' );
        return view;
    },

    /** listen to any element events */
    _listenToElementView : function( view ){
        // var creator = this;
        // creator.listenTo( view, {
        // });
    },

    swap : function(){
        this.workingElements = [
            this.workingElements[1],
            this.workingElements[0],
        ];
        this._renderList();
    },

    events : _.extend( _.clone( _super.prototype.events ), {
        'click .swap'              : 'swap',
    }),

    // ------------------------------------------------------------------------ templates
    //TODO: move to require text plugin and load these as text
    //TODO: underscore currently unnecc. bc no vars are used
    //TODO: better way of localizing text-nodes in long strings
    /** underscore template fns attached to class */
    templates : _.extend( _.clone( _super.prototype.templates ), {
        /** the middle: element list */
        middle : _.template([
            '<div class="collection-elements-controls">',
                '<a class="swap" href="javascript:void(0);" title="', _l( 'Swap forward and reverse datasets' ), '">',
                    _l( 'Swap' ),
                '</a>',
            '</div>',
            '<div class="collection-elements scroll-container flex-row">',
            '</div>'
        ].join('')),

        /** help content */
        helpContent : _.template([
            '<p>', _l([
                'Pair collections are permanent collections containing two datasets: one forward and one reverse. ',
                'Often these are forward and reverse reads. The pair collections can be passed to tools and ',
                'workflows in order to have analyses done on both datasets. This interface allows ',
                'you to create a pair, name it, and swap which is forward and which reverse.'
            ].join( '' )), '</p>',
            '<ul>',
                '<li>', _l([
                    'Click the <i data-target=".swap">"Swap"</i> link to make your forward dataset the reverse ',
                    'and the reverse dataset forward.'
                ].join( '' )), '</li>',
                '<li>', _l([
                    'Click the <i data-target=".cancel-create">"Cancel"</i> button to exit the interface.'
                ].join( '' )), '</li>',
            '</ul><br />',
            '<p>', _l([
                'Once your collection is complete, enter a <i data-target=".collection-name">name</i> and ',
                'click <i data-target=".create-collection">"Create list"</i>.'
            ].join( '' )), '</p>'
        ].join(''))
    }),

    // ------------------------------------------------------------------------ misc
    /** string rep */
    toString : function(){ return 'PairCollectionCreator'; }
});


//==============================================================================
/** List collection flavor of collectionCreatorModal. */
var pairCollectionCreatorModal = function _pairCollectionCreatorModal( elements, options ){
    options = options || {};
    options.title = _l( 'Create a collection from a pair of datasets' );
    return LIST_CREATOR.collectionCreatorModal( elements, options, PairCollectionCreator );
};


//==============================================================================
/** Use a modal to create a pair collection, then add it to the given history contents.
 *  @returns {Deferred} resolved when the collection is added to the history.
 */
function createPairCollection( contents ){
    if( contents.length !== 2 ){
        errorModal(
            'When pairing datasets, select only two datasets: one forward and one reverse.',
            'Not a valid pair'
        );
        return jQuery.Deferred().reject( 'invalid pair' );
    }

    var elements = contents.toJSON(),
        promise = pairCollectionCreatorModal( elements, {
            creationFn : function( elements, name ){
                elements = [
                    { name: "forward", src: "hda", id: elements[0].id },
                    { name: "reverse", src: "hda", id: elements[1].id }
                ];
                return contents.createHDCA( elements, 'paired', name );
            }
        });
    return promise;
}

//==============================================================================
    return {
        PairCollectionCreator       : PairCollectionCreator,
        pairCollectionCreatorModal  : pairCollectionCreatorModal,
        createPairCollection        : createPairCollection,
    };
});
