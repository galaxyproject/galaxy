define([
    "utils/levenshtein",
    "mvc/base-mvc",
    "utils/localization"
], function( levelshteinDistance, baseMVC, _l ){
/* ============================================================================
TODO:
    _adjPairedOnScrollBar
    parition drag now doesn't stop when dragging down
        can push footer out of modal
        only *after* partition is all the way down once?


PROGRAMMATICALLY:
currPanel.once( 'rendered', function(){
    currPanel.showSelectors();
    currPanel.selectAllDatasets();
    _.last( currPanel.actionsPopup.options ).func();
});

============================================================================ */
/** A view for paired datasets in the collections creator.
 */
var PairView = Backbone.View.extend( baseMVC.LoggableMixin ).extend({

    tagName     : 'li',
    className   : 'dataset paired',

    initialize : function( attributes ){
        //console.debug( 'PairView.initialize:', attributes );
        this.pair = attributes.pair || {};
    },

    render : function(){
        this.$el
            .attr( 'draggable', true )
            .data( 'pair', this.pair )
            .html( _.template([
                '<span class="forward-dataset-name flex-column"><%= pair.forward.name %></span>',
                '<span class="pair-name-column flex-column">',
                    '<span class="pair-name"><%= pair.name %></span>',
                '</span>',
                '<span class="reverse-dataset-name flex-column"><%= pair.reverse.name %></span>'
            ].join(''), { pair: this.pair }))
            .addClass( 'flex-column-container' );

//TODO: would be good to get the unpair-btn into this view - but haven't found a way with css

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
        //console.debug( this, '_dragstartPair', ev );
        ev.currentTarget.style.opacity = '0.4';
        if( ev.originalEvent ){ ev = ev.originalEvent; }

        ev.dataTransfer.effectAllowed = 'move';
        ev.dataTransfer.setData( 'text/plain', JSON.stringify( this.pair ) );

        //ev.dataTransfer.setDragImage( null, 0, 0 );

        // the canvas can be used to create the image
        //ev.dataTransfer.setDragImage( canvasCrossHairs(), 25, 25 );

        //console.debug( 'ev.dataTransfer:', ev.dataTransfer );
        this.$el.parent().trigger( 'pair.dragstart', [ this ] );
    },
    /** dragging pairs for re-ordering */
    _dragend : function( ev ){
        //console.debug( this, '_dragendPair', ev );
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

/** An interface for building collections of paired datasets.
 */
var PairedCollectionCreator = Backbone.View.extend( baseMVC.LoggableMixin ).extend({

    className: 'collection-creator flex-row-container',

    /** set up initial options, instance vars, behaviors, and autopair (if set to do so) */
    initialize : function( attributes ){
        //this.debug( '-- PairedCollectionCreator:', attributes );

        attributes = _.defaults( attributes, {
            datasets            : [],
            filters             : this.DEFAULT_FILTERS,
            //automaticallyPair   : false,
            automaticallyPair   : true,
            matchPercentage     : 1.0,
            //matchPercentage     : 0.9,
            //matchPercentage     : 0.8,
            //strategy            : 'levenshtein'
            strategy            : 'lcs'
        });
        //this.debug( 'attributes now:', attributes );

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

        /** distance/mismatch level allowed for autopairing */
        this.matchPercentage = attributes.matchPercentage;

        /** what method to use for auto pairing (will be passed aggression level) */
        this.strategy = this.strategies[ attributes.strategy ] || this.strategies[ this.DEFAULT_STRATEGY ];
        if( _.isFunction( attributes.strategy ) ){
            this.strategy = attributes.strategy;
        }

        /** remove file extensions (\.*) from created pair names? */
        this.removeExtensions = true;
        //this.removeExtensions = false;

        /** fn to call when the cancel button is clicked (scoped to this) - if falsy, no btn is displayed */
        this.oncancel = attributes.oncancel;
        /** fn to call when the collection is created (scoped to this) */
        this.oncreate = attributes.oncreate;

        /** is the unpaired panel shown? */
        this.unpairedPanelHidden = false;
        /** is the paired panel shown? */
        this.pairedPanelHidden = false;

        /** DOM elements currently being dragged */
        this.$dragging = null;

        this._dataSetUp();

        this._setUpBehaviors();
    },

    /** map of common filter pairs by name */
    commonFilters : {
        none            : [ '', '' ],
        illumina        : [ '_1', '_2' ]
    },
    /** which commonFilter to use by default */
    DEFAULT_FILTERS : 'illumina',
    //DEFAULT_FILTERS : 'none',

    /** map of name->fn for autopairing */
    strategies : {
        'lcs'           : 'autoPairLCSs',
        'levenshtein'   : 'autoPairLevenshtein'
    },
    /** default autopair strategy name */
    DEFAULT_STRATEGY : 'lcs',

    // ------------------------------------------------------------------------ process raw list
    /** set up main data: cache initialList, sort, and autopair */
    _dataSetUp : function(){
        //this.debug( '-- _dataSetUp' );

        this.paired = [];
        this.unpaired = [];

        //this.fwdSelectedIds = [];
        //this.revSelectedIds = [];
        this.selectedIds = [];

        // sort initial list, add ids if needed, and save new working copy to unpaired
        this._sortInitialList();
        this._ensureIds();
        this.unpaired = this.initialList.slice( 0 );

        if( this.automaticallyPair ){
            this.autoPair();
        }
    },

    /** sort initial list */
    _sortInitialList : function(){
        //this.debug( '-- _sortInitialList' );
        this._sortDatasetList( this.initialList );
        //this._printList( this.unpaired );
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
        //this._printList( this.unpaired );
        return this.initialList;
    },

    /** split initial list into two lists, those that pass forward filters & those passing reverse */
    _splitByFilters : function( filters ){
        var fwd = [],
            rev = [];
        this.unpaired.forEach( function( unpaired ){
            if( this._filterFwdFn( unpaired ) ){
                fwd.push( unpaired );
            }
            if( this._filterRevFn( unpaired ) ){
                rev.push( unpaired );
            }
        }.bind( this ) );
        return [ fwd, rev ];
    },

    /** filter fn to apply to forward datasets */
    _filterFwdFn : function( dataset ){
//TODO: this treats *all* strings as regex which may confuse people
        var regexp = new RegExp( this.filters[0] );
        return regexp.test( dataset.name );
        //return dataset.name.indexOf( this.filters[0] ) >= 0;
    },

    /** filter fn to apply to reverse datasets */
    _filterRevFn : function( dataset ){
        var regexp = new RegExp( this.filters[1] );
        return regexp.test( dataset.name );
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
//TODO: lots of boiler plate btwn the three auto pair fns
    /** two passes to automatically create pairs:
     *  use both simpleAutoPair, then the fn mentioned in strategy
     */
    autoPair : function( strategy ){
        strategy = strategy || this.strategy;
        //this.debug( '-- autoPair', strategy );
        this.simpleAutoPair();
        return this[ strategy ].call( this );
    },

    /** attempts to pair forward with reverse when names exactly match (after removing filters) */
    simpleAutoPair : function(){
        //this.debug( '-- simpleAutoPair' );
        // simplified auto pair that moves down unpaired lists *in order*,
        //  removes filters' strings from fwd and rev,
        //  and, if names w/o filters *exactly* match, creates a pair
        // possibly good as a first pass
        var i = 0, j,
            split = this._splitByFilters(),
            fwdList = split[0],
            revList = split[1],
            fwdName, revName,
            matchFound = false;

        while( i<fwdList.length ){
            var fwd = fwdList[ i ];
            //TODO: go through the filterFwdFn
            fwdName = fwd.name.replace( this.filters[0], '' );
            //this.debug( i, 'fwd:', fwdName );
            matchFound = false;

            for( j=0; j<revList.length; j++ ){
                var rev = revList[ j ];
                revName = rev.name.replace( this.filters[1], '' );
                //this.debug( '\t ', j, 'rev:', revName );

                if( fwd !== rev && fwdName === revName ){
                    matchFound = true;
                    // if it is a match, keep i at current, pop fwd, pop rev and break
                    //this.debug( '---->', fwdName, revName );
                    this._pair(
                        fwdList.splice( i, 1 )[0],
                        revList.splice( j, 1 )[0],
                        { silent: true }
                    );
                    break;
                }
            }
            if( !matchFound ){ i += 1; }
        }
        //this.debug( 'remaining Forward:' );
        //this._printList( this.unpairedForward );
        //this.debug( 'remaining Reverse:' );
        //this._printList( this.unpairedReverse );
        //this.debug( '' );
    },

    /** attempt to autopair using edit distance between forward and reverse (after removing filters) */
    autoPairLevenshtein : function(){
        //precondition: filters are set, both lists are not empty, and all filenames.length > filters[?].length
        //this.debug( '-- autoPairLevenshtein' );
        var i = 0, j,
            split = this._splitByFilters(),
            fwdList = split[0],
            revList = split[1],
            fwdName, revName,
            distance, bestIndex, bestDist;

        while( i<fwdList.length ){
            var fwd = fwdList[ i ];
            //TODO: go through the filterFwdFn
            fwdName = fwd.name.replace( this.filters[0], '' );
            //this.debug( i, 'fwd:', fwdName );
            bestDist = Number.MAX_VALUE;

            for( j=0; j<revList.length; j++ ){
                var rev = revList[ j ];
                revName = rev.name.replace( this.filters[1], '' );
                //this.debug( '\t ', j, 'rev:', revName );

                if( fwd !== rev ){
                    if( fwdName === revName ){
                        //this.debug( '\t\t exactmatch:', fwdName, revName );
                        bestIndex = j;
                        bestDist = 0;
                        break;
                    }
                    distance = levenshteinDistance( fwdName, revName );
                    //this.debug( '\t\t distance:', distance, 'bestDist:', bestDist );
                    if( distance < bestDist ){
                        bestIndex = j;
                        bestDist = distance;
                    }
                }
            }
            //this.debug( '---->', fwd.name, bestIndex, bestDist );
            //this.debug( '---->', fwd.name, revList[ bestIndex ].name, bestDist );

            var percentage = 1.0 - ( bestDist / ( Math.max( fwdName.length, revName.length ) ) );
            //this.debug( '----> %', percentage * 100 );

            if( percentage >= this.matchPercentage ){
                this._pair(
                    fwdList.splice( i, 1 )[0],
                    revList.splice( bestIndex, 1 )[0],
                    { silent: true }
                );
                if( fwdList.length <= 0 || revList.length <= 0 ){
                    return;
                }
            } else {
                i += 1;
            }
        }
        //this.debug( 'remaining Forward:' );
        //this._printList( this.unpairedForward );
        //this.debug( 'remaining Reverse:' );
        //this._printList( this.unpairedReverse );
        //this.debug( '' );
    },

    /** attempt to auto pair using common substrings from both front and back (after removing filters) */
    autoPairLCSs : function(){
        //precondition: filters are set, both lists are not empty
        //this.debug( '-- autoPairLCSs' );
        var i = 0, j,
            split = this._splitByFilters(),
            fwdList = split[0],
            revList = split[1],
            fwdName, revName,
            currMatch, bestIndex, bestMatch;
        if( !fwdList.length || !revList.length ){ return; }
        //this.debug( fwdList, revList );

        while( i<fwdList.length ){
            var fwd = fwdList[ i ];
            fwdName = fwd.name.replace( this.filters[0], '' );
            //this.debug( i, 'fwd:', fwdName );
            bestMatch = 0;

            for( j=0; j<revList.length; j++ ){
                var rev = revList[ j ];
                revName = rev.name.replace( this.filters[1], '' );
                //this.debug( '\t ', j, 'rev:', revName );

                if( fwd !== rev ){
                    if( fwdName === revName ){
                        //this.debug( '\t\t exactmatch:', fwdName, revName );
                        bestIndex = j;
                        bestMatch = fwdName.length;
                        break;
                    }
                    var match = this._naiveStartingAndEndingLCS( fwdName, revName );
                    currMatch = match.length;
                    //this.debug( '\t\t match:', match, 'currMatch:', currMatch, 'bestMatch:', bestMatch );
                    if( currMatch > bestMatch ){
                        bestIndex = j;
                        bestMatch = currMatch;
                    }
                }
            }
            //this.debug( '---->', i, fwd.name, bestIndex, revList[ bestIndex ].name, bestMatch );

            var percentage = bestMatch / ( Math.min( fwdName.length, revName.length ) );
            //this.debug( '----> %', percentage * 100 );

            if( percentage >= this.matchPercentage ){
                this._pair(
                    fwdList.splice( i, 1 )[0],
                    revList.splice( bestIndex, 1 )[0],
                    { silent: true }
                );
                if( fwdList.length <= 0 || revList.length <= 0 ){
                    return;
                }
            } else {
                i += 1;
            }
        }
        //this.debug( 'remaining Forward:' );
        //this._printList( this.unpairedForward );
        //this.debug( 'remaining Reverse:' );
        //this._printList( this.unpairedReverse );
        //this.debug( '' );
    },

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
        //TODO: eventing, options
        //this.debug( '_pair:', fwd, rev );
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
        var lcs = this._naiveStartingAndEndingLCS(
//TODO: won't work with regex
            fwd.name.replace( this.filters[0], '' ),
            rev.name.replace( this.filters[1], '' )
        );
        if( removeExtensions ){
            var lastDotIndex = lcs.lastIndexOf( '.' );
            if( lastDotIndex > 0 ){
                lcs = lcs.slice( 0, lastDotIndex );
            }
        }
        //TODO: optionally remove extension
        return lcs || ( fwd.name + ' & ' + rev.name );
    },

    ///** find datasets with fwdId and revID and pair them */
    //_pairById : function( fwdId, revId, name ){
    //    var both = this.unpaired.filter( function( unpaired ){
    //            return unpaired.id === fwdId || unpaired.id === revId;
    //        }),
    //        fwd = both[0], rev = both[1];
    //    if( both[0].id === revId ){
    //        fwd = rev; rev = both[0];
    //    }
    //    return this._pair( fwd, rev, name );
    //},

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
    _pairToJSON : function( pair ){
        //TODO: consider making this the pair structure when created instead
        return {
            collection_type : 'paired',
            src             : 'new_collection',
            name            : pair.name,
            element_identifiers : [{
                name    : 'forward',
                id      : pair.forward.id,
                //TODO: isn't necessarily true
                src     : 'hda'
            }, {
                name    : 'reverse',
                id      : pair.reverse.id,
                //TODO: isn't necessarily true
                src     : 'hda'
            }]
        };
    },

    /** create the collection via the API
     *  @returns {jQuery.xhr Object}    the jquery ajax request
     */
    createList : function(){
        var creator = this,
            url;
        if( creator.historyId ){
            url = '/api/histories/' + this.historyId + '/contents/dataset_collections';
        //} else {
        //
        }

//TODO:?? Can't we use ListPairedCollection.create()
        var ajaxData = {
            type            : 'dataset_collection',
            collection_type : 'list:paired',
            name            : _.escape( creator.$( '.collection-name' ).val() ),
            element_identifiers : creator.paired.map( function( pair ){
                return creator._pairToJSON( pair );
            })
        };
        //this.debug( JSON.stringify( ajaxData ) );
        return jQuery.ajax( url, {
            type        : 'POST',
            contentType : 'application/json',
            dataType    : 'json',
            data        : JSON.stringify( ajaxData )
        })
        .fail( function( xhr, status, message ){
            creator._ajaxErrHandler( xhr, status, message );
        })
        .done( function( response, message, xhr ){
            //this.info( 'ok', response, message, xhr );
            creator.trigger( 'collection:created', response, message, xhr );
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
        //this.$el.empty().html( PairedCollectionCreator.templates.main() );
        this.$el.empty().html( PairedCollectionCreator.templates.main() );
        this._renderHeader( speed );
        this._renderMiddle( speed );
        this._renderFooter( speed );
        this._addPluginComponents();
        return this;
    },

    /** render the header section */
    _renderHeader : function( speed, callback ){
        //this.debug( '-- _renderHeader' );
        var $header = this.$( '.header' ).empty().html( PairedCollectionCreator.templates.header() )
            .find( '.help-content' ).prepend( $( PairedCollectionCreator.templates.helpContent() ) );

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
        var $middle = this.$( '.middle' ).empty().html( PairedCollectionCreator.templates.middle() );

        // (re-) hide the un/paired panels based on instance vars
        //TODO: use replaceWith
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
        //TODO: not the best way to render
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
        if( !$firstDataset.size() ){ return; }
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
//TODO: data-index="i"
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

    /** render the footer, completion controls, and cancel controls */
    _renderFooter : function( speed, callback ){
        var $footer = this.$( '.footer' ).empty().html( PairedCollectionCreator.templates.footer() );
        this.$( '.remove-extensions' ).prop( 'checked', this.removeExtensions );
        if( typeof this.oncancel === 'function' ){
            this.$( '.cancel-create.btn' ).show();
        }
        return $footer;
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
                //TODO: connect with common filters
                filterChoice( '_1', '_2' ),
                filterChoice( '_R1', '_R2' ),
            '</div>'
        ].join(''), {}));

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
                }
            } else {
                message = _l( 'Could not automatically create any pairs from the given dataset names' );
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
        'click .header .alert button'               : '_hideAlert',
        'click .forward-column .column-title'       : '_clickShowOnlyUnpaired',
        'click .reverse-column .column-title'       : '_clickShowOnlyUnpaired',
        'click .unpair-all-link'                    : '_clickUnpairAll',
        //TODO: this seems kinda backasswards
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
        'click .cancel-create'                      : function( ev ){
            if( typeof this.oncancel === 'function' ){
                this.oncancel.call( this );
            }
        },
        'click .create-collection'                  : '_clickCreate'//,
    },

    // ........................................................................ header
    /** expand help */
    _clickMoreHelp : function( ev ){
        this.$( '.main-help' ).addClass( 'expanded' );
        this.$( '.more-help' ).hide();
    },
    /** collapse help */
    _clickLessHelp : function( ev ){
        this.$( '.main-help' ).removeClass( 'expanded' );
        this.$( '.more-help' ).show();
    },

    /** show an alert on the top of the interface containing message (alertClass is bootstrap's alert-*)*/
    _showAlert : function( message, alertClass ){
        alertClass = alertClass || 'alert-danger';
        this.$( '.main-help' ).hide();
        this.$( '.header .alert' ).attr( 'class', 'alert alert-dismissable' ).addClass( alertClass ).show()
            .find( '.alert-message' ).html( message );
    },
    /** hide the alerts at the top */
    _hideAlert : function( message ){
        this.$( '.main-help' ).show();
        this.$( '.header .alert' ).hide();
    },

    //TODO: consolidate these
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
        this.unpairAll();
    },

    /** attempt to autopair */
    _clickAutopair : function( ev ){
        var paired = this.autoPair();
        //this.debug( 'autopaired', paired );
        //TODO: an indication of how many pairs were found - if 0, assist
        this.trigger( 'autopair', paired );
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
        if( !$dataset.size() || dataset === undefined ){ return $dataset; }

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
        //TODO: could be made more concise
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
        //TODO: animate
        this._pair( fwd, rev );
    },

    // ........................................................................ divider/partition
//TODO: simplify
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

//TODO: seems like shouldn't need this (it should be part of the hide/show/splitView)
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
        var $control = $( ev.currentTarget ),
            pair = this.paired[ $control.parent().index() ],
            response = prompt( 'Enter a new name for the pair:', pair.name );
        if( response ){
            pair.name = response;
            // set a flag (which won't be passed in json creation) for manual naming so we don't overwrite these
            //  when adding/removing extensions
            //TODO: kinda hacky
            pair.customizedName = true;
            $control.text( pair.name );
        }
    },

    /** unpair this pair */
    _clickUnpair : function( ev ){
        //if( !ev.currentTarget ){ return true; }
        //TODO: this is a hack bc each paired rev now has two elems (dataset, button)
        var pairIndex = Math.floor( $( ev.currentTarget ).index() / 2 );
        //this.debug( 'pair:', pairIndex );
        //TODO: animate
        this._unpair( this.paired[ pairIndex ] );
    },

    // ........................................................................ paired - drag and drop re-ordering
    //_dragenterPairedColumns : function( ev ){
    //    console.debug( '_dragenterPairedColumns:', ev );
    //},
    //_dragleavePairedColumns : function( ev ){
    //    //console.debug( '_dragleavePairedColumns:', ev );
    //},
    /** track the mouse drag over the paired list adding a placeholder to show where the drop would occur */
    _dragoverPairedColumns : function( ev ){
        //console.debug( '_dragoverPairedColumns:', ev );
        ev.preventDefault();

        var $list = this.$( '.paired-columns .column-datasets' ),
            offset = $list.offset();
        //console.debug( ev.originalEvent.clientX, ev.originalEvent.clientY );
        var $nearest = this._getNearestPairedDatasetLi( ev.originalEvent.clientY );
        //console.debug( ev.originalEvent.clientX - offset.left, ev.originalEvent.clientY - offset.top );

        $( '.paired-drop-placeholder' ).remove();
        var $placeholder = $( '<div class="paired-drop-placeholder"></div>')
        if( !$nearest.size() ){
            $list.append( $placeholder );
        } else {
            $nearest.before( $placeholder );
        }
    },
    /** get the nearest *previous* paired dataset PairView based on the mouse's Y coordinate.
     *      If the y is at the end of the list, return an empty jQuery object.
     */
    _getNearestPairedDatasetLi : function( y ){
        var WIGGLE = 4,
            lis = this.$( '.paired-columns .column-datasets li' ).toArray();
//TODO: better way?
        for( var i=0; i<lis.length; i++ ){
            var $li = $( lis[i] ),
                top = $li.offset().top,
                halfHeight = Math.floor( $li.outerHeight() / 2 ) + WIGGLE;
            if( top + halfHeight > y && top - halfHeight < y ){
                //console.debug( y, top + halfHeight, top - halfHeight )
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
        if( $nearest.size() ){
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
//TODO: ugh
        this.$( '.paired-columns .dataset.paired' ).each( function(){
            newPaired.push( $( this ).data( 'pair' ) );
        });
        //console.debug( newPaired );
        this.paired = newPaired;
        this._renderPaired();
    },
    /** drag communication with pair sub-views: dragstart */
    _pairDragstart : function( ev, pair ){
        //console.debug( '_pairDragstart', ev, pair )
        // auto select the pair causing the event and move all selected
        pair.$el.addClass( 'selected' );
        var $selected = this.$( '.paired-columns .dataset.selected' );
        this.$dragging = $selected;
    },
    /** drag communication with pair sub-views: dragend - remove the placeholder */
    _pairDragend : function( ev, pair ){
        //console.debug( '_pairDragend', ev, pair )
        $( '.paired-drop-placeholder' ).remove();
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

    /** handle a collection name change */
    _changeName : function( ev ){
        this._validationWarning( 'name', !!this._getName() );
    },

    /** get the current collection name */
    _getName : function(){
        return _.escape( this.$( '.collection-name' ).val() );
    },

    /** attempt to create the current collection */
    _clickCreate : function( ev ){
        var name = this._getName();
        if( !name ){
            this._validationWarning( 'name' );
        } else {
            this.createList();
        }
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
    toString : function(){ return 'PairedCollectionCreator'; }
});


//TODO: move to require text plugin and load these as text
//TODO: underscore currently unnecc. bc no vars are used
//TODO: better way of localizing text-nodes in long strings
/** underscore template fns attached to class */
PairedCollectionCreator.templates = PairedCollectionCreator.templates || {

    /** the skeleton */
    main : _.template([
        '<div class="header flex-row no-flex"></div>',
        '<div class="middle flex-row flex-row-container"></div>',
        '<div class="footer flex-row no-flex">'
    ].join('')),

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
                '<label class="remove-extensions-prompt pull-right">',
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
};


//=============================================================================
(function(){
    /** plugin that will highlight an element when this element is hovered over */
    jQuery.fn.extend({
        hoverhighlight : function $hoverhighlight( scope, color ){
            scope = scope || 'body';
            if( !this.size() ){ return this; }

            $( this ).each( function(){
                var $this = $( this ),
                    targetSelector = $this.data( 'target' );

                if( targetSelector ){
                    $this.mouseover( function( ev ){
                        $( targetSelector, scope ).css({
                            background: color
                        });
                    })
                    .mouseout( function( ev ){
                        $( targetSelector ).css({
                            background: ''
                        });
                    });
                }
            });
            return this;
        }
    });
}());


//=============================================================================
/** a modal version of the paired collection creator */
var pairedCollectionCreatorModal = function _pairedCollectionCreatorModal( datasets, options ){
    options = _.defaults( options || {}, {
        datasets    : datasets,
        oncancel    : function(){ Galaxy.modal.hide(); },
        oncreate    : function(){
            Galaxy.modal.hide();
            Galaxy.currHistoryPanel.refreshContents();
        }
    });

    if( !window.Galaxy || !Galaxy.modal ){
        throw new Error( 'Galaxy or Galaxy.modal not found' );
    }

    var creator = new PairedCollectionCreator( options ).render();
    Galaxy.modal.show({
        title   : 'Create a collection of paired datasets',
        body    : creator.$el,
        width   : '80%',
        height  : '800px',
        closing_events: true
    });
    //TODO: remove modal header
    window.PCC = creator;
    return creator;
};


//=============================================================================
    return {
        PairedCollectionCreator : PairedCollectionCreator,
        pairedCollectionCreatorModal : pairedCollectionCreatorModal
    };
});
