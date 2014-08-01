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
            //this.log( 'change:object' );
//TODO: prob. better to update the sub-model instead of re-creating it
            this.object = this._createObjectModel();
        });
    },

    _createObjectModel : function(){
        //this.log( '_createObjectModel', this.get( 'object' ), this.object );
        //TODO: same patterns as HDCA _createElementsModel - refactor to BASE_MVC.hasSubModel?
        if( _.isUndefined( this.object ) ){ this.object = null; }
        if( !this.get( 'object' ) ){ return this.object; }

        var object = this.get( 'object' ),
            ObjectClass = this._getObjectClass();
        this.unset( 'object', { silent: true });
        this.object = new ObjectClass( object );

        return this.object;
    },

    _getObjectClass : function(){
        this.debug( 'DCE, element_type:', this.get( 'element_type' ) );
        switch( this.get( 'element_type' ) ){
            case 'dataset_collection':
                return DatasetCollection;
            case 'hda':
                return HDA_MODEL.HistoryDatasetAssociation;
        }
        throw new TypeError( 'Unknown element_type: ' + this.get( 'element_type' ) );
    },

    toJSON : function(){
        var json = Backbone.Model.prototype.toJSON.call( this );
        if( this.object ){
            json.object = this.object.toJSON();
        }
        return json;
    },

    hasDetails : function(){
        return ( this.object !== null
            &&   this.object.hasDetails() );
    },

    /** String representation. */
    toString : function(){
        var objStr = ( this.object )?( '' + this.object ):( this.get( 'element_identifier' ) );
        return ([ 'DatasetCollectionElement(', objStr, ')' ].join( '' ));
    }
});


//==============================================================================
/** @class Backbone model for
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDADCE = DatasetCollectionElement.extend(
/** @lends DatasetCollectionElement.prototype */{

    _getObjectClass : function(){
        return HDA_MODEL.HistoryDatasetAssociation;
    },

    /** String representation. */
    toString : function(){
        var objStr = ( this.object )?( '' + this.object ):( this.get( 'element_identifier' ) );
        return ([ 'HDADCE(', objStr, ')' ].join( '' ));
    }
});


//==============================================================================
/** @class Backbone model for
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DCDCE = DatasetCollectionElement.extend(
/** @lends DatasetCollectionElement.prototype */{

    _getObjectClass : function(){
        return DatasetCollection;
    },

    getVisibleContents : function(){
        return this.object? this.object.getVisibleContents(): [];
    },

    /** String representation. */
    toString : function(){
        var objStr = ( this.object )?( '' + this.object ):( this.get( 'element_identifier' ) );
        return ([ 'DCDCE(', objStr, ')' ].join( '' ));
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
var DCECollection = Backbone.Collection.extend( BASE_MVC.LoggableMixin ).extend(
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
/** @class Backbone collection for
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDADCECollection = DCECollection.extend(
/** @lends DatasetCollectionElementCollection.prototype */{
    model: HDADCE,

    /** String representation. */
    toString : function(){
         return ([ 'HDADCECollection(', this.length, ')' ].join( '' ));
    }
});


//==============================================================================
/** @class Backbone collection for
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var DCDCECollection = DCECollection.extend(
/** @lends DatasetCollectionElementCollection.prototype */{
    model: DCDCE,

    /** String representation. */
    toString : function(){
         return ([ 'DCDCECollection(', this.length, ')' ].join( '' ));
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

    collectionClass : DCECollection,

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

    toJSON : function(){
        var json = Backbone.Model.prototype.toJSON.call( this );
        if( this.elements ){
            json.elements = this.elements.toJSON();
        }
        return json;
    },

    hasDetails : function(){
//TODO: this is incorrect for (accidentally) empty collections
        this.debug( 'hasDetails:', this.elements.length );
        return this.elements.length !== 0;
    },

    getVisibleContents : function( filters ){
        //TODO: filters unused for now
        return this.elements;
    },

    // ........................................................................ misc
    /** String representation */
    toString : function(){
        var idAndName = [ this.get( 'id' ), this.get( 'name' ) || this.get( 'element_identifier' ) ];
        return 'DatasetCollection(' + ( idAndName.join(',') ) + ')';
    }
});


//==============================================================================
var ListDatasetCollection = DatasetCollection.extend(
/** @lends ListDatasetCollection.prototype */{

    collectionClass : HDADCECollection,

    /** String representation. */
    toString : function(){
         return ([ 'ListDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
var PairDatasetCollection = ListDatasetCollection.extend(
/** @lends ListDatasetCollection.prototype */{

    /** String representation. */
    toString : function(){
         return ([ 'PairDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
var ListPairedDatasetCollection = DatasetCollection.extend(
/** @lends ListDatasetCollection.prototype */{

    collectionClass : DCDCECollection,

    // list:paired is the only collection that itself contains collections
    //collectionClass : DatasetCollectionCollection,

    /** String representation. */
    toString : function(){
         return ([ 'ListPairedDatasetCollection(', this.get( 'name' ), ')' ].join( '' ));
    }
});


//==============================================================================
    return {
        //DatasetCollection                   : DatasetCollection,
        ListDatasetCollection               : ListDatasetCollection,
        PairDatasetCollection               : PairDatasetCollection,
        ListPairedDatasetCollection         : ListPairedDatasetCollection
    };
});
