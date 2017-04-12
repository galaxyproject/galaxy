
define([
    "mvc/history/hdca-model",
    "mvc/dataset/states",
    "mvc/base-mvc",
    "mvc/collection/base-creator",
    "mvc/ui/ui-modal",
    "utils/natural-sort",
    "utils/localization",
    "ui/hoverhighlight"
], function( HDCA, STATES, BASE_MVC, baseCreator, UI_MODAL, naturalSort, _l ){

'use strict';

var logNamespace = 'collections';

/*==============================================================================
TODO:
    use proper Element model and not just json
    straighten out createFn, collection.createHDCA
    possibly stop using modals for this
    It would be neat to do a drag and drop

==============================================================================*/
/** A view for both DatasetDCEs and NestedDCDCEs
 *  (things that implement collection-model:DatasetCollectionElementMixin)
 */
var DatasetCollectionElementView = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend({
    _logNamespace : logNamespace,

//TODO: use proper class (DatasetDCE or NestedDCDCE (or the union of both))
    tagName     : 'li',
    className   : 'collection-element',

    initialize : function( attributes ){
        this.element = attributes.element || {};
        this.selected = attributes.selected || false;
    },

    render : function(){
        this.$el
            .attr( 'data-element-id', this.element.id )
            .attr( 'draggable', true )
            .html( this.template({ element: this.element }) );
        if( this.selected ){
            this.$el.addClass( 'selected' );
        }
        return this;
    },

    //TODO: lots of unused space in the element - possibly load details and display them horiz.
    template : _.template([
        '<a class="name" title="', _l( 'Click to rename' ), '" href="javascript:void(0)">',
            '<%- element.name %>',
        '</a>',
        '<button class="discard btn btn-sm" title="', _l( 'Remove this dataset from the list' ), '">',
            _l( 'Discard' ),
        '</button>',
    ].join('')),

    /** select this element and pub */
    select : function( toggle ){
        this.$el.toggleClass( 'selected', toggle );
        this.trigger( 'select', {
            source   : this,
            selected : this.$el.hasClass( 'selected' )
        });
    },

    /** animate the removal of this element and pub */
    discard : function(){
        var view = this,
            parentWidth = this.$el.parent().width();
        this.$el.animate({ 'margin-right' : parentWidth }, 'fast', function(){
            view.trigger( 'discard', {
                source : view
            });
            view.destroy();
        });
    },

    /** remove the DOM and any listeners */
    destroy : function(){
        this.off();
        this.$el.remove();
    },

    events : {
        'click'         : '_click',
        'click .name'   : '_clickName',
        'click .discard': '_clickDiscard',

        'dragstart'     : '_dragstart',
        'dragend'       : '_dragend',
        'dragover'      : '_sendToParent',
        'drop'          : '_sendToParent'
    },

    /** select when the li is clicked */
    _click : function( ev ){
        ev.stopPropagation();
        this.select( ev );
    },

    /** rename a pair when the name is clicked */
    _clickName : function( ev ){
        ev.stopPropagation();
        ev.preventDefault();
        var promptString = [ _l( 'Enter a new name for the element' ), ':\n(',
                             _l( 'Note that changing the name here will not rename the dataset' ), ')' ].join( '' ),
            response = prompt( _l( 'Enter a new name for the element' ) + ':', this.element.name );
        if( response ){
            this.element.name = response;
            this.render();
        }
        //TODO: cancelling with ESC leads to closure of the creator...
    },

    /** discard when the discard button is clicked */
    _clickDiscard : function( ev ){
        ev.stopPropagation();
        this.discard();
    },

    /** dragging pairs for re-ordering */
    _dragstart : function( ev ){
        if( ev.originalEvent ){ ev = ev.originalEvent; }
        ev.dataTransfer.effectAllowed = 'move';
        ev.dataTransfer.setData( 'text/plain', JSON.stringify( this.element ) );

        this.$el.addClass( 'dragging' );
        this.$el.parent().trigger( 'collection-element.dragstart', [ this ] );
    },

    /** dragging for re-ordering */
    _dragend : function( ev ){
        this.$el.removeClass( 'dragging' );
        this.$el.parent().trigger( 'collection-element.dragend', [ this ] );
    },

    /** manually bubble up an event to the parent/container */
    _sendToParent : function( ev ){
        this.$el.parent().trigger( ev );
    },

    /** string rep */
    toString : function(){
        return 'DatasetCollectionElementView()';
    }
});


// ============================================================================
/** An interface for building collections.
 */
var ListCollectionCreator = Backbone.View.extend( BASE_MVC.LoggableMixin ).extend( baseCreator.CollectionCreatorMixin ).extend({
    _logNamespace : logNamespace,

    /** the class used to display individual elements */
    elementViewClass : DatasetCollectionElementView,
    /** the class this creator will create and save */
    collectionClass  : HDCA.HistoryListDatasetCollection,
    className        : 'list-collection-creator collection-creator flex-row-container',

    /** minimum number of valid elements to start with in order to build a collection of this type */
    minElements      : 1,

    defaultAttributes : {
//TODO: remove - use new collectionClass().save()
        /** takes elements and creates the proper collection - returns a promise */
        creationFn : function(){ throw new TypeError( 'no creation fn for creator' ); },
        /** fn to call when the collection is created (scoped to this) */
        oncreate   : function(){},
        /** fn to call when the cancel button is clicked (scoped to this) - if falsy, no btn is displayed */
        oncancel   : function(){},
        /** distance from list edge to begin autoscrolling list */
        autoscrollDist  : 24,
        /** Color passed to hoverhighlight */
        highlightClr    : 'rgba( 64, 255, 255, 1.0 )'
    },

    footerSettings : {
        '.hide-originals': 'hideOriginals'
    },

    /** set up initial options, instance vars, behaviors */
    initialize : function( attributes ){
        this.metric( 'ListCollectionCreator.initialize', attributes );
        var creator = this;
        _.each( this.defaultAttributes, function( value, key ){
            value = attributes[ key ] || value;
            creator[ key ] = value;
        });

        /** unordered, original list - cache to allow reversal */
        creator.initialElements = attributes.elements || [];

        this._setUpCommonSettings( attributes );
        this._instanceSetUp();
        this._elementsSetUp();
        this._setUpBehaviors();
    },

    /** set up instance vars */
    _instanceSetUp : function(){
        /** Ids of elements that have been selected by the user - to preserve over renders */
        this.selectedIds = {};
        /** DOM elements currently being dragged */
        this.$dragging = null;
        /** Used for blocking UI events during ajax/operations (don't post twice) */
        this.blocking = false;
    },

    // ------------------------------------------------------------------------ process raw list
    /** set up main data */
    _elementsSetUp : function(){
        //this.debug( '-- _dataSetUp' );
        /** a list of invalid elements and the reasons they aren't valid */
        this.invalidElements = [];
//TODO: handle fundamental problem of syncing DOM, views, and list here
        /** data for list in progress */
        this.workingElements = [];
        /** views for workingElements */
        this.elementViews = [];

        // copy initial list, sort, add ids if needed
        this.workingElements = this.initialElements.slice( 0 );
        this._ensureElementIds();
        this._validateElements();
        this._mangleDuplicateNames();
        this._sortElements();
    },

    /** add ids to dataset objs in initial list if none */
    _ensureElementIds : function(){
        this.workingElements.forEach( function( element ){
            if( !element.hasOwnProperty( 'id' ) ){
                element.id = _.uniqueId();
            }
        });
        return this.workingElements;
    },

    /** separate working list into valid and invalid elements for this collection */
    _validateElements : function(){
        var creator = this,
            existingNames = {};
        creator.invalidElements = [];

        this.workingElements = this.workingElements.filter( function( element ){
            var problem = creator._isElementInvalid( element );
            if( problem ){
                creator.invalidElements.push({
                    element : element,
                    text    : problem
                });
            }
            return !problem;
        });
        return this.workingElements;
    },

    /** describe what is wrong with a particular element if anything */
    _isElementInvalid : function( element ){
        if( element.history_content_type !== 'dataset' ){
            return _l( "is not a dataset" );
        }
        var validState = element.state === STATES.OK || _.contains( STATES.NOT_READY_STATES, element.state );
        if( ! validState ){
            return _l( "has errored, is paused, or is not accessible" );
        }
        if( element.deleted || element.purged ){
            return _l( "has been deleted or purged" );
        }
        return null;
    },

    /** mangle duplicate names using a mac-like '(counter)' addition to any duplicates */
    _mangleDuplicateNames : function(){
        var SAFETY = 900,
            counter = 1,
            existingNames = {};
        this.workingElements.forEach( function( element ){
            var currName = element.name;
            while( existingNames.hasOwnProperty( currName ) ){
                currName = element.name + ' (' + counter + ')';
                counter += 1;
                if( counter >= SAFETY ){
                    throw new Error( 'Safety hit in while loop - thats impressive' );
                }
            }
            element.name = currName;
            existingNames[ element.name ] = true;
        });
    },

    /** sort a list of elements */
    _sortElements : function( list ){
        // // currently only natural sort by name
        // this.workingElements.sort( function( a, b ){ return naturalSort( a.name, b.name ); });
        // return this.workingElements;
    },

    // ------------------------------------------------------------------------ rendering
    // templates : ListCollectionCreator.templates,
    /** render the entire interface */
    render : function( speed, callback ){
        //this.debug( '-- _render' );
        if( this.workingElements.length < this.minElements ){
            return this._renderInvalid( speed, callback );
        }

        this.$el.empty().html( this.templates.main() );
        this._renderHeader( speed );
        this._renderMiddle( speed );
        this._renderFooter( speed );
        this._addPluginComponents();
        this.$( '.collection-name' ).focus();
        this.trigger( 'rendered', this );
        return this;
    },


    /** render a simplified interface aimed at telling the user why they can't move forward */
    _renderInvalid : function( speed, callback ){
        //this.debug( '-- _render' );
        this.$el.empty().html( this.templates.invalidInitial({
            problems: this.invalidElements,
            elements: this.workingElements,
        }));
        if( typeof this.oncancel === 'function' ){
            this.$( '.cancel-create.btn' ).show();
        }
        this.trigger( 'rendered', this );
        return this;
    },

    /** render the header section */
    _renderHeader : function( speed, callback ){
        var $header = this.$( '.header' ).empty().html( this.templates.header() )
            .find( '.help-content' ).prepend( $( this.templates.helpContent() ) );
        //TODO: should only show once despite calling _renderHeader again
        if( this.invalidElements.length ){
            this._invalidElementsAlert();
        }
        return $header;
    },

    /** render the middle including the elements */
    _renderMiddle : function( speed, callback ){
        var $middle = this.$( '.middle' ).empty().html( this.templates.middle() );
        this._renderList( speed );
        return $middle;
    },

    /** add any jQuery/bootstrap/custom plugins to elements rendered */
    _addPluginComponents : function(){
        this.$( '.help-content i' ).hoverhighlight( '.collection-creator', this.highlightClr );
    },

    /** build and show an alert describing any elements that could not be included due to problems */
    _invalidElementsAlert : function(){
        this._showAlert( this.templates.invalidElements({ problems: this.invalidElements }), 'alert-warning' );
    },

    _disableNameAndCreate : function( disable ){
        disable = !_.isUndefined( disable )? disable : true;
        if( disable ){
            this.$( '.collection-name' ).prop( 'disabled', true );
            this.$( '.create-collection' ).toggleClass( 'disabled', true );
        // } else {
        //     this.$( '.collection-name' ).prop( 'disabled', false );
        //     this.$( '.create-collection' ).removeClass( 'disable' );
        }
    },

    // ------------------------------------------------------------------------ rendering elements
    /** conv. to the main list display DOM */
    $list : function(){
        return this.$( '.collection-elements' );
    },

    /** show or hide the clear selected control based on the num of selected elements */
    _renderClearSelected : function(){
        if( _.size( this.selectedIds ) ){
            this.$( '.collection-elements-controls > .clear-selected' ).show();
        } else {
            this.$( '.collection-elements-controls > .clear-selected' ).hide();
        }
    },

    /** render the elements in order (or a warning if no elements found) */
    _renderList : function( speed, callback ){
        //this.debug( '-- _renderList' );
        var creator = this,
            $tmp = jQuery( '<div/>' ),
            $list = creator.$list();

        _.each( this.elementViews, function( view ){
            view.destroy();
            creator.removeElementView( view );
        });

        // if( !this.workingElements.length ){
        //     this._renderNoValidElements();
        //     return;
        // }

        creator.workingElements.forEach( function( element ){
            var elementView = creator._createElementView( element );
            $tmp.append( elementView.$el );
        });

        creator._renderClearSelected();
        $list.empty().append( $tmp.children() );
        _.invoke( creator.elementViews, 'render' );

        if( $list.height() > $list.css( 'max-height' ) ){
            $list.css( 'border-width', '1px 0px 1px 0px' );
        } else {
            $list.css( 'border-width', '0px' );
        }
    },

    /** create an element view, cache in elementViews, set up listeners, and return */
    _createElementView : function( element ){
        var elementView = new this.elementViewClass({
//TODO: use non-generic class or not all
            // model : COLLECTION.DatasetDCE( element )
            element : element,
            selected: _.has( this.selectedIds, element.id )
        });
        this.elementViews.push( elementView );
        this._listenToElementView( elementView );
        return elementView;
    },

    /** listen to any element events */
    _listenToElementView : function( view ){
        var creator = this;
        creator.listenTo( view, {
            select : function( data ){
                var element = data.source.element;
                if( data.selected ){
                    creator.selectedIds[ element.id ] = true;
                } else {
                    delete creator.selectedIds[ element.id ];
                }
                creator.trigger( 'elements:select', data );
            },
            discard : function( data ){
                creator.trigger( 'elements:discard', data );
            }
        });
    },

    /** add a new element view based on the json in element */
    addElementView : function( element ){
//TODO: workingElements is sorted, add element in appropo index
        // add element, sort elements, find element index
        // var view = this._createElementView( element );
        // return view;
    },

    /** stop listening to view and remove from caches */
    removeElementView : function( view ){
        delete this.selectedIds[ view.element.id ];
        this._renderClearSelected();

        this.elementViews = _.without( this.elementViews, view );
        this.stopListening( view );
    },

    /** render a message in the list that no elements remain to create a collection */
    _renderNoElementsLeft : function(){
        this._disableNameAndCreate( true );
        this.$( '.collection-elements' ).append( this.templates.noElementsLeft() );
    },

    // /** render a message in the list that no valid elements were found to create a collection */
    // _renderNoValidElements : function(){
    //     this._disableNameAndCreate( true );
    //     this.$( '.collection-elements' ).append( this.templates.noValidElements() );
    // },

    // ------------------------------------------------------------------------ API
    /** convert element into JSON compatible with the collections API */
    _elementToJSON : function( element ){
        // return element.toJSON();
        return element;
    },

    /** create the collection via the API
     *  @returns {jQuery.xhr Object} the jquery ajax request
     */
    createList : function( name ){
        if( !this.workingElements.length ){
            var message = _l( 'No valid elements for final list' ) + '. ';
            message += '<a class="cancel-create" href="javascript:void(0);">' + _l( 'Cancel' ) + '</a> ';
            message += _l( 'or' );
            message += ' <a class="reset" href="javascript:void(0);">' + _l( 'start over' ) + '</a>.';
            this._showAlert( message );
            return;
        }

        var creator = this,
            elements = this.workingElements.map( function( element ){
                return creator._elementToJSON( element );
            });

        creator.blocking = true;
        return creator.creationFn( elements, name, creator.hideOriginals )
            .always( function(){
                creator.blocking = false;
            })
            .fail( function( xhr, status, message ){
                creator.trigger( 'error', {
                    xhr     : xhr,
                    status  : status,
                    message : _l( 'An error occurred while creating this collection' )
                });
            })
            .done( function( response, message, xhr ){
                creator.trigger( 'collection:created', response, message, xhr );
                creator.metric( 'collection:created', response );
                if( typeof creator.oncreate === 'function' ){
                    creator.oncreate.call( this, response, message, xhr );
                }
            });
    },

    // ------------------------------------------------------------------------ events
    /** set up event handlers on self */
    _setUpBehaviors : function(){
        this.on( 'error', this._errorHandler );

        this.once( 'rendered', function(){
            this.trigger( 'rendered:initial', this );
        });

        this.on( 'elements:select', function( data ){
            this._renderClearSelected();
        });

        this.on( 'elements:discard', function( data ){
            var element = data.source.element;
            this.removeElementView( data.source );

            this.workingElements = _.without( this.workingElements, element );
            if( !this.workingElements.length ){
                this._renderNoElementsLeft();
            }
        });

        //this.on( 'all', function(){
        //    this.info( arguments );
        //});
        return this;
    },

    /** handle errors with feedback and details to the user (if available) */
    _errorHandler : function( data ){
        this.error( data );

        var creator = this;
            content = data.message || _l( 'An error occurred' );
        if( data.xhr ){
            var xhr = data.xhr,
                message = data.message;
            if( xhr.readyState === 0 && xhr.status === 0 ){
                content += ': ' + _l( 'Galaxy could not be reached and may be updating.' ) +
                    _l( ' Try again in a few minutes.' );
            } else if( xhr.responseJSON ){
                content += ':<br /><pre>' + JSON.stringify( xhr.responseJSON ) + '</pre>';
            } else {
                content += ': ' + message;
            }
        }
        creator._showAlert( content, 'alert-danger' );
    },

    events : {
        // header
        'click .more-help'              : '_clickMoreHelp',
        'click .less-help'              : '_clickLessHelp',
        'click .main-help'              : '_toggleHelp',
        'click .header .alert button'   : '_hideAlert',

        'click .reset'                  : 'reset',
        'click .clear-selected'         : 'clearSelectedElements',

        // elements - selection
        'click .collection-elements'    : 'clearSelectedElements',

        // elements - drop target
        // 'dragenter .collection-elements': '_dragenterElements',
        // 'dragleave .collection-elements': '_dragleaveElements',
        'dragover .collection-elements' : '_dragoverElements',
        'drop .collection-elements'     : '_dropElements',

        // these bubble up from the elements as custom events
        'collection-element.dragstart .collection-elements' : '_elementDragstart',
        'collection-element.dragend   .collection-elements' : '_elementDragend',

        // footer
        'change .collection-name'       : '_changeName',
        'keydown .collection-name'      : '_nameCheckForEnter',
        'change .hide-originals'        : '_changeHideOriginals',
        'click .cancel-create'          : '_cancelCreate',
        'click .create-collection'      : '_clickCreate'//,
    },

    // ........................................................................ elements
    /** reset all data to the initial state */
    reset : function(){
        this._instanceSetUp();
        this._elementsSetUp();
        this.render();
    },

    /** deselect all elements */
    clearSelectedElements : function( ev ){
        this.$( '.collection-elements .collection-element' ).removeClass( 'selected' );
        this.$( '.collection-elements-controls > .clear-selected' ).hide();
    },

    //_dragenterElements : function( ev ){
    //    //this.debug( '_dragenterElements:', ev );
    //},
//TODO: if selected are dragged out of the list area - remove the placeholder - cuz it won't work anyway
    // _dragleaveElements : function( ev ){
    //    //this.debug( '_dragleaveElements:', ev );
    // },

    /** track the mouse drag over the list adding a placeholder to show where the drop would occur */
    _dragoverElements : function( ev ){
        //this.debug( '_dragoverElements:', ev );
        ev.preventDefault();

        var $list = this.$list();
        this._checkForAutoscroll( $list, ev.originalEvent.clientY );
        var $nearest = this._getNearestElement( ev.originalEvent.clientY );

        //TODO: no need to re-create - move instead
        this.$( '.element-drop-placeholder' ).remove();
        var $placeholder = $( '<div class="element-drop-placeholder"></div>' );
        if( !$nearest.length ){
            $list.append( $placeholder );
        } else {
            $nearest.before( $placeholder );
        }
    },

    /** If the mouse is near enough to the list's top or bottom, scroll the list */
    _checkForAutoscroll : function( $element, y ){
        var AUTOSCROLL_SPEED = 2,
            offset = $element.offset(),
            scrollTop = $element.scrollTop(),
            upperDist = y - offset.top,
            lowerDist = ( offset.top + $element.outerHeight() ) - y;
        if( upperDist >= 0 && upperDist < this.autoscrollDist ){
            $element.scrollTop( scrollTop - AUTOSCROLL_SPEED );
        } else if( lowerDist >= 0 && lowerDist < this.autoscrollDist ){
            $element.scrollTop( scrollTop + AUTOSCROLL_SPEED );
        }
    },

    /** get the nearest element based on the mouse's Y coordinate.
     *  If the y is at the end of the list, return an empty jQuery object.
     */
    _getNearestElement : function( y ){
        var WIGGLE = 4,
            lis = this.$( '.collection-elements li.collection-element' ).toArray();
        for( var i=0; i<lis.length; i++ ){
            var $li = $( lis[i] ),
                top = $li.offset().top,
                halfHeight = Math.floor( $li.outerHeight() / 2 ) + WIGGLE;
            if( top + halfHeight > y && top - halfHeight < y ){
                return $li;
            }
        }
        return $();
    },

    /** drop (dragged/selected elements) onto the list, re-ordering the internal list */
    _dropElements : function( ev ){
        if( ev.originalEvent ){ ev = ev.originalEvent; }
        // both required for firefox
        ev.preventDefault();
        ev.dataTransfer.dropEffect = 'move';

        // insert before the nearest element or after the last.
        var $nearest = this._getNearestElement( ev.clientY );
        if( $nearest.length ){
            this.$dragging.insertBefore( $nearest );
        } else {
            // no nearest before - insert after last element
            this.$dragging.insertAfter( this.$( '.collection-elements .collection-element' ).last() );
        }
        // resync the creator's list based on the new DOM order
        this._syncOrderToDom();
        return false;
    },

    /** resync the creator's list of elements based on the DOM order */
    _syncOrderToDom : function(){
        var creator = this,
            newElements = [];
        //TODO: doesn't seem wise to use the dom to store these - can't we sync another way?
        this.$( '.collection-elements .collection-element' ).each( function(){
            var id = $( this ).attr( 'data-element-id' ),
                element = _.findWhere( creator.workingElements, { id: id });
            if( element ){
                newElements.push( element );
            } else {
                console.error( 'missing element: ', id );
            }
        });
        this.workingElements = newElements;
        this._renderList();
    },

    /** drag communication with element sub-views: dragstart */
    _elementDragstart : function( ev, element ){
        // auto select the element causing the event and move all selected
        element.select( true );
        this.$dragging = this.$( '.collection-elements .collection-element.selected' );
    },

    /** drag communication with element sub-views: dragend - remove the placeholder */
    _elementDragend : function( ev, element ){
        $( '.element-drop-placeholder' ).remove();
        this.$dragging = null;
    },

    // ------------------------------------------------------------------------ templates
    //TODO: move to require text plugin and load these as text
    //TODO: underscore currently unnecc. bc no vars are used
    //TODO: better way of localizing text-nodes in long strings
    /** underscore template fns attached to class */
    templates : _.extend({}, baseCreator.CollectionCreatorMixin._creatorTemplates, {

        /** the header (not including help text) */
        header : _.template([
            '<div class="main-help well clear">',
                '<a class="more-help" href="javascript:void(0);">', _l( 'More help' ), '</a>',
                '<div class="help-content">',
                    '<a class="less-help" href="javascript:void(0);">', _l( 'Less' ), '</a>',
                '</div>',
            '</div>',
            '<div class="alert alert-dismissable">',
                '<button type="button" class="close" data-dismiss="alert" ',
                    'title="', _l( 'Close and show more help' ), '" aria-hidden="true">&times;</button>',
                '<span class="alert-message"></span>',
            '</div>',
        ].join('')),

        /** the middle: element list */
        middle : _.template([
            '<div class="collection-elements-controls">',
                '<a class="reset" href="javascript:void(0);" ',
                    'title="', _l( 'Undo all reordering and discards' ), '">',
                    _l( 'Start over' ),
                '</a>',
                '<a class="clear-selected" href="javascript:void(0);" ',
                    'title="', _l( 'De-select all selected datasets' ), '">',
                    _l( 'Clear selected' ),
                '</a>',
            '</div>',
            '<div class="collection-elements scroll-container flex-row">',
            '</div>'
        ].join('')),

        /** creation and cancel controls */
        footer : _.template([
            '<div class="attributes clear">',
                '<div class="clear">',
                    '<label class="setting-prompt pull-right">',
                        _l( 'Hide original elements' ), '?',
                        '<input class="hide-originals pull-right" type="checkbox" />',
                    '</label>',
                '</div>',
                '<div class="clear">',
                    '<input class="collection-name form-control pull-right" ',
                        'placeholder="', _l( 'Enter a name for your new collection' ), '" />',
                    '<div class="collection-name-prompt pull-right">', _l( 'Name' ), ':</div>',
                '</div>',
            '</div>',

            '<div class="actions clear vertically-spaced">',
                '<div class="other-options pull-left">',
                    '<button class="cancel-create btn" tabindex="-1">', _l( 'Cancel' ), '</button>',
                    '<div class="create-other btn-group dropup">',
                        '<button class="btn btn-default dropdown-toggle" data-toggle="dropdown">',
                              _l( 'Create a different kind of collection' ),
                              ' <span class="caret"></span>',
                        '</button>',
                        '<ul class="dropdown-menu" role="menu">',
                              '<li><a href="#">', _l( 'Create a <i>single</i> pair' ), '</a></li>',
                              '<li><a href="#">', _l( 'Create a list of <i>unpaired</i> datasets' ), '</a></li>',
                        '</ul>',
                    '</div>',
                '</div>',

                '<div class="main-options pull-right">',
                    '<button class="create-collection btn btn-primary">', _l( 'Create list' ), '</button>',
                '</div>',
            '</div>'
        ].join('')),

        /** help content */
        helpContent : _.template([
            '<p>', _l([
                'Collections of datasets are permanent, ordered lists of datasets that can be passed to tools and ',
                'workflows in order to have analyses done on each member of the entire group. This interface allows ',
                'you to create a collection and re-order the final collection.'
            ].join( '' )), '</p>',
            '<ul>',
                '<li>', _l([
                    'Rename elements in the list by clicking on ',
                    '<i data-target=".collection-element .name">the existing name</i>.'
                ].join( '' )), '</li>',
                '<li>', _l([
                    'Discard elements from the final created list by clicking on the ',
                    '<i data-target=".collection-element .discard">"Discard"</i> button.'
                ].join( '' )), '</li>',
                '<li>', _l([
                    'Reorder the list by clicking and dragging elements. Select multiple elements by clicking on ',
                    '<i data-target=".collection-element">them</i> and you can then move those selected by dragging the ',
                    'entire group. Deselect them by clicking them again or by clicking the ',
                    'the <i data-target=".clear-selected">"Clear selected"</i> link.'
                ].join( '' )), '</li>',
                '<li>', _l([
                    'Click the <i data-target=".reset">"Start over"</i> link to begin again as if you had just opened ',
                    'the interface.'
                ].join( '' )), '</li>',
                '<li>', _l([
                    'Click the <i data-target=".cancel-create">"Cancel"</i> button to exit the interface.'
                ].join( '' )), '</li>',
            '</ul><br />',
            '<p>', _l([
                'Once your collection is complete, enter a <i data-target=".collection-name">name</i> and ',
                'click <i data-target=".create-collection">"Create list"</i>.'
            ].join( '' )), '</p>'
        ].join('')),

        /** shown in list when all elements are discarded */
        invalidElements : _.template([
            _l( 'The following selections could not be included due to problems:' ),
            '<ul><% _.each( problems, function( problem ){ %>',
                '<li><b><%- problem.element.name %></b>: <%- problem.text %></li>',
            '<% }); %></ul>'
        ].join('')),

        /** shown in list when all elements are discarded */
        noElementsLeft : _.template([
            '<li class="no-elements-left-message">',
                _l( 'No elements left! ' ),
                _l( 'Would you like to ' ), '<a class="reset" href="javascript:void(0)">', _l( 'start over' ), '</a>?',
            '</li>'
        ].join('')),

        /** a simplified page communicating what went wrong and why the user needs to reselect something else */
        invalidInitial : _.template([
            '<div class="header flex-row no-flex">',
                '<div class="alert alert-warning" style="display: block">',
                    '<span class="alert-message">',
                        '<% if( _.size( problems ) ){ %>',
                            _l( 'The following selections could not be included due to problems' ), ':',
                            '<ul><% _.each( problems, function( problem ){ %>',
                                '<li><b><%- problem.element.name %></b>: <%- problem.text %></li>',
                            '<% }); %></ul>',
                        '<% } else if( _.size( elements ) < 1 ){ %>',
                            _l( 'No datasets were selected' ), '.',
                        '<% } %>',
                        '<br />',
                        _l( 'At least one element is needed for the collection' ), '. ',
                        _l( 'You may need to ' ),
                        '<a class="cancel-create" href="javascript:void(0)">', _l( 'cancel' ), '</a> ',
                        _l( 'and reselect new elements' ), '.',
                    '</span>',
                '</div>',
            '</div>',
            '<div class="footer flex-row no-flex">',
                '<div class="actions clear vertically-spaced">',
                    '<div class="other-options pull-left">',
                        '<button class="cancel-create btn" tabindex="-1">', _l( 'Cancel' ), '</button>',
                        // _l( 'Create a different kind of collection' ),
                    '</div>',
                '</div>',
            '</div>'
        ].join('')),
    }),

    // ------------------------------------------------------------------------ misc
    /** string rep */
    toString : function(){ return 'ListCollectionCreator'; }
});



//=============================================================================
/** Create a modal and load its body with the given CreatorClass creator type
 *  @returns {Deferred} resolved when creator has built a collection.
 */
var collectionCreatorModal = function _collectionCreatorModal( elements, options, CreatorClass ){

    var deferred = jQuery.Deferred(),
        modal = Galaxy.modal || ( new UI_MODAL.View() ),
        creator;

    options = _.defaults( options || {}, {
        elements    : elements,
        oncancel    : function(){
            modal.hide();
            deferred.reject( 'cancelled' );
        },
        oncreate    : function( creator, response ){
            modal.hide();
            deferred.resolve( response );
        }
    });

    creator = new CreatorClass( options );
    modal.show({
        title   : options.title || _l( 'Create a collection' ),
        body    : creator.$el,
        width   : '80%',
        height  : '100%',
        closing_events: true
    });
    creator.render();
    window._collectionCreator = creator;

    //TODO: remove modal header
    return deferred;
};

/** List collection flavor of collectionCreatorModal. */
var listCollectionCreatorModal = function _listCollectionCreatorModal( elements, options ){
    options = options || {};
    options.title = _l( 'Create a collection from a list of datasets' );
    return collectionCreatorModal( elements, options, ListCollectionCreator );
};


//==============================================================================
/** Use a modal to create a list collection, then add it to the given history contents.
 *  @returns {Deferred} resolved when the collection is added to the history.
 */
function createListCollection( contents, defaultHideSourceItems ){
    var elements = contents.toJSON(),
        promise = listCollectionCreatorModal( elements, {
            defaultHideSourceItems: defaultHideSourceItems,
            creationFn : function( elements, name, hideSourceItems ){
                elements = elements.map( function( element ){
                    return {
                        id      : element.id,
                        name    : element.name,
                        //TODO: this allows for list:list even if the filter above does not - reconcile
                        src     : ( element.history_content_type === 'dataset'? 'hda' : 'hdca' )
                    };
                });
                return contents.createHDCA( elements, 'list', name, hideSourceItems );
            }
        });
    return promise;
}

//==============================================================================
    return {
        DatasetCollectionElementView: DatasetCollectionElementView,
        ListCollectionCreator       : ListCollectionCreator,

        collectionCreatorModal      : collectionCreatorModal,
        listCollectionCreatorModal  : listCollectionCreatorModal,
        createListCollection        : createListCollection
    };
});
