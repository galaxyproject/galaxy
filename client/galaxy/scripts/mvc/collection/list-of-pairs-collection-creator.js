define([
    "utils/levenshtein",
    "utils/natural-sort",
    "mvc/collection/base-creator",
    "mvc/base-mvc",
    "utils/localization",
    "ui/hoverhighlight"
], function( levenshteinDistance, naturalSort, baseCreator, baseMVC, _l ){

'use strict';

var logNamespace = 'collections';
/* ============================================================================
TODO:


PROGRAMMATICALLY:
currPanel.once( 'rendered', function(){
    currPanel.showSelectors();
    currPanel.selectAll();
    _.last( currPanel.actionsPopup.options ).func();
});

============================================================================ */
/** A view for paired datasets in the collections creator.
 */
var PairView = Backbone.View.extend( baseMVC.LoggableMixin ).extend({
    _logNamespace : logNamespace,

    tagName     : 'li',
    className   : 'dataset paired',

    initialize : function( attributes ){
        this.pair = attributes.pair || {};
    },

    template : _.template([
        '<span class="forward-dataset-name flex-column"><%- pair.forward.name %></span>',
        '<span class="pair-name-column flex-column">',
            '<span class="pair-name"><%- pair.name %></span>',
        '</span>',
        '<span class="reverse-dataset-name flex-column"><%- pair.reverse.name %></span>'
    ].join('')),

    render : function(){
        this.$el
            .attr( 'draggable', true )
            .data( 'pair', this.pair )
            .html( this.template({ pair: this.pair }) )
            .addClass( 'flex-column-container' );
        return this;
    },

    events : {
        'dragstart'         : '_dragstart',
        'dragend'           : '_dragend',
        'dragover'          : '_sendToParent',
        'drop'              : '_sendToParent'
    },

    /** dragging pairs for re-ordering */
    _dragstart : function( ev ){
        ev.currentTarget.style.opacity = '0.4';
        if( ev.originalEvent ){ ev = ev.originalEvent; }

        ev.dataTransfer.effectAllowed = 'move';
        ev.dataTransfer.setData( 'text/plain', JSON.stringify( this.pair ) );

        this.$el.parent().trigger( 'pair.dragstart', [ this ] );
    },

    /** dragging pairs for re-ordering */
    _dragend : function( ev ){
        ev.currentTarget.style.opacity = '1.0';
        this.$el.parent().trigger( 'pair.dragend', [ this ] );
    },

    /** manually bubble up an event to the parent/container */
    _sendToParent : function( ev ){
        this.$el.parent().trigger( ev );
    },

    /** string rep */
    toString : function(){
        return 'PairView(' + this.pair.name + ')';
    }
});


// ============================================================================
/** returns an autopair function that uses the provided options.match function */
function autoPairFnBuilder( options ){
    options = options || {};
    options.createPair = options.createPair || function _defaultCreatePair( params ){
        params = params || {};
        var a = params.listA.splice( params.indexA, 1 )[0],
            b = params.listB.splice( params.indexB, 1 )[0],
            aInBIndex = params.listB.indexOf( a ),
            bInAIndex = params.listA.indexOf( b );
        if( aInBIndex !== -1 ){ params.listB.splice( aInBIndex, 1 ); }
        if( bInAIndex !== -1 ){ params.listA.splice( bInAIndex, 1 ); }
        return this._pair( a, b, { silent: true });
    };
    // compile these here outside of the loop
    var _regexps = [];
    function getRegExps(){
        if( !_regexps.length ){
            _regexps = [
                new RegExp( this.filters[0] ),
                new RegExp( this.filters[1] )
            ];
        }
        return _regexps;
    }
    // mangle params as needed
    options.preprocessMatch = options.preprocessMatch || function _defaultPreprocessMatch( params ){
        var regexps = getRegExps.call( this );
        return _.extend( params, {
            matchTo     : params.matchTo.name.replace( regexps[0], '' ),
            possible    : params.possible.name.replace( regexps[1], '' )
        });
    };

    return function _strategy( params ){
        this.debug( 'autopair _strategy ---------------------------' );
        params = params || {};
        var listA = params.listA,
            listB = params.listB,
            indexA = 0, indexB,
            bestMatch = {
                score : 0.0,
                index : null
            },
            paired = [];
        //console.debug( 'params:', JSON.stringify( params, null, '  ' ) );
        this.debug( 'starting list lens:', listA.length, listB.length );
        this.debug( 'bestMatch (starting):', JSON.stringify( bestMatch, null, '  ' ) );

        while( indexA < listA.length ){
            var matchTo = listA[ indexA ];
            bestMatch.score = 0.0;

            for( indexB=0; indexB<listB.length; indexB++ ){
                var possible = listB[ indexB ];
                this.debug( indexA + ':' + matchTo.name );
                this.debug( indexB + ':' + possible.name );

                // no matching with self
                if( listA[ indexA ] !== listB[ indexB ] ){
                    bestMatch = options.match.call( this, options.preprocessMatch.call( this, {
                        matchTo : matchTo,
                        possible: possible,
                        index   : indexB,
                        bestMatch : bestMatch
                    }));
                    this.debug( 'bestMatch:', JSON.stringify( bestMatch, null, '  ' ) );
                    if( bestMatch.score === 1.0 ){
                        this.debug( 'breaking early due to perfect match' );
                        break;
                    }
                }
            }
            var scoreThreshold = options.scoreThreshold.call( this );
            this.debug( 'scoreThreshold:', scoreThreshold );
            this.debug( 'bestMatch.score:', bestMatch.score );

            if( bestMatch.score >= scoreThreshold ){
                //console.debug( 'autoPairFnBuilder.strategy', listA[ indexA ].name, listB[ bestMatch.index ].name );
                paired.push( options.createPair.call( this, {
                    listA   : listA,
                    indexA  : indexA,
                    listB   : listB,
                    indexB  : bestMatch.index
                }));
                //console.debug( 'list lens now:', listA.length, listB.length );
            } else {
                indexA += 1;
            }
            if( !listA.length || !listB.length ){
                return paired;
            }
        }
        this.debug( 'paired:', JSON.stringify( paired, null, '  ' ) );
        this.debug( 'autopair _strategy ---------------------------' );
        return paired;
    };
}


// ============================================================================
/** An interface for building collections of paired datasets.
 */
var PairedCollectionCreator = Backbone.View.extend( baseMVC.LoggableMixin ).extend( baseCreator.CollectionCreatorMixin ).extend({
    _logNamespace : logNamespace,

    className: 'list-of-pairs-collection-creator collection-creator flex-row-container',

    /** set up initial options, instance vars, behaviors, and autopair (if set to do so) */
    initialize : function( attributes ){
        this.metric( 'PairedCollectionCreator.initialize', attributes );
        //this.debug( '-- PairedCollectionCreator:', attributes );

        attributes = _.defaults( attributes, {
            datasets            : [],
            filters             : this.DEFAULT_FILTERS,
            automaticallyPair   : true,
            strategy            : 'lcs',
            matchPercentage     : 0.9,
            twoPassAutopairing  : true
        });

        /** unordered, original list */
        this.initialList = attributes.datasets;

        /** is this from a history? if so, what's its id? */
        this.historyId = attributes.historyId;

        /** which filters should be used initially? (String[2] or name in commonFilters) */
        this.filters = this.commonFilters[ attributes.filters ] || this.commonFilters[ this.DEFAULT_FILTERS ];
        if( _.isArray( attributes.filters ) ){
            this.filters = attributes.filters;
        }

        /** try to auto pair the unpaired datasets on load? */
        this.automaticallyPair = attributes.automaticallyPair;

        /** what method to use for auto pairing (will be passed aggression level) */
        this.strategy = this.strategies[ attributes.strategy ] || this.strategies[ this.DEFAULT_STRATEGY ];
        if( _.isFunction( attributes.strategy ) ){
            this.strategy = attributes.strategy;
        }

        /** distance/mismatch level allowed for autopairing */
        this.matchPercentage = attributes.matchPercentage;

        /** try to autopair using simple first, then this.strategy on the remainder */
        this.twoPassAutopairing = attributes.twoPassAutopairing;

        /** remove file extensions (\.*) from created pair names? */
        this.removeExtensions = true;
        //this.removeExtensions = false;

        /** fn to call when the cancel button is clicked (scoped to this) - if falsy, no btn is displayed */
        this.oncancel = attributes.oncancel;
        /** fn to call when the collection is created (scoped to this) */
        this.oncreate = attributes.oncreate;

        /** fn to call when the cancel button is clicked (scoped to this) - if falsy, no btn is displayed */
        this.autoscrollDist = attributes.autoscrollDist || 24;

        /** is the unpaired panel shown? */
        this.unpairedPanelHidden = false;
        /** is the paired panel shown? */
        this.pairedPanelHidden = false;

        /** DOM elements currently being dragged */
        this.$dragging = null;

        /** Used for blocking UI events during ajax/operations (don't post twice) */
        this.blocking = false;

        this._setUpCommonSettings( attributes );
        this._setUpBehaviors();
        this._dataSetUp();
    },

    /** map of common filter pairs by name */
    commonFilters : {
        illumina        : [ '_1', '_2' ],
        Rs              : [ '_R1', '_R2' ]
    },
    /** which commonFilter to use by default */
    DEFAULT_FILTERS : 'illumina',

    /** map of name->fn for autopairing */
    strategies : {
        'simple'        : 'autopairSimple',
        'lcs'           : 'autopairLCS',
        'levenshtein'   : 'autopairLevenshtein'
    },
    /** default autopair strategy name */
    DEFAULT_STRATEGY : 'lcs',

    // ------------------------------------------------------------------------ process raw list
    /** set up main data: cache initialList, sort, and autopair */
    _dataSetUp : function(){
        //this.debug( '-- _dataSetUp' );

        this.paired = [];
        this.unpaired = [];

        this.selectedIds = [];

        // sort initial list, add ids if needed, and save new working copy to unpaired
        this._sortInitialList();
        this._ensureIds();
        this.unpaired = this.initialList.slice( 0 );

        if( this.automaticallyPair ){
            this.autoPair();
            this.once( 'rendered:initial', function(){
                this.trigger( 'autopair' );
            });
        }
    },

    /** sort initial list */
    _sortInitialList : function(){
        //this.debug( '-- _sortInitialList' );
        this._sortDatasetList( this.initialList );
    },

    /** sort a list of datasets */
    _sortDatasetList : function( list ){
        // currently only natural sort by name
        list.sort( function( a, b ){ return naturalSort( a.name, b.name ); });
        return list;
    },

    /** add ids to dataset objs in initial list if none */
    _ensureIds : function(){
        this.initialList.forEach( function( dataset ){
            if( !dataset.hasOwnProperty( 'id' ) ){
                dataset.id = _.uniqueId();
            }
        });
        return this.initialList;
    },

    /** split initial list into two lists, those that pass forward filters & those passing reverse */
    _splitByFilters : function(){
        var regexFilters = this.filters.map( function( stringFilter ){
                return new RegExp( stringFilter );
            }),
            split = [ [], [] ];

        function _filter( unpaired, filter ){
            return filter.test( unpaired.name );
            //return dataset.name.indexOf( filter ) >= 0;
        }
        this.unpaired.forEach( function _filterEach( unpaired ){
            // 90% of the time this seems to work, but:
            //TODO: this treats *all* strings as regex which may confuse people - possibly check for // surrounding?
            //  would need explanation in help as well
            regexFilters.forEach( function( filter, i ){
                if( _filter( unpaired, filter ) ){
                    split[i].push( unpaired );
                }
            });
        });
        return split;
    },

    /** add a dataset to the unpaired list in it's proper order */
    _addToUnpaired : function( dataset ){
        // currently, unpaired is natural sorted by name, use binary search to find insertion point
        var binSearchSortedIndex = function( low, hi ){
            if( low === hi ){ return low; }

            var mid = Math.floor( ( hi - low ) / 2 ) + low,
                compared = naturalSort( dataset.name, this.unpaired[ mid ].name );

            if( compared < 0 ){
                return binSearchSortedIndex( low, mid );
            } else if( compared > 0 ){
                return binSearchSortedIndex( mid + 1, hi );
            }
            // walk the equal to find the last
            while( this.unpaired[ mid ] && this.unpaired[ mid ].name === dataset.name ){ mid++; }
            return mid;

        }.bind( this );

        this.unpaired.splice( binSearchSortedIndex( 0, this.unpaired.length ), 0, dataset );
    },

    // ------------------------------------------------------------------------ auto pairing
    /** two passes to automatically create pairs:
     *  use both simpleAutoPair, then the fn mentioned in strategy
     */
    autoPair : function( strategy ){
        // split first using exact matching
        var split = this._splitByFilters(),
            paired = [];
        if( this.twoPassAutopairing ){
            paired = this.autopairSimple({
                listA : split[0],
                listB : split[1]
            });
            split = this._splitByFilters();
        }

        // uncomment to see printlns while running tests
        //this.debug = function(){ console.log.apply( console, arguments ); };

        // then try the remainder with something less strict
        strategy = strategy || this.strategy;
        split = this._splitByFilters();
        paired = paired.concat( this[ strategy ].call( this, {
            listA : split[0],
            listB : split[1]
        }));
        return paired;
    },

    /** autopair by exact match */
    autopairSimple : autoPairFnBuilder({
        scoreThreshold: function(){ return 1.0; },
        match : function _match( params ){
            params = params || {};
            if( params.matchTo === params.possible ){
                return {
                    index: params.index,
                    score: 1.0
                };
            }
            return params.bestMatch;
        }
    }),

    /** autopair by levenshtein edit distance scoring */
    autopairLevenshtein : autoPairFnBuilder({
        scoreThreshold: function(){ return this.matchPercentage; },
        match : function _matches( params ){
            params = params || {};
            var distance = levenshteinDistance( params.matchTo, params.possible ),
                score = 1.0 - ( distance / ( Math.max( params.matchTo.length, params.possible.length ) ) );
            if( score > params.bestMatch.score ){
                return {
                    index: params.index,
                    score: score
                };
            }
            return params.bestMatch;
        }
    }),

    /** autopair by longest common substrings scoring */
    autopairLCS : autoPairFnBuilder({
        scoreThreshold: function(){ return this.matchPercentage; },
        match : function _matches( params ){
            params = params || {};
            var match = this._naiveStartingAndEndingLCS( params.matchTo, params.possible ).length,
                score = match / ( Math.max( params.matchTo.length, params.possible.length ) );
            if( score > params.bestMatch.score ){
                return {
                    index: params.index,
                    score: score
                };
            }
            return params.bestMatch;
        }
    }),

    /** return the concat'd longest common prefix and suffix from two strings */
    _naiveStartingAndEndingLCS : function( s1, s2 ){
        var fwdLCS = '',
            revLCS = '',
            i = 0, j = 0;
        while( i < s1.length && i < s2.length ){
            if( s1[ i ] !== s2[ i ] ){
                break;
            }
            fwdLCS += s1[ i ];
            i += 1;
        }
        if( i === s1.length ){ return s1; }
        if( i === s2.length ){ return s2; }

        i = ( s1.length - 1 );
        j = ( s2.length - 1 );
        while( i >= 0 && j >= 0 ){
            if( s1[ i ] !== s2[ j ] ){
                break;
            }
            revLCS = [ s1[ i ], revLCS ].join( '' );
            i -= 1;
            j -= 1;
        }
        return fwdLCS + revLCS;
    },

    // ------------------------------------------------------------------------ pairing / unpairing
    /** create a pair from fwd and rev, removing them from unpaired, and placing the new pair in paired */
    _pair : function( fwd, rev, options ){
        options = options || {};
        this.debug( '_pair:', fwd, rev );
        var pair = this._createPair( fwd, rev, options.name );
        this.paired.push( pair );
        this.unpaired = _.without( this.unpaired, fwd, rev );
        if( !options.silent ){
            this.trigger( 'pair:new', pair );
        }
        return pair;
    },

    /** create a pair Object from fwd and rev, adding the name attribute (will guess if not given) */
    _createPair : function( fwd, rev, name ){
        // ensure existance and don't pair something with itself
        if( !( fwd && rev ) || ( fwd === rev ) ){
            throw new Error( 'Bad pairing: ' + [ JSON.stringify( fwd ), JSON.stringify( rev ) ] );
        }
        name = name || this._guessNameForPair( fwd, rev );
        return { forward : fwd, name : name, reverse : rev };
    },

    /** try to find a good pair name for the given fwd and rev datasets */
    _guessNameForPair : function( fwd, rev, removeExtensions ){
        removeExtensions = ( removeExtensions !== undefined )?( removeExtensions ):( this.removeExtensions );
        var fwdName = fwd.name,
            revName = rev.name,
            lcs = this._naiveStartingAndEndingLCS(
                fwdName.replace( new RegExp( this.filters[0] ), '' ),
                revName.replace( new RegExp( this.filters[1] ), '' )
            );
        if( removeExtensions ){
            var lastDotIndex = lcs.lastIndexOf( '.' );
            if( lastDotIndex > 0 ){
                var extension = lcs.slice( lastDotIndex, lcs.length );
                lcs = lcs.replace( extension, '' );
                fwdName = fwdName.replace( extension, '' );
                revName = revName.replace( extension, '' );
            }
        }
        return lcs || ( fwdName + ' & ' + revName );
    },

    /** unpair a pair, removing it from paired, and adding the fwd,rev datasets back into unpaired */
    _unpair : function( pair, options ){
        options = options || {};
        if( !pair ){
            throw new Error( 'Bad pair: ' + JSON.stringify( pair ) );
        }
        this.paired = _.without( this.paired, pair );
        this._addToUnpaired( pair.forward );
        this._addToUnpaired( pair.reverse );

        if( !options.silent ){
            this.trigger( 'pair:unpair', [ pair ] );
        }
        return pair;
    },

    /** unpair all paired datasets */
    unpairAll : function(){
        var pairs = [];
        while( this.paired.length ){
            pairs.push( this._unpair( this.paired[ 0 ], { silent: true }) );
        }
        this.trigger( 'pair:unpair', pairs );
    },

    // ------------------------------------------------------------------------ API
    /** convert a pair into JSON compatible with the collections API */
    _pairToJSON : function( pair, src ){
        src = src || 'hda';
        //TODO: consider making this the pair structure when created instead
        return {
            collection_type : 'paired',
            src             : 'new_collection',
            name            : pair.name,
            element_identifiers : [{
                name    : 'forward',
                id      : pair.forward.id,
                src     : src
            }, {
                name    : 'reverse',
                id      : pair.reverse.id,
                src     : src
            }]
        };
    },

    /** create the collection via the API
     *  @returns {jQuery.xhr Object}    the jquery ajax request
     */
    createList : function( name ){
        var creator = this,
            url = Galaxy.root + 'api/histories/' + this.historyId + '/contents/dataset_collections';

        //TODO: use ListPairedCollection.create()
        var ajaxData = {
            type            : 'dataset_collection',
            collection_type : 'list:paired',
            hide_source_items : creator.hideOriginals || false,
            name            : _.escape( name || creator.$( '.collection-name' ).val() ),
            element_identifiers : creator.paired.map( function( pair ){
                return creator._pairToJSON( pair );
            })

        };
        //this.debug( JSON.stringify( ajaxData ) );
        creator.blocking = true;
        return jQuery.ajax( url, {
            type        : 'POST',
            contentType : 'application/json',
            dataType    : 'json',
            data        : JSON.stringify( ajaxData )
        })
        .always( function(){
            creator.blocking = false;
        })
        .fail( function( xhr, status, message ){
            creator._ajaxErrHandler( xhr, status, message );
        })
        .done( function( response, message, xhr ){
            //this.info( 'ok', response, message, xhr );
            creator.trigger( 'collection:created', response, message, xhr );
            creator.metric( 'collection:created', response );
            if( typeof creator.oncreate === 'function' ){
                creator.oncreate.call( this, response, message, xhr );
            }
        });
    },

    /** handle ajax errors with feedback and details to the user (if available) */
    _ajaxErrHandler : function( xhr, status, message ){
        this.error( xhr, status, message );
        var content = _l( 'An error occurred while creating this collection' );
        if( xhr ){
            if( xhr.readyState === 0 && xhr.status === 0 ){
                content += ': ' + _l( 'Galaxy could not be reached and may be updating.' )
                    + _l( ' Try again in a few minutes.' );
            } else if( xhr.responseJSON ){
                content += '<br /><pre>' + JSON.stringify( xhr.responseJSON ) + '</pre>';
            } else {
                content += ': ' + message;
            }
        }
        creator._showAlert( content, 'alert-danger' );
    },

    // ------------------------------------------------------------------------ rendering
    /** render the entire interface */
    render : function( speed, callback ){
        //this.debug( '-- _render' );
        //this.$el.empty().html( this.templates.main() );
        this.$el.empty().html( this.templates.main() );
        this._renderHeader( speed );
        this._renderMiddle( speed );
        this._renderFooter( speed );
        this._addPluginComponents();
        this.trigger( 'rendered', this );
        return this;
    },

    /** render the header section */
    _renderHeader : function( speed, callback ){
        //this.debug( '-- _renderHeader' );
        var $header = this.$( '.header' ).empty().html( this.templates.header() )
            .find( '.help-content' ).prepend( $( this.templates.helpContent() ) );

        this._renderFilters();
        return $header;
    },
    /** fill the filter inputs with the filter values */
    _renderFilters : function(){
        return    this.$( '.forward-column .column-header input' ).val( this.filters[0] )
            .add( this.$( '.reverse-column .column-header input' ).val( this.filters[1] ) );
    },

    /** render the middle including unpaired and paired sections (which may be hidden) */
    _renderMiddle : function( speed, callback ){
        var $middle = this.$( '.middle' ).empty().html( this.templates.middle() );

        // (re-) hide the un/paired panels based on instance vars
        if( this.unpairedPanelHidden ){
            this.$( '.unpaired-columns' ).hide();
        } else if( this.pairedPanelHidden ){
            this.$( '.paired-columns' ).hide();
        }

        this._renderUnpaired();
        this._renderPaired();
        return $middle;
    },
    /** render the unpaired section, showing datasets accrd. to filters, update the unpaired counts */
    _renderUnpaired : function( speed, callback ){
        //this.debug( '-- _renderUnpaired' );
        var creator = this,
            $fwd, $rev, $prd = [],
            split = this._splitByFilters();
        // update unpaired counts
        this.$( '.forward-column .title' )
            .text([ split[0].length, _l( 'unpaired forward' ) ].join( ' ' ));
        this.$( '.forward-column .unpaired-info' )
            .text( this._renderUnpairedDisplayStr( this.unpaired.length - split[0].length ) );
        this.$( '.reverse-column .title' )
            .text([ split[1].length, _l( 'unpaired reverse' ) ].join( ' ' ));
        this.$( '.reverse-column .unpaired-info' )
            .text( this._renderUnpairedDisplayStr( this.unpaired.length - split[1].length ) );

        this.$( '.unpaired-columns .column-datasets' ).empty();

        // show/hide the auto pair button if any unpaired are left
        this.$( '.autopair-link' ).toggle( this.unpaired.length !== 0 );
        if( this.unpaired.length === 0 ){
            this._renderUnpairedEmpty();
            return;
        }

        // create the dataset dom arrays
        $rev = split[1].map( function( dataset, i ){
            // if there'll be a fwd dataset across the way, add a button to pair the row
            if( ( split[0][ i ] !== undefined )
            &&  ( split[0][ i ] !== dataset ) ){
                $prd.push( creator._renderPairButton() );
            }
            return creator._renderUnpairedDataset( dataset );
        });
        $fwd = split[0].map( function( dataset ){
            return creator._renderUnpairedDataset( dataset );
        });

        if( !$fwd.length && !$rev.length ){
            this._renderUnpairedNotShown();
            return;
        }
        // add to appropo cols
        //TODO: not the best way to render - consider rendering the entire unpaired-columns section in a fragment
        //  and swapping out that
        this.$( '.unpaired-columns .forward-column .column-datasets' ).append( $fwd )
            .add( this.$( '.unpaired-columns .paired-column .column-datasets' ).append( $prd ) )
            .add( this.$( '.unpaired-columns .reverse-column .column-datasets' ).append( $rev ) );
        this._adjUnpairedOnScrollbar();
    },
    /** return a string to display the count of filtered out datasets */
    _renderUnpairedDisplayStr : function( numFiltered ){
        return [ '(', numFiltered, ' ', _l( 'filtered out' ), ')' ].join('');
    },
    /** return an unattached jQuery DOM element to represent an unpaired dataset */
    _renderUnpairedDataset : function( dataset ){
        //TODO: to underscore template
        return $( '<li/>')
            .attr( 'id', 'dataset-' + dataset.id )
            .addClass( 'dataset unpaired' )
            .attr( 'draggable', true )
            .addClass( dataset.selected? 'selected': '' )
            .append( $( '<span/>' ).addClass( 'dataset-name' ).text( dataset.name ) )
            //??
            .data( 'dataset', dataset );
    },
    /** render the button that may go between unpaired datasets, allowing the user to pair a row */
    _renderPairButton : function(){
        //TODO: *not* a dataset - don't pretend like it is
        return $( '<li/>').addClass( 'dataset unpaired' )
            .append( $( '<span/>' ).addClass( 'dataset-name' ).text( _l( 'Pair these datasets' ) ) );
    },
    /** a message to display when no unpaired left */
    _renderUnpairedEmpty : function(){
        //this.debug( '-- renderUnpairedEmpty' );
        var $msg = $( '<div class="empty-message"></div>' )
            .text( '(' + _l( 'no remaining unpaired datasets' ) + ')' );
        this.$( '.unpaired-columns .paired-column .column-datasets' ).empty().prepend( $msg );
        return $msg;
    },
    /** a message to display when no unpaired can be shown with the current filters */
    _renderUnpairedNotShown : function(){
        //this.debug( '-- renderUnpairedEmpty' );
        var $msg = $( '<div class="empty-message"></div>' )
            .text( '(' + _l( 'no datasets were found matching the current filters' ) + ')' );
        this.$( '.unpaired-columns .paired-column .column-datasets' ).empty().prepend( $msg );
        return $msg;
    },
    /** try to detect if the unpaired section has a scrollbar and adjust left column for better centering of all */
    _adjUnpairedOnScrollbar : function(){
        var $unpairedColumns = this.$( '.unpaired-columns' ).last(),
            $firstDataset = this.$( '.unpaired-columns .reverse-column .dataset' ).first();
        if( !$firstDataset.length ){ return; }
        var ucRight = $unpairedColumns.offset().left + $unpairedColumns.outerWidth(),
            dsRight = $firstDataset.offset().left + $firstDataset.outerWidth(),
            rightDiff = Math.floor( ucRight ) - Math.floor( dsRight );
        //this.debug( 'rightDiff:', ucRight, '-', dsRight, '=', rightDiff );
        this.$( '.unpaired-columns .forward-column' )
            .css( 'margin-left', ( rightDiff > 0 )? rightDiff: 0 );
    },

    /** render the paired section and update counts of paired datasets */
    _renderPaired : function( speed, callback ){
        //this.debug( '-- _renderPaired' );
        this.$( '.paired-column-title .title' ).text([ this.paired.length, _l( 'paired' ) ].join( ' ' ) );
        // show/hide the unpair all link
        this.$( '.unpair-all-link' ).toggle( this.paired.length !== 0 );
        if( this.paired.length === 0 ){
            this._renderPairedEmpty();
            return;
            //TODO: would be best to return here (the $columns)
        } else {
            // show/hide 'remove extensions link' when any paired and they seem to have extensions
            this.$( '.remove-extensions-link' ).show();
        }

        this.$( '.paired-columns .column-datasets' ).empty();
        var creator = this;
        this.paired.forEach( function( pair, i ){
            //TODO: cache these?
            var pairView = new PairView({ pair: pair });
            creator.$( '.paired-columns .column-datasets' )
                .append( pairView.render().$el )
                .append([
                    '<button class="unpair-btn">',
                        '<span class="fa fa-unlink" title="', _l( 'Unpair' ), '"></span>',
                    '</button>'
                ].join( '' ));
        });
    },
    /** a message to display when none paired */
    _renderPairedEmpty : function(){
        var $msg = $( '<div class="empty-message"></div>' )
            .text( '(' + _l( 'no paired datasets yet' ) + ')' );
        this.$( '.paired-columns .column-datasets' ).empty().prepend( $msg );
        return $msg;
    },

    footerSettings : {
        '.hide-originals': 'hideOriginals',
        '.remove-extensions': 'removeExtensions'
    },

    /** add any jQuery/bootstrap/custom plugins to elements rendered */
    _addPluginComponents : function(){
        this._chooseFiltersPopover( '.choose-filters-link' );
        this.$( '.help-content i' ).hoverhighlight( '.collection-creator', 'rgba( 64, 255, 255, 1.0 )' );
    },

    /** build a filter selection popover allowing selection of common filter pairs */
    _chooseFiltersPopover : function( selector ){
        function filterChoice( val1, val2 ){
            return [
                '<button class="filter-choice btn" ',
                        'data-forward="', val1, '" data-reverse="', val2, '">',
                    _l( 'Forward' ), ': ', val1, ', ',
                    _l( 'Reverse' ), ': ', val2,
                '</button>'
            ].join('');
        }
        var $popoverContent = $( _.template([
            '<div class="choose-filters">',
                '<div class="help">',
                    _l( 'Choose from the following filters to change which unpaired reads are shown in the display' ),
                ':</div>',
                _.values( this.commonFilters ).map( function( filterSet ){
                    return filterChoice( filterSet[0], filterSet[1] );
                }).join( '' ),
            '</div>'
        ].join(''))({}));

        return this.$( selector ).popover({
            container   : '.collection-creator',
            placement   : 'bottom',
            html        : true,
            //animation   : false,
            content     : $popoverContent
        });
    },

    /** add (or clear if clear is truthy) a validation warning to what */
    _validationWarning : function( what, clear ){
        var VALIDATION_CLASS = 'validation-warning';
        if( what === 'name' ){
            what = this.$( '.collection-name' ).add( this.$( '.collection-name-prompt' ) );
            this.$( '.collection-name' ).focus().select();
        }
        if( clear ){
            what = what || this.$( '.' + VALIDATION_CLASS );
            what.removeClass( VALIDATION_CLASS );
        } else {
            what.addClass( VALIDATION_CLASS );
        }
    },

    // ------------------------------------------------------------------------ events
    /** set up event handlers on self */
    _setUpBehaviors : function(){
        this.once( 'rendered', function(){
            this.trigger( 'rendered:initial', this );
        });

        this.on( 'pair:new', function(){
            //TODO: ideally only re-render the columns (or even elements) involved
            this._renderUnpaired();
            this._renderPaired();

            // scroll to bottom where new pairs are added
            //TODO: this doesn't seem to work - innerHeight sticks at 133...
            //  may have to do with improper flex columns
            //var $pairedView = this.$( '.paired-columns' );
            //$pairedView.scrollTop( $pairedView.innerHeight() );
            //this.debug( $pairedView.height() )
            this.$( '.paired-columns' ).scrollTop( 8000000 );
        });
        this.on( 'pair:unpair', function( pairs ){
            //TODO: ideally only re-render the columns (or even elements) involved
            this._renderUnpaired();
            this._renderPaired();
            this.splitView();
        });

        this.on( 'filter-change', function(){
            this.filters = [
                this.$( '.forward-unpaired-filter input' ).val(),
                this.$( '.reverse-unpaired-filter input' ).val()
            ];
            this.metric( 'filter-change', this.filters );
            this._renderFilters();
            this._renderUnpaired();
        });

        this.on( 'autopair', function(){
            this._renderUnpaired();
            this._renderPaired();

            var message, msgClass = null;
            if( this.paired.length ){
                msgClass = 'alert-success';
                message = this.paired.length + ' ' + _l( 'pairs created' );
                if( !this.unpaired.length ){
                    message += ': ' + _l( 'all datasets have been successfully paired' );
                    this.hideUnpaired();
                    this.$( '.collection-name' ).focus();
                }
            } else {
                message = _l([
                    'Could not automatically create any pairs from the given dataset names.',
                    'You may want to choose or enter different filters and try auto-pairing again.',
                    'Close this message using the X on the right to view more help.'
                ].join( ' ' ));
            }
            this._showAlert( message, msgClass );
        });

        //this.on( 'all', function(){
        //    this.info( arguments );
        //});
        return this;
    },

    events : {
        // header
        'click .more-help'                          : '_clickMoreHelp',
        'click .less-help'                          : '_clickLessHelp',
        'click .main-help'                          : '_toggleHelp',
        'click .header .alert button'               : '_hideAlert',
        'click .forward-column .column-title'       : '_clickShowOnlyUnpaired',
        'click .reverse-column .column-title'       : '_clickShowOnlyUnpaired',
        'click .unpair-all-link'                    : '_clickUnpairAll',
        //TODO: this seems kinda backasswards - re-sending jq event as a backbone event, can we listen directly?
        'change .forward-unpaired-filter input'     : function( ev ){ this.trigger( 'filter-change' ); },
        'focus .forward-unpaired-filter input'      : function( ev ){ $( ev.currentTarget ).select(); },
        'click .autopair-link'                      : '_clickAutopair',
        'click .choose-filters .filter-choice'      : '_clickFilterChoice',
        'click .clear-filters-link'                 : '_clearFilters',
        'change .reverse-unpaired-filter input'     : function( ev ){ this.trigger( 'filter-change' ); },
        'focus .reverse-unpaired-filter input'      : function( ev ){ $( ev.currentTarget ).select(); },
        // unpaired
        'click .forward-column .dataset.unpaired'   : '_clickUnpairedDataset',
        'click .reverse-column .dataset.unpaired'   : '_clickUnpairedDataset',
        'click .paired-column .dataset.unpaired'    : '_clickPairRow',
        'click .unpaired-columns'                   : 'clearSelectedUnpaired',
        'mousedown .unpaired-columns .dataset'      : '_mousedownUnpaired',
        // divider
        'click .paired-column-title'                : '_clickShowOnlyPaired',
        'mousedown .flexible-partition-drag'        : '_startPartitionDrag',
        // paired
        'click .paired-columns .dataset.paired'     : 'selectPair',
        'click .paired-columns'                     : 'clearSelectedPaired',
        'click .paired-columns .pair-name'          : '_clickPairName',
        'click .unpair-btn'                         : '_clickUnpair',
        // paired - drop target
        //'dragenter .paired-columns'                 : '_dragenterPairedColumns',
        //'dragleave .paired-columns .column-datasets': '_dragleavePairedColumns',
        'dragover .paired-columns .column-datasets' : '_dragoverPairedColumns',
        'drop .paired-columns .column-datasets'     : '_dropPairedColumns',

        'pair.dragstart .paired-columns .column-datasets' : '_pairDragstart',
        'pair.dragend   .paired-columns .column-datasets' : '_pairDragend',

        // footer
        'change .remove-extensions'                 : function( ev ){ this.toggleExtensions(); },
        'change .collection-name'                   : '_changeName',
        'keydown .collection-name'                  : '_nameCheckForEnter',
        'change .hide-originals'                    : '_changeHideOriginals',
        'click .cancel-create'                      : '_cancelCreate',
        'click .create-collection'                  : '_clickCreate'//,
    },

    /** toggle between showing only unpaired and split view */
    _clickShowOnlyUnpaired : function( ev ){
        //this.debug( 'click unpaired', ev.currentTarget );
        if( this.$( '.paired-columns' ).is( ':visible' ) ){
            this.hidePaired();
        } else {
            this.splitView();
        }
    },
    /** toggle between showing only paired and split view */
    _clickShowOnlyPaired : function( ev ){
        //this.debug( 'click paired' );
        if( this.$( '.unpaired-columns' ).is( ':visible' ) ){
            this.hideUnpaired();
        } else {
            this.splitView();
        }
    },

    /** hide unpaired, show paired */
    hideUnpaired : function( speed, callback ){
        this.unpairedPanelHidden = true;
        this.pairedPanelHidden = false;
        this._renderMiddle( speed, callback );
    },
    /** hide paired, show unpaired */
    hidePaired : function( speed, callback ){
        this.unpairedPanelHidden = false;
        this.pairedPanelHidden = true;
        this._renderMiddle( speed, callback );
    },
    /** show both paired and unpaired (splitting evenly) */
    splitView : function( speed, callback ){
        this.unpairedPanelHidden = this.pairedPanelHidden = false;
        this._renderMiddle( speed, callback );
        return this;
    },

    /** unpair all paired and do other super neat stuff which I'm not really sure about yet... */
    _clickUnpairAll : function( ev ){
        this.metric( 'unpairAll' );
        this.unpairAll();
    },

    /** attempt to autopair */
    _clickAutopair : function( ev ){
        var paired = this.autoPair();
        this.metric( 'autopair', paired.length, this.unpaired.length );
        this.trigger( 'autopair' );
    },

    /** set the filters based on the data attributes of the button click target */
    _clickFilterChoice : function( ev ){
        var $selected = $( ev.currentTarget );
        this.$( '.forward-unpaired-filter input' ).val( $selected.data( 'forward' ) );
        this.$( '.reverse-unpaired-filter input' ).val( $selected.data( 'reverse' ) );
        this._hideChooseFilters();
        this.trigger( 'filter-change' );
    },

    /** hide the choose filters popover */
    _hideChooseFilters : function(){
        //TODO: update bootstrap and remove the following hack
        //  see also: https://github.com/twbs/bootstrap/issues/10260
        this.$( '.choose-filters-link' ).popover( 'hide' );
        this.$( '.popover' ).css( 'display', 'none' );
    },

    /** clear both filters */
    _clearFilters : function( ev ){
        this.$( '.forward-unpaired-filter input' ).val( '' );
        this.$( '.reverse-unpaired-filter input' ).val( '' );
        this.trigger( 'filter-change' );
    },

    // ........................................................................ unpaired
    /** select an unpaired dataset */
    _clickUnpairedDataset : function( ev ){
        ev.stopPropagation();
        return this.toggleSelectUnpaired( $( ev.currentTarget ) );
    },

    /** Toggle the selection of an unpaired dataset representation.
     *  @param [jQuery] $dataset        the unpaired dataset dom rep to select
     *  @param [Boolean] options.force  if defined, force selection based on T/F; otherwise, toggle
     */
    toggleSelectUnpaired : function( $dataset, options ){
        options = options || {};
        var dataset = $dataset.data( 'dataset' ),
            select = options.force !== undefined? options.force: !$dataset.hasClass( 'selected' );
        //this.debug( id, options.force, $dataset, dataset );
        if( !$dataset.length || dataset === undefined ){ return $dataset; }

        if( select ){
            $dataset.addClass( 'selected' );
            if( !options.waitToPair ){
                this.pairAllSelected();
            }

        } else {
            $dataset.removeClass( 'selected' );
            //delete dataset.selected;
        }
        return $dataset;
    },

    /** pair all the currently selected unpaired datasets */
    pairAllSelected : function( options ){
        options = options || {};
        var creator = this,
            fwds = [],
            revs = [],
            pairs = [];
        creator.$( '.unpaired-columns .forward-column .dataset.selected' ).each( function(){
            fwds.push( $( this ).data( 'dataset' ) );
        });
        creator.$( '.unpaired-columns .reverse-column .dataset.selected' ).each( function(){
            revs.push( $( this ).data( 'dataset' ) );
        });
        fwds.length = revs.length = Math.min( fwds.length, revs.length );
        //this.debug( fwds );
        //this.debug( revs );
        fwds.forEach( function( fwd, i ){
            try {
                pairs.push( creator._pair( fwd, revs[i], { silent: true }) );

            } catch( err ){
                //TODO: preserve selected state of those that couldn't be paired
                //TODO: warn that some could not be paired
                creator.error( err );
            }
        });
        if( pairs.length && !options.silent ){
            this.trigger( 'pair:new', pairs );
        }
        return pairs;
    },

    /** clear the selection on all unpaired datasets */
    clearSelectedUnpaired : function(){
        this.$( '.unpaired-columns .dataset.selected' ).removeClass( 'selected' );
    },

    /** when holding down the shift key on a click, 'paint' the moused over datasets as selected */
    _mousedownUnpaired : function( ev ){
        if( ev.shiftKey ){
            var creator = this,
                $startTarget = $( ev.target ).addClass( 'selected' ),
                moveListener = function( ev ){
                    creator.$( ev.target ).filter( '.dataset' ).addClass( 'selected' );
                };
            $startTarget.parent().on( 'mousemove', moveListener );

            // on any mouseup, stop listening to the move and try to pair any selected
            $( document ).one( 'mouseup', function( ev ){
                $startTarget.parent().off( 'mousemove', moveListener );
                creator.pairAllSelected();
            });
        }
    },

    /** attempt to pair two datasets directly across from one another */
    _clickPairRow : function( ev ){
        //if( !ev.currentTarget ){ return true; }
        var rowIndex = $( ev.currentTarget ).index(),
            fwd = $( '.unpaired-columns .forward-column .dataset' ).eq( rowIndex ).data( 'dataset' ),
            rev = $( '.unpaired-columns .reverse-column .dataset' ).eq( rowIndex ).data( 'dataset' );
        //this.debug( 'row:', rowIndex, fwd, rev );
        this._pair( fwd, rev );
    },

    // ........................................................................ divider/partition
    /** start dragging the visible divider/partition between unpaired and paired panes */
    _startPartitionDrag : function( ev ){
        var creator = this,
            startingY = ev.pageY;
        //this.debug( 'partition drag START:', ev );
        $( 'body' ).css( 'cursor', 'ns-resize' );
        creator.$( '.flexible-partition-drag' ).css( 'color', 'black' );

        function endDrag( ev ){
            //creator.debug( 'partition drag STOP:', ev );
            // doing this by an added class didn't really work well - kept flashing still
            creator.$( '.flexible-partition-drag' ).css( 'color', '' );
            $( 'body' ).css( 'cursor', '' ).unbind( 'mousemove', trackMouse );
        }
        function trackMouse( ev ){
            var offset = ev.pageY - startingY;
            //creator.debug( 'partition:', startingY, offset );
            if( !creator.adjPartition( offset ) ){
                //creator.debug( 'mouseup triggered' );
                $( 'body' ).trigger( 'mouseup' );
            }
            creator._adjUnpairedOnScrollbar();
            startingY += offset;
        }
        $( 'body' ).mousemove( trackMouse );
        $( 'body' ).one( 'mouseup', endDrag );
    },

    /** adjust the parition up/down +/-adj pixels */
    adjPartition : function( adj ){
        var $unpaired = this.$( '.unpaired-columns' ),
            $paired = this.$( '.paired-columns' ),
            unpairedHi = parseInt( $unpaired.css( 'height' ), 10 ),
            pairedHi = parseInt( $paired.css( 'height' ), 10 );
        //this.debug( adj, 'hi\'s:', unpairedHi, pairedHi, unpairedHi + adj, pairedHi - adj );

        unpairedHi = Math.max( 10, unpairedHi + adj );
        pairedHi = pairedHi - adj;

        var movingUpwards = adj < 0;
        // when the divider gets close to the top - lock into hiding the unpaired section
        if( movingUpwards ){
            if( this.unpairedPanelHidden ){
                return false;
            } else if( unpairedHi <= 10 ){
                this.hideUnpaired();
                return false;
            }
        } else {
            if( this.unpairedPanelHidden ){
                $unpaired.show();
                this.unpairedPanelHidden = false;
            }
        }

        // when the divider gets close to the bottom - lock into hiding the paired section
        if( !movingUpwards ){
            if( this.pairedPanelHidden ){
                return false;
            } else if( pairedHi <= 15 ){
                this.hidePaired();
                return false;
            }

        } else {
            if( this.pairedPanelHidden ){
                $paired.show();
                this.pairedPanelHidden = false;
            }
        }

        $unpaired.css({
            height  : unpairedHi + 'px',
            flex    : '0 0 auto'
        });
        return true;
    },

    // ........................................................................ paired
    /** select a pair when clicked */
    selectPair : function( ev ){
        ev.stopPropagation();
        $( ev.currentTarget ).toggleClass( 'selected' );
    },

    /** deselect all pairs */
    clearSelectedPaired : function( ev ){
        this.$( '.paired-columns .dataset.selected' ).removeClass( 'selected' );
    },

    /** rename a pair when the pair name is clicked */
    _clickPairName : function( ev ){
        ev.stopPropagation();
        var $name = $( ev.currentTarget ),
            $pair = $name.parent().parent(),
            index = $pair.index( '.dataset.paired' ),
            pair = this.paired[ index ],
            response = prompt( 'Enter a new name for the pair:', pair.name );
        if( response ){
            pair.name = response;
            // set a flag (which won't be passed in json creation) for manual naming so we don't overwrite these
            //  when adding/removing extensions
            //hackish
            pair.customizedName = true;
            $name.text( pair.name );
        }
    },

    /** unpair this pair */
    _clickUnpair : function( ev ){
        //if( !ev.currentTarget ){ return true; }
        var pairIndex = Math.floor( $( ev.currentTarget ).index( '.unpair-btn' ) );
        //this.debug( 'pair:', pairIndex );
        this._unpair( this.paired[ pairIndex ] );
    },

    // ........................................................................ paired - drag and drop re-ordering
    //_dragenterPairedColumns : function( ev ){
    //    this.debug( '_dragenterPairedColumns:', ev );
    //},
    //_dragleavePairedColumns : function( ev ){
    //    //this.debug( '_dragleavePairedColumns:', ev );
    //},
    /** track the mouse drag over the paired list adding a placeholder to show where the drop would occur */
    _dragoverPairedColumns : function( ev ){
        //this.debug( '_dragoverPairedColumns:', ev );
        ev.preventDefault();

        var $list = this.$( '.paired-columns .column-datasets' );
        this._checkForAutoscroll( $list, ev.originalEvent.clientY );
        //this.debug( ev.originalEvent.clientX, ev.originalEvent.clientY );
        var $nearest = this._getNearestPairedDatasetLi( ev.originalEvent.clientY );

        $( '.element-drop-placeholder' ).remove();
        var $placeholder = $( '<div class="element-drop-placeholder"></div>' );
        if( !$nearest.length ){
            $list.append( $placeholder );
        } else {
            $nearest.before( $placeholder );
        }
    },

    /** If the mouse is near enough to the list's top or bottom, scroll the list */
    _checkForAutoscroll : function( $element, y ){
        var AUTOSCROLL_SPEED = 2;
        var offset = $element.offset(),
            scrollTop = $element.scrollTop(),
            upperDist = y - offset.top,
            lowerDist = ( offset.top + $element.outerHeight() ) - y;
        //this.debug( '_checkForAutoscroll:', scrollTop, upperDist, lowerDist );
        if( upperDist >= 0 && upperDist < this.autoscrollDist ){
            $element.scrollTop( scrollTop - AUTOSCROLL_SPEED );
        } else if( lowerDist >= 0 && lowerDist < this.autoscrollDist ){
            $element.scrollTop( scrollTop + AUTOSCROLL_SPEED );
        }
    },

    /** get the nearest *previous* paired dataset PairView based on the mouse's Y coordinate.
     *      If the y is at the end of the list, return an empty jQuery object.
     */
    _getNearestPairedDatasetLi : function( y ){
        var WIGGLE = 4,
            lis = this.$( '.paired-columns .column-datasets li' ).toArray();
        for( var i=0; i<lis.length; i++ ){
            var $li = $( lis[i] ),
                top = $li.offset().top,
                halfHeight = Math.floor( $li.outerHeight() / 2 ) + WIGGLE;
            if( top + halfHeight > y && top - halfHeight < y ){
                //this.debug( y, top + halfHeight, top - halfHeight )
                return $li;
            }
        }
        return $();
    },
    /** drop (dragged/selected PairViews) onto the list, re-ordering both the DOM and the internal array of pairs */
    _dropPairedColumns : function( ev ){
        // both required for firefox
        ev.preventDefault();
        ev.dataTransfer.dropEffect = 'move';

        var $nearest = this._getNearestPairedDatasetLi( ev.originalEvent.clientY );
        if( $nearest.length ){
            this.$dragging.insertBefore( $nearest );

        } else {
            // no nearest before - insert after last element (unpair button)
            this.$dragging.insertAfter( this.$( '.paired-columns .unpair-btn' ).last() );
        }
        // resync the creator's list of paired based on the new DOM order
        this._syncPairsToDom();
        return false;
    },
    /** resync the creator's list of paired based on the DOM order of pairs */
    _syncPairsToDom : function(){
        var newPaired = [];
        //TODO: doesn't seem wise to use the dom to store these - can't we sync another way?
        this.$( '.paired-columns .dataset.paired' ).each( function(){
            newPaired.push( $( this ).data( 'pair' ) );
        });
        //this.debug( newPaired );
        this.paired = newPaired;
        this._renderPaired();
    },
    /** drag communication with pair sub-views: dragstart */
    _pairDragstart : function( ev, pair ){
        //this.debug( '_pairDragstart', ev, pair )
        // auto select the pair causing the event and move all selected
        pair.$el.addClass( 'selected' );
        var $selected = this.$( '.paired-columns .dataset.selected' );
        this.$dragging = $selected;
    },
    /** drag communication with pair sub-views: dragend - remove the placeholder */
    _pairDragend : function( ev, pair ){
        //this.debug( '_pairDragend', ev, pair )
        $( '.element-drop-placeholder' ).remove();
        this.$dragging = null;
    },

    // ........................................................................ footer
    toggleExtensions : function( force ){
        var creator = this;
        creator.removeExtensions = ( force !== undefined )?( force ):( !creator.removeExtensions );

        _.each( creator.paired, function( pair ){
            // don't overwrite custom names
            if( pair.customizedName ){ return; }
            pair.name = creator._guessNameForPair( pair.forward, pair.reverse );
        });

        creator._renderPaired();
        creator._renderFooter();
    },

    // ------------------------------------------------------------------------ misc
    /** debug a dataset list */
    _printList : function( list ){
        var creator = this;
        _.each( list, function( e ){
            if( list === creator.paired ){
                creator._printPair( e );
            } else {
                //creator.debug( e );
            }
        });
    },

    /** print a pair Object */
    _printPair : function( pair ){
        this.debug( pair.forward.name, pair.reverse.name, ': ->', pair.name );
    },

    /** string rep */
    toString : function(){ return 'PairedCollectionCreator'; },

    templates: _.extend({}, baseCreator.CollectionCreatorMixin._creatorTemplates, {

        /** the header (not including help text) */
        header : _.template([
            '<div class="main-help well clear">',
                '<a class="more-help" href="javascript:void(0);">', _l( 'More help' ), '</a>',
                '<div class="help-content">',
                    '<a class="less-help" href="javascript:void(0);">', _l( 'Less' ), '</a>',
                '</div>',
            '</div>',
            '<div class="alert alert-dismissable">',
                '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>',
                '<span class="alert-message"></span>',
            '</div>',

            '<div class="column-headers vertically-spaced flex-column-container">',
                '<div class="forward-column flex-column column">',
                    '<div class="column-header">',
                        '<div class="column-title">',
                            '<span class="title">', _l( 'Unpaired forward' ), '</span>',
                            '<span class="title-info unpaired-info"></span>',
                        '</div>',
                        '<div class="unpaired-filter forward-unpaired-filter pull-left">',
                            '<input class="search-query" placeholder="', _l( 'Filter this list' ), '" />',
                        '</div>',
                    '</div>',
                '</div>',
                '<div class="paired-column flex-column no-flex column">',
                    '<div class="column-header">',
                        '<a class="choose-filters-link" href="javascript:void(0)">',
                            _l( 'Choose filters' ),
                        '</a>',
                        '<a class="clear-filters-link" href="javascript:void(0);">',
                            _l( 'Clear filters' ),
                        '</a><br />',
                        '<a class="autopair-link" href="javascript:void(0);">',
                            _l( 'Auto-pair' ),
                        '</a>',
                    '</div>',
                '</div>',
                '<div class="reverse-column flex-column column">',
                    '<div class="column-header">',
                        '<div class="column-title">',
                            '<span class="title">', _l( 'Unpaired reverse' ), '</span>',
                            '<span class="title-info unpaired-info"></span>',
                        '</div>',
                        '<div class="unpaired-filter reverse-unpaired-filter pull-left">',
                            '<input class="search-query" placeholder="', _l( 'Filter this list' ), '" />',
                        '</div>',
                    '</div>',
                '</div>',
            '</div>'
        ].join('')),

        /** the middle: unpaired, divider, and paired */
        middle : _.template([
            // contains two flex rows (rows that fill available space) and a divider btwn
            '<div class="unpaired-columns flex-column-container scroll-container flex-row">',
                '<div class="forward-column flex-column column">',
                    '<ol class="column-datasets"></ol>',
                '</div>',
                '<div class="paired-column flex-column no-flex column">',
                    '<ol class="column-datasets"></ol>',
                '</div>',
                '<div class="reverse-column flex-column column">',
                    '<ol class="column-datasets"></ol>',
                '</div>',
            '</div>',
            '<div class="flexible-partition">',
                '<div class="flexible-partition-drag" title="', _l( 'Drag to change' ), '"></div>',
                '<div class="column-header">',
                    '<div class="column-title paired-column-title">',
                        '<span class="title"></span>',
                    '</div>',
                    '<a class="unpair-all-link" href="javascript:void(0);">',
                        _l( 'Unpair all' ),
                    '</a>',
                '</div>',
            '</div>',
            '<div class="paired-columns flex-column-container scroll-container flex-row">',
                '<ol class="column-datasets"></ol>',
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
                    '<label class="setting-prompt pull-right">',
                        _l( 'Remove file extensions from pair names' ), '?',
                        '<input class="remove-extensions pull-right" type="checkbox" />',
                    '</label>',
                '</div>',
                '<div class="clear">',
                    '<input class="collection-name form-control pull-right" ',
                        'placeholder="', _l( 'Enter a name for your new list' ), '" />',
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
                'Collections of paired datasets are ordered lists of dataset pairs (often forward and reverse reads). ',
                'These collections can be passed to tools and workflows in order to have analyses done on each member of ',
                'the entire group. This interface allows you to create a collection, choose which datasets are paired, ',
                'and re-order the final collection.'
            ].join( '' )), '</p>',
            '<p>', _l([
                'Unpaired datasets are shown in the <i data-target=".unpaired-columns">unpaired section</i> ',
                '(hover over the underlined words to highlight below). ',
                'Paired datasets are shown in the <i data-target=".paired-columns">paired section</i>.',
                '<ul>To pair datasets, you can:',
                    '<li>Click a dataset in the ',
                        '<i data-target=".unpaired-columns .forward-column .column-datasets,',
                                        '.unpaired-columns .forward-column">forward column</i> ',
                        'to select it then click a dataset in the ',
                        '<i data-target=".unpaired-columns .reverse-column .column-datasets,',
                                        '.unpaired-columns .reverse-column">reverse column</i>.',
                    '</li>',
                    '<li>Click one of the "Pair these datasets" buttons in the ',
                        '<i data-target=".unpaired-columns .paired-column .column-datasets,',
                                        '.unpaired-columns .paired-column">middle column</i> ',
                        'to pair the datasets in a particular row.',
                    '</li>',
                    '<li>Click <i data-target=".autopair-link">"Auto-pair"</i> ',
                        'to have your datasets automatically paired based on name.',
                    '</li>',
                '</ul>'
            ].join( '' )), '</p>',
            '<p>', _l([
                '<ul>You can filter what is shown in the unpaired sections by:',
                    '<li>Entering partial dataset names in either the ',
                        '<i data-target=".forward-unpaired-filter input">forward filter</i> or ',
                        '<i data-target=".reverse-unpaired-filter input">reverse filter</i>.',
                    '</li>',
                    '<li>Choosing from a list of preset filters by clicking the ',
                        '<i data-target=".choose-filters-link">"Choose filters" link</i>.',
                    '</li>',
                    '<li>Entering regular expressions to match dataset names. See: ',
                        '<a href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions"',
                            ' target="_blank">MDN\'s JavaScript Regular Expression Tutorial</a>. ',
                        'Note: forward slashes (\\) are not needed.',
                    '</li>',
                    '<li>Clearing the filters by clicking the ',
                        '<i data-target=".clear-filters-link">"Clear filters" link</i>.',
                    '</li>',
                '</ul>'
            ].join( '' )), '</p>',
            '<p>', _l([
                'To unpair individual dataset pairs, click the ',
                    '<i data-target=".unpair-btn">unpair buttons ( <span class="fa fa-unlink"></span> )</i>. ',
                'Click the <i data-target=".unpair-all-link">"Unpair all" link</i> to unpair all pairs.'
            ].join( '' )), '</p>',
            '<p>', _l([
                'You can include or remove the file extensions (e.g. ".fastq") from your pair names by toggling the ',
                    '<i data-target=".remove-extensions-prompt">"Remove file extensions from pair names?"</i> control.'
            ].join( '' )), '</p>',
            '<p>', _l([
                'Once your collection is complete, enter a <i data-target=".collection-name">name</i> and ',
                'click <i data-target=".create-collection">"Create list"</i>. ',
                '(Note: you do not have to pair all unpaired datasets to finish.)'
            ].join( '' )), '</p>'
        ].join(''))
    })
});

//=============================================================================
/** a modal version of the paired collection creator */
var pairedCollectionCreatorModal = function _pairedCollectionCreatorModal( datasets, options ){

    var deferred = jQuery.Deferred(),
        creator;

    options = _.defaults( options || {}, {
        datasets    : datasets,
        oncancel    : function(){
            Galaxy.modal.hide();
            deferred.reject( 'cancelled' );
        },
        oncreate    : function( creator, response ){
            Galaxy.modal.hide();
            deferred.resolve( response );
        }
    });

    if( !window.Galaxy || !Galaxy.modal ){
        throw new Error( 'Galaxy or Galaxy.modal not found' );
    }

    creator = new PairedCollectionCreator( options );
    Galaxy.modal.show({
        title   : 'Create a collection of paired datasets',
        body    : creator.$el,
        width   : '80%',
        height  : '800px',
        closing_events: true
    });
    creator.render();
    window.creator = creator;

    //TODO: remove modal header
    return deferred;
};


//=============================================================================
function createListOfPairsCollection( collection, defaultHideSourceItems ){
    var elements = collection.toJSON();
//TODO: validate elements
    return pairedCollectionCreatorModal( elements, {
        historyId : collection.historyId,
        defaultHideSourceItems: defaultHideSourceItems
    });
}


//=============================================================================
    return {
        PairedCollectionCreator : PairedCollectionCreator,
        pairedCollectionCreatorModal : pairedCollectionCreatorModal,
        createListOfPairsCollection : createListOfPairsCollection
    };
});
