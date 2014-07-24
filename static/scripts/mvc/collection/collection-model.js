define([
    "mvc/dataset/hda-model",
    "mvc/base-mvc",
    "utils/localization"
], function( HDA_MODEL, BASE_MVC, _l ){
//==============================================================================
/** @class Backbone model for Dataset collection elements.
 *      DC Elements contain a sub-model named 'object'. This class moves that
 *      'object' from the JSON in the attributes list to a full, instantiated
 *      sub-model found in this.object. This is done on intialization and
 *      everytime the 'change:object' event is fired.
 *
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DatasetCollectionElement = Backbone.Model.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends DatasetCollectionElement.prototype */{
    //TODO:?? this model may be unneccessary - it reflects the api structure, but...
    //  if we munge the element with the element.object at parse, we can flatten the entire hierarchy

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    defaults : {
        id                  : null,
        model_class         : 'DatasetCollectionElement',
        element_identifier  : null,
        element_index       : null,
        element_type        : null
    },

    /** Set up.
     *  @see Backbone.Collection#initialize
     */
    initialize : function( model, options ){
        this.info( this + '.initialize:', model, options );
        options = options || {};
        //this._setUpListeners();

        this.object = this._createObjectModel();
        this.on( 'change:object', function(){
            //console.log( 'change:object' );
//TODO: prob. better to update the sub-model instead of re-creating it
            this.object = this._createObjectModel();
        });
    },

    _createObjectModel : function(){
        //console.log( '_createObjectModel', this.get( 'object' ), this.object );
        //TODO: same patterns as HDCA _createElementsModel - refactor to BASE_MVC.hasSubModel?
        if( _.isUndefined( this.object ) ){ this.object = null; }
        if( !this.get( 'object' ) ){ return this.object; }

        var object = this.get( 'object' );
        this.unset( 'object', { silent: true });

        this.debug( 'DCE, element_type:', this.get( 'element_type' ) );
        switch( this.get( 'element_type' ) ){
            case 'dataset_collection':
                this.object = new DatasetCollection( object );
                break;
            case 'hda':
                this.object = new HDA_MODEL.HistoryDatasetAssociation( object );
                break;
            default:
                throw new TypeError( 'Unknown element_type: ' + this.get( 'element_type' ) );
        }
        return this.object;
    },

    /** String representation. */
    toString : function(){
        var objStr = ( this.object )?( '' + this.object ):( this.get( 'element_identifier' ) );
        return ([ 'DatasetCollectionElement(', objStr, ')' ].join( '' ));
    }
});


//==============================================================================
/** @class Backbone collection for DCEs.
 *      NOTE: used *only* in second level of list:paired collections (a
 *      collection that contains collections)
 *
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DatasetCollectionElementCollection = Backbone.Collection.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends DatasetCollectionElementCollection.prototype */{
    model: DatasetCollectionElement,

    // comment this out to suppress log output
    /** logger used to record this.log messages, commonly set to console */
    //logger              : console,

    /** Set up.
     *  @see Backbone.Collection#initialize
     */
    initialize : function( models, options ){
        options = options || {};
        this.info( this + '.initialize:', models, options );
        //this._setUpListeners();
    },

    /** String representation. */
    toString : function(){
         return ([ 'DatasetCollectionElementCollection(', this.length, ')' ].join( '' ));
    }
});


//==============================================================================
/** @class Backbone model for Dataset Collections.
 *      DCs contain a bbone collection named 'elements' using the class found in
 *      this.collectionClass (gen. DatasetCollectionElementCollection). DCs move
 *      that 'object' from the JSON in the attributes list to a full, instantiated
 *      collection found in this.elements. This is done on intialization and
 *      everytime the 'change:elements' event is fired.
 *
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DatasetCollection = Backbone.Model.extend( BASE_MVC.LoggableMixin ).extend(
/** @lends ListDatasetCollection.prototype */{

    //logger : console,

    /** default attributes for a model */
    defaults : {
        collection_type     : 'list'
    },

    collectionClass : DatasetCollectionElementCollection,

    /**  */
    initialize : function( model, options ){
        this.info( 'DatasetCollection.initialize:', model, options );
        //historyContent.HistoryContent.prototype.initialize.call( this, attrs, options );
        this.elements = this._createElementsModel();
//TODO:?? no way to use parse here?
        this.on( 'change:elements', function(){
            this.log( 'change:elements' );
//TODO: prob. better to update the collection instead of re-creating it
            this.elements = this._createElementsModel();
        });
    },

    /** move elements model attribute to full collection */
    _createElementsModel : function(){
        this.log( '_createElementsModel', this.get( 'elements' ), this.elements );
//TODO: same patterns as DatasetCollectionElement _createObjectModel - refactor to BASE_MVC.hasSubModel?
        var elements = this.get( 'elements' ) || [];
        this.info( 'elements:', elements );
        this.unset( 'elements', { silent: true });
        this.elements = new this.collectionClass( elements );
        return this.elements;
    },

    hasDetails : function(){
//TODO: this is incorrect for (accidentally) empty collections
        return this.elements.length !== 0;
    },

    // ........................................................................ misc
    /** String representation */
    toString : function(){
        var idAndName = [ this.get( 'id' ), this.get( 'name' ) || this.get( 'element_identifier' ) ];
        return 'DatasetCollection(' + ( idAndName.join(',') ) + ')';
    }
});


//==============================================================================
/** @class Backbone collection for a collection of collection collections collecting correctly.  */
var DatasetCollectionCollection = Backbone.Collection.extend( BASE_MVC.LoggableMixin ).extend({

    model: DatasetCollection,

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    /** Set up.
     *  @see Backbone.Collection#initialize
     */
    initialize : function( models, options ){
        options = options || {};
        this.info( 'DatasetCollectionCollection.initialize:', models, options );
        //this._setUpListeners();
    },

    /** String representation. */
    toString : function(){
         return ([ 'DatasetCollectionCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//NOTE: the following prototypes may not be necessary - but I wanted to specifiy
//  them (for now) and allow for the possibility of unique functionality
//==============================================================================
var ListDatasetCollection = DatasetCollection.extend(
/** @lends ListDatasetCollection.prototype */{

    /** String representation. */
    toString : function(){
         return ([ 'ListDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
var PairDatasetCollection = DatasetCollection.extend(
/** @lends ListDatasetCollection.prototype */{

    /** String representation. */
    toString : function(){
         return ([ 'PairDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
var ListPairedDatasetCollection = DatasetCollection.extend(
/** @lends ListDatasetCollection.prototype */{

    // list:paired is the only collection that itself contains collections
    //collectionClass : DatasetCollectionCollection,

    /** String representation. */
    toString : function(){
         return ([ 'ListPairedDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
    return {
        DatasetCollectionElement            : DatasetCollectionElement,
        DatasetCollectionElementCollection  : DatasetCollectionElementCollection,
        DatasetCollection                   : DatasetCollection,
        DatasetCollectionCollection         : DatasetCollectionCollection,
        ListDatasetCollection               : ListDatasetCollection,
        PairDatasetCollection               : PairDatasetCollection,
        ListPairedDatasetCollection         : ListPairedDatasetCollection
    };
});
