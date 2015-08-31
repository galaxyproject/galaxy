define([
    "mvc/history/history-model",
    "mvc/history/history-panel-edit",
    "mvc/base-mvc",
    "utils/ajax-queue",
    "ui/mode-button",
    "ui/search-input"
], function( HISTORY_MODEL, HPANEL_EDIT, baseMVC, ajaxQueue ){
//==============================================================================
/**  */
function historyCopyDialog( history, options ){
    options = options || {};
    // fall back to un-notifying copy
    if( !( Galaxy && Galaxy.modal ) ){
        return history.copy();
    }

    // maybe better as multiselect dialog?
    var historyName = history.get( 'name' ),
        defaultCopyName = "Copy of '" + historyName + "'";

    function validateName( name ){
        if( !name ){
            if( !Galaxy.modal.$( '#invalid-title' ).size() ){
                var $invalidTitle = $( '<p/>' ).attr( 'id', 'invalid-title' )
                    .css({ color: 'red', 'margin-top': '8px' })
                    .addClass( 'bg-danger' ).text( _l( 'Please enter a valid history title' ) );
                Galaxy.modal.$( '.modal-body' ).append( $invalidTitle );
            }
            return false;
        }
        return name;
    }

    function copyHistory( name ){
        var $copyIndicator = $( '<p><span class="fa fa-spinner fa-spin"></span> Copying history...</p>' )
            .css( 'margin-top', '8px' );
        Galaxy.modal.$( '.modal-body' ).append( $copyIndicator );
        history.copy( true, name )
            //TODO: make this unneccessary with pub-sub error
            .fail( function(){
                alert( _l( 'History could not be copied. Please contact a Galaxy administrator' ) );
            })
            .always( function(){
                Galaxy.modal.hide();
            });
    }
    function checkNameAndCopy(){
        var name = Galaxy.modal.$( '#copy-modal-title' ).val();
        if( !validateName( name ) ){ return; }
        copyHistory( name );
    }

    Galaxy.modal.show( _.extend({
        title   : _l( 'Copying history' ) + ' "' + historyName + '"',
        body    : $([
                '<label for="copy-modal-title">',
                    _l( 'Enter a title for the copied history' ), ':',
                '</label><br />',
                '<input id="copy-modal-title" class="form-control" style="width: 100%" value="',
                    defaultCopyName, '" />'
            ].join('')),
        buttons : {
            'Cancel' : function(){ Galaxy.modal.hide(); },
            'Copy'   : checkNameAndCopy
        }
    }, options ));
    $( '#copy-modal-title' ).focus().select();
    $( '#copy-modal-title' ).on( 'keydown', function( ev ){
        if( ev.keyCode === 13 ){
            checkNameAndCopy();
        }
    });
}


/* ==============================================================================
TODO:
    rendering/delayed rendering is a mess
        may not need to render columns in renderColumns (just moving them/attaching them may be enough)
    copy places old current in wrong location
    handle delete current
        currently manual by user - delete then create new - make one step
    render
        move all columns over as one (agg. then html())
    performance
        rendering columns could be better
    move in-view from pubsub

    handle errors
    handle no histories
    handle no histories found

    include hidden/deleted
        allow toggling w/o setting in storage
    reloading with expanded collections doesn't get details of that collection

    change includeDeleted to an ajax call

    better narrowing

    privatize non-interface fns
    search for and drag and drop - should reset after dataset is loaded (or alt. clear search)
    ?columns should be a panel, not have a panel

============================================================================== */
/** @class A container for a history panel that renders controls for that history (delete, copy, etc.)
 */
var HistoryPanelColumn = Backbone.View.extend( baseMVC.LoggableMixin ).extend({
//TODO: extend from panel? (instead of aggregating)

    //logger : console,

    tagName     : 'div',
    className   : 'history-column flex-column flex-row-container',
    id : function id(){
        if( !this.model ){ return ''; }
        return 'history-column-' + this.model.get( 'id' );
    },

    // ------------------------------------------------------------------------ set up
    /** set up passed-in panel (if any) and listeners */
    initialize : function initialize( options ){
        options = options || {};
        this.purgeAllowed = !_.isUndefined( options.purgeAllowed )? options.purgeAllowed: false;
        this.panel = options.panel || this.createPanel( options );

        this.setUpListeners();
    },

    /** create a history panel for this column */
    createPanel : function createPanel( panelOptions ){
        panelOptions = _.extend({
            model       : this.model,
            //el          : this.$panel(),
            // non-current panels should set their hdas to draggable
            purgeAllowed: this.purgeAllowed,
            dragItems   : true
        }, panelOptions );
        //this.log( 'panelOptions:', panelOptions );
//TODO: use current-history-panel for current
        var panel = new HPANEL_EDIT.HistoryPanelEdit( panelOptions );
        panel._renderEmptyMessage = this.__patch_renderEmptyMessage;
        return panel;
    },

//TODO: move to stub-class to avoid monkey-patching
    /** the function monkey-patched into panels to show contents loading state */
    __patch_renderEmptyMessage : function( $whereTo ){
        var panel = this,
            // a more useful attribute, but does not account for collections (for some reason)
            // hdaCount = _.chain( this.model.get( 'state_ids' ) ).values().flatten().value().length,
            empty = panel.model.get( 'empty' ),
            newMsg,
            $emptyMsg = panel.$emptyMessage( $whereTo );

        if( !_.isEmpty( panel.hdaViews ) ){
            return $emptyMsg.hide();
        }

        if( empty ){
            newMsg = panel.emptyMsg;

        } else if( !this.model.contents.length ){
            newMsg = '<span class="fa fa-spinner fa-spin"></span> <i>' + _l( 'loading datasets' ) + '...</i>';

        } if( panel.searchFor ){
            // this is a hack until HDCAs implement searching and haveDetails entirely
            var mixed = !!panel.model.contents.find( function( c ){
                return c.get( 'model_class' ) !== 'HistoryDatasetAssociation';
            });
            if( !mixed && !panel.model.contents.haveDetails() ){
                newMsg = '<span class="fa fa-spinner fa-spin"></span> <i>' + _l( 'searching' ) + '...</i>';

            } else {
                newMsg = panel.noneFoundMsg;
            }
        }
        return $emptyMsg.empty().append( newMsg ).show();
    },

    /** set up reflexive listeners */
    setUpListeners : function setUpListeners(){
        var column = this;
        //this.log( 'setUpListeners', this );
        this.once( 'rendered', function(){
            column.trigger( 'rendered:initial', column );
        });
        this.setUpPanelListeners();
    },

    /** set listeners needed for panel */
    setUpPanelListeners : function setUpPanelListeners(){
        var column = this;
        this.listenTo( this.panel, {
            //'all': function(){ console.info( 'panel of ' + this, arguments ); },

            // assumes panel will take the longest to render
            'rendered': function(){
                column.trigger( 'rendered', column );
            }
        }, this );
    },

    /** do the dimensions of this column overlap the given (horizontal) browser coords? */
    inView : function( viewLeft, viewRight ){
//TODO: offset is expensive
        var columnLeft = this.$el.offset().left,
            columnRight = columnLeft + this.$el.width();
        if( columnRight < viewLeft ){ return false; }
        if( columnLeft > viewRight ){ return false; }
        return true;
    },

    /** shortcut to the panel */
    $panel : function $panel(){
        return this.$( '.history-panel' );
    },

    // ------------------------------------------------------------------------ render
    /** render ths column, its panel, and set up plugins */
    render : function render( speed ){
        speed = ( speed !== undefined )?( speed ):( 'fast' );
        //this.log( this + '.render', this.$el, this.el );
        //TODO: not needed
        var modelData = this.model? this.model.toJSON(): {};
        this.$el.html( this.template( modelData ) );
        this.renderPanel( speed );
        // if model and not children
            // template
            // render controls
        this.setUpBehaviors();
        // add panel
        return this;
    },

    /** set up plugins */
    setUpBehaviors : function setUpBehaviors(){
        //this.log( 'setUpBehaviors:', this );
        //var column = this;
        // on panel size change, ...
    },

    /** column body template with inner div for panel based on data (model json) */
    template : function template( data ){
        data = _.extend( data || {}, {
            isCurrentHistory : this.currentHistory
        });
        return $([
            '<div class="panel-controls clear flex-row">',
                this.controlsLeftTemplate({ history: data, view: this }),
                //'<button class="btn btn-default">Herp</button>',
                this.controlsRightTemplate({ history: data, view: this }),
            '</div>',
            '<div class="inner flex-row flex-column-container">',
                '<div id="history-', data.id, '" class="history-column history-panel flex-column"></div>',
            '</div>'
        ].join( '' ));
    },

    /** render the panel contained in the column using speed for fx speed */
    renderPanel : function renderPanel( speed ){
        speed = ( speed !== undefined )?( speed ):( 'fast' );
        this.panel.setElement( this.$panel() ).render( speed );
        if( this.currentHistory ){
            this.panel.$list().before( this.panel._renderDropTargetHelp() );
        }
        return this;
    },

    // ------------------------------------------------------------------------ behaviors and events
    /** event map */
    events : {
        // will make this the current history
        'click .switch-to.btn'      : function(){ this.model.setAsCurrent(); },
        //TODO: remove boiler plate from next 3
        'click .delete-history' : function(){
            var column = this;
            this.model._delete()
                .fail( function( xhr, status, error ){
                    alert( _l( 'Could not delete the history' ) + ':\n' + error );
                })
                .done( function( data ){
                    column.render();
                });
        },
        'click .undelete-history' : function(){
            var column = this;
            this.model.undelete()
                .fail( function( xhr, status, error ){
                    alert( _l( 'Could not undelete the history' ) + ':\n' + error );
                })
                .done( function( data ){
                    column.render();
                });
        },
        'click .purge-history' : function(){
            if( confirm( _l( 'This will permanently remove the data. Are you sure?' ) ) ){
                var column = this;
                this.model.purge()
                    .fail( function( xhr, status, error ){
                        alert( _l( 'Could not purge the history' ) + ':\n' + error );
                    })
                    .done( function( data ){
                        column.render();
                    });
            }
        },
        // will copy this history and make the copy the current history
        'click .copy-history'       : 'copy'
    },

    // ------------------------------------------------------------------------ non-current controls
    /** Open a modal to get a new history name, copy it (if not canceled), and makes the copy current */
    copy : function copy(){
        historyCopyDialog( this.model );
    },

    // ------------------------------------------------------------------------ templates
    /** controls template displaying controls above the panel based on this.currentHistory */
    controlsLeftTemplate : _.template([
        '<div class="pull-left">',
            '<% if( data.history.isCurrentHistory ){ %>',
                '<strong class="current-label">', _l( 'Current History' ), '</strong>',
            '<% } else { %>',
                '<button class="switch-to btn btn-default">', _l( 'Switch to' ), '</button>',
            '<% } %>',
        '</div>'
    ].join( '' ), { variable : 'data' }),

    /** controls template displaying controls above the panel based on this.currentHistory */
    controlsRightTemplate : _.template([
        '<div class="pull-right">',
            '<% if( !data.history.purged ){ %>',
                '<div class="panel-menu btn-group">',
                    '<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown">',
                        '<span class="caret"></span>',
                    '</button>',
                    '<ul class="dropdown-menu pull-right" role="menu">',
                        '<% if( !data.history.deleted ){ %>',
                            '<li><a href="javascript:void(0);" class="copy-history">',
                                _l( 'Copy' ),
                            '</a></li>',
                            //'<li><a href="javascript:void(0);" class="publish-history">',
                            //    _l( 'Publish' ),
                            //'</a></li>',
                            '<li><a href="javascript:void(0);" class="delete-history">',
                                _l( 'Delete' ),
                            '</a></li>',
                        '<% } else /* if is deleted */ { %>',
                            '<li><a href="javascript:void(0);" class="undelete-history">',
                                _l( 'Undelete' ),
                            '</a></li>',
                        '<% } %>',
                        '<% if( data.view.purgeAllowed ){ %>',
                            '<li><a href="javascript:void(0);" class="purge-history">',
                                _l( 'Purge' ),
                            '</a></li>',
                        '<% } %>',
                    '</ul>',
                '</div>',
            '<% } %>',
        '</div>'
    ].join( '' ), { variable: 'data' }),

    // ------------------------------------------------------------------------ misc
    /** String rep */
    toString : function(){
        return 'HistoryPanelColumn(' + ( this.panel? this.panel : '' ) + ')';
    }
});


//==============================================================================
/** @class A view of a HistoryCollection and displays histories similarly to the current history panel.
 */
var MultiPanelColumns = Backbone.View.extend( baseMVC.LoggableMixin ).extend({

    //logger : console,
    className : 'multi-panel-history',

    // ------------------------------------------------------------------------ set up
    /** Set up internals, history collection, and columns to display the history */
    initialize : function initialize( options ){
        options = options || {};
        this.log( this + '.init', options );

        // add the className here (since we gen. pass the el in options)
        this.$el.addClass( this.className );

        // --- instance vars
        //TODO: move these to some defaults
        this.options = {
            columnWidth     : 312,
            borderWidth     : 1,
            columnGap       : 8,
            headerHeight    : 29,
            footerHeight    : 0,
            controlsHeight  : 20
        };

        /** how many histories to get when fetching a new batch/page */
        this.perPage = options.perPage || 10;

        /** named ajax queue for loading hdas */
        this.hdaQueue = new ajaxQueue.NamedAjaxQueue( [], false );

        // --- set up models, sub-views, and listeners
        /** the original unfiltered and unordered collection of histories */
        this.collection = null;
        /** model id to column map */
        this.columnMap = {};
        /** model id to column map */
        this.columnOptions = options.columnOptions || {};

        /** what to search for within all histories */
        this.historySearch = null;
        /** what to search for within all datasets */
        this.datasetSearch = null;

        this.setCollection( options.histories );
        this.setUpListeners();
    },

    /** Set up reflexive listeners */
    setUpListeners : function setUpListeners(){
        var multipanel = this;
        //multipanel.log( 'setUpListeners', multipanel );
        this.on( 'end-of-scroll', function(){
            multipanel.collection.fetch({ limit : multipanel.perPage });
        });
    },

    // ------------------------------------------------------------------------ collection
    /** Set up a (new) history collection, sorting and adding listeners
     *  @fires 'new-collection' when set with this view as the arg
     */
    setCollection : function setCollection( collection ){
        this.stopListening( this.collection );

        this.collection = collection || new HISTORY_MODEL.HistoryCollection();
        this.collection.allFetched = !this.perPage || ( this.collection.length < this.perPage );
        this.setUpCollectionListeners();

        this.collection.sort({ silent : true });
        this.createColumns();
        this.hdaQueue.clear();

        // multipanel.addModels( collection, { silent: true });
        this.trigger( 'new-collection', this );
        return this;
    },

    /** Set up a (new) history collection, sorting and adding listeners
     *  @fires 'new-collection' when set with this view as the arg
     */
    addModels : function setCollection( models, collection, options ){
        options = options || {};
        var multipanel = this;
        models = _.isArray( models )? models : [ models ];
        models.forEach( function( model ){
            multipanel.addColumn( model, false );
        });
        return this;
    },

    /** Set up listeners for the collection - handling: added histories, change of current, deletion, and sorting */
    setUpCollectionListeners : function(){
        var multipanel = this;
        multipanel.listenTo( multipanel.collection, {
            // handle ajax errors from the collection
            'error'                         : multipanel._ajaxErrorHandler,
            // add multiple models
            'add'                           : multipanel.addModels,
            // when all the histories a user has have been fetched
            'all-fetched'                   : multipanel._postFetchAll,
            // handle addition of histories, triggered by column copy and create new
            'new-current'                   : multipanel.addAsCurrentColumn,
            // handle setting a history as current, triggered by history.setAsCurrent
            'set-as-current'                : multipanel.setCurrentHistory,
            // handle deleting a history (depends on whether panels is including deleted or not)
            'change:deleted change:purged'  : multipanel.handleDeletedHistory,
            // re-render columns after a sort
            'sort' : function(){
                multipanel.renderColumns( 0 );
            },
        });
    },

    _postFetchAll : function( fetchData ){
        this.$( '.histories-loading-indicator' ).remove();
        // when new histories is fetched and the indicator is not required,
        // the panel will jump slightly left - totally aesthetic but jarring
        // TODO: this probably would be best handled elsewhere during a refinement cycle (if any)
        if( !this.historySearch ){
            var $scrollContainer = this.$( '.outer-middle' );
            $scrollContainer.scrollLeft( $scrollContainer.scrollLeft() + 24 );
        }
    },

    /** Re-render and set currentHistoryId to reflect a new current history */
    setCurrentHistory : function setCurrentHistory( history ){
        var oldCurrentColumn = _.findWhere( this.columnMap, { currentHistory: true });
        if( oldCurrentColumn ){
            oldCurrentColumn.currentHistory = false;
            oldCurrentColumn.$el.height( '' );
        }

        var newCurrentColumn = this.columnMap[ this.collection.currentHistoryId ];
        newCurrentColumn.currentHistory = true;
        this.collection.sort();
        this._recalcFirstColumnHeight();
        return newCurrentColumn;
    },

    /** Either remove a deleted history or re-render it to show the deleted message
     *      based on collection.includeDeleted
     */
    handleDeletedHistory : function handleDeletedHistory( history ){
        if( history.get( 'deleted' ) || history.get( 'purged' ) ){
            this.log( 'handleDeletedHistory', this.collection.includeDeleted, history );
            var multipanel = this;
                column = multipanel.columnMap[ history.id ];
            if( !column ){ return; }

            // if it's the current column, create a new, empty history as the new current
            if( column.model.id === this.collection.currentHistoryId ){
                //TODO: figuring out the order of async here is tricky
                //  - for now let the user handle the two step process
                //multipanel.collection.create().done( function(){
                //    if( !multipanel.collection.includeDeleted ){ multipanel.removeColumn( column, false ); }
                //});
            } else if( !multipanel.collection.includeDeleted ){
                multipanel.removeColumn( column );
            }
       }
    },

    /** If Galaxy object is available handle error there, otherwise, locally (and crudely) */
    _ajaxErrorHandler : function(){
        var errArgs = _.toArray( arguments );
        if( window.Galaxy && Galaxy.handleErrors ){
            Galaxy.handleErrors.apply( Galaxy, errArgs );
        } else {
            alert( _l( 'There was a problem getting data from the server' ) );
            console.error( errArgs[0].responseText );
        }
    },

    /** create a new history and set it to current */
    create : function( ev ){
        return this.collection.create({ current: true });
    },

    // ------------------------------------------------------------------------ columns
    /** create columns from collection */
    createColumns : function createColumns( models, columnOptions ){
        columnOptions = columnOptions || this.options.columnOptions;
        var multipanel = this;
        // clear column map
        // TODO: make cummulative
        multipanel.columnMap = {};
        multipanel.collection.each( function( model, i ){
            var column = multipanel.createColumn( model, columnOptions );
            multipanel.columnMap[ model.id ] = column;
        });
    },

    /** create a column and its panel and set up any listeners to them */
    createColumn : function createColumn( history, options ){
        // options passed can be re-used, so extend them before adding the model to prevent pollution for the next
        options = _.extend( {}, options, {
            model       : history,
            purgeAllowed: Galaxy.config.allow_user_dataset_purge
        });
        var column = new HistoryPanelColumn( options );
        if( history.id === this.collection.currentHistoryId ){ column.currentHistory = true; }
        this.setUpColumnListeners( column );
        if( this.datasetSearch ){
            column.panel.searchItems( this.datasetSearch );
            this.queueHdaFetchDetails( column );
        }
        return column;
    },

    /** add a new column for history and render all columns if render is true */
    addColumn : function add( history, render ){
        //this.debug( 'adding column for:', history );
        render = render !== undefined? render : true;
        var newColumn = this.createColumn( history );
        this.columnMap[ history.id ] = newColumn;
        if( render ){
            this.renderColumns();
        }
        return newColumn;
    },

    /** add a new column for history and make it the current history/column */
    addAsCurrentColumn : function add( history, collection, options ){
        //this.log( 'adding current column for:', history );
        var multipanel = this,
            newColumn = this.addColumn( history, false );
        this.setCurrentHistory( history );
        newColumn.once( 'rendered', function(){
            multipanel.queueHdaFetch( newColumn );
        });
        return newColumn;
    },

    /** remove the given column, it's listeners, and optionally render */
    removeColumn : function remove( column, render ){
        render = render !== undefined? render : true;
        this.log( 'removeColumn', column );
        if( !column ){ return; }
        var multipanel = this,
            widthToRemove = this.options.columnWidth + this.options.columnGap;
        column.$el.fadeOut( 'fast', function(){
            if( render ){
                $( this ).remove();
                multipanel.$( '.middle' ).width( multipanel.$( '.middle' ).width() - widthToRemove );
                multipanel.checkColumnsInView();
                multipanel._recalcFirstColumnHeight();
            }

        //TODO: to freeColumn (where Columns have freePanel)
            multipanel.stopListening( column.panel );
            multipanel.stopListening( column );
            delete multipanel.columnMap[ column.model.id ];
            column.remove();
        });
    },

    /** set up listeners for a column and it's panel - handling: hda lazy-loading, drag and drop */
    setUpColumnListeners : function setUpColumnListeners( column ){
        var multipanel = this;
        multipanel.listenTo( column, {
            //'all': function(){ console.info( 'column ' + column + ':', arguments ) },
            'in-view': multipanel.queueHdaFetch
        });

        multipanel.listenTo( column.panel, {
            //'all': function(){ console.info( 'panel ' + column.panel + ':', arguments ) },

            'view:draggable:dragstart': function( ev, view, panel, column ){
                multipanel._dropData = JSON.parse( ev.dataTransfer.getData( 'text' ) );
                multipanel.currentColumnDropTargetOn();
            },
            'view:draggable:dragend': function( ev, view, panel, column ){
                multipanel._dropData = null;
                multipanel.currentColumnDropTargetOff();
            },
           'droptarget:drop': function( ev, data, panel ){
                //note: bad copy sources fail silently
                var toCopy = multipanel._dropData.filter( function( json ){
                    return panel.model.contents.isCopyable( json );
                });
                multipanel._dropData = null;

                var queue = new ajaxQueue.NamedAjaxQueue();
                toCopy.forEach( function( content ){
                    queue.add({
                        name : 'copy-' + content.id,
                        fn : function(){
                            return panel.model.contents.copy( content );
                        }
                    });
                });
                queue.start();
                queue.done( function( responses ){
                    panel.model.fetch();
                });
            }
         });
    },

    /** conv. fn to count the columns in columnMap */
    columnMapLength : function(){
        return Object.keys( this.columnMap ).length;
    },

    /** return array of Columns filtered by filters and sorted to match the collection
     *  @param: filters Function[] array of filter fns
     */
    sortedFilteredColumns : function( filters ){
        filters = filters || this.filters;
        if( !filters || !filters.length ){
            return this.sortedColumns();
        }
        var multipanel = this;
        return multipanel.sortedColumns().filter( function( column, index ){
            var filtered = column.currentHistory || _.every( filters.map( function( filter ){
                return filter.call( column );
            }));
            return filtered;
        });
    },

    /** return array of Columns sorted to match the collection */
    sortedColumns : function(){
        var multipanel = this;
        var sorted = this.collection.map( function( history, index ){
            return multipanel.columnMap[ history.id ];
        });
        return sorted;
    },

    // ------------------------------------------------------------------------ render
    /** Render this view, columns, and set up view plugins */
    render : function render( speed ){
        speed = speed !== undefined? speed: this.fxSpeed;
        var multipanel = this;

        multipanel.log( multipanel + '.render' );
        multipanel.$el.html( multipanel.mainTemplate( multipanel ) );
        multipanel.renderColumns( speed );

        // set the columns to full height allowed and set up behaviors for thie multipanel
        multipanel.setUpBehaviors();
        //TODO: wrong - has to wait for columns to render
        //  - create a column listener that fires this when all columns are rendered
        multipanel.trigger( 'rendered', multipanel );
        return multipanel;
    },

    /** Render the columns and panels */
    renderColumns : function renderColumns( speed ){
        speed = speed !== undefined? speed: this.fxSpeed;
        //this.log( 'renderColumns:', speed );
        // render columns and track the total number rendered, firing an event when all are rendered
        var multipanel = this,
            sortedAndFiltered = multipanel.sortedFilteredColumns();
        //this.log( '\t sortedAndFiltered:', sortedAndFiltered );

        // set up width based on collection size
        var $middle = multipanel.$( '.middle' ).empty()
            .width( multipanel._calcMiddleWidth( sortedAndFiltered.length ) );

        sortedAndFiltered.forEach( function( column, i ){
            column.$el.appendTo( $middle );
            column.delegateEvents();
            multipanel.renderColumn( column, speed );
        });
        if( !multipanel.collection.allFetched ){
            $middle.append( multipanel.loadingIndicatorTemplate( multipanel ) );
        }
        //TODO: sorta - at least their fx queue has started the re-rendering
        multipanel.trigger( 'columns-rendered', sortedAndFiltered, multipanel );

        if( multipanel.datasetSearch && sortedAndFiltered.length <= 1 ){
        } else {
            // check for in-view, hda lazy-loading if so
            multipanel.checkColumnsInView();
            // the first, current column has position: fixed and flex css will not apply - adjust height manually
            multipanel._recalcFirstColumnHeight();
        }
        return sortedAndFiltered;
    },

    _calcMiddleWidth : function( numColumns ){
        var preventStackWidthAdj = 16;
        return (
            numColumns * ( this.options.columnWidth + this.options.columnGap ) +
            // last column gap
            this.options.columnGap +
            // the amount that safely prevents stacking of columns when adding a new one
            preventStackWidthAdj
        );
    },

    /** Render a single column using the non-blocking setTimeout( 0 ) pattern */
    renderColumn : function( column, speed ){
        speed = speed !== undefined? speed: this.fxSpeed;
        return column.render( speed );
    },

    //TODO: combine the following two more sensibly
    //TODO: could have HistoryContents.haveDetails return false
    //      if column.model.contents.length === 0 && !column.model.get( 'empty' ) then just check that
    /** Get the *summary* contents of a column's history (and details on any expanded contents),
     *      queueing the ajax call and using a named queue to prevent the call being sent twice
     */
    queueHdaFetch : function queueHdaFetch( column ){
        //this.log( 'queueHdaFetch:', column );
        // if the history model says it has hdas but none are present, queue an ajax req for them
        if( column.model.contents.length === 0 && !column.model.get( 'empty' ) ){
            //this.log( '\t fetch needed:', column );
            var xhrData = {},
                ids = _.values( column.panel.storage.get( 'expandedIds' ) ).join();
            if( ids ){
                xhrData.dataset_details = ids;
            }
            // this uses a 'named' queue so that duplicate requests are ignored
            this.hdaQueue.add({
                name : column.model.id,
                fn : function(){
                    var xhr = column.model.contents.fetch({ data: xhrData, silent: true });
                    return xhr.done( function( response ){
                        column.panel.renderItems();
                    });
                }
            });
            // the queue is re-used, so if it's not processing requests - start it again
            if( !this.hdaQueue.running ){ this.hdaQueue.start(); }
        }
    },

    /** Get the *detailed* json for *all* of a column's history's contents - req'd for searching */
    queueHdaFetchDetails : function( column ){
        if( ( column.model.contents.length === 0 && !column.model.get( 'empty' ) )
        ||  ( !column.model.contents.haveDetails() ) ){
            // this uses a 'named' queue so that duplicate requests are ignored
            this.hdaQueue.add({
                name : column.model.id,
                fn : function(){
                    var xhr = column.model.contents.fetch({ data: { details: 'all' }, silent: true });
                    return xhr.done( function( response ){
                        column.panel.renderItems();
                    });
                }
            });
            // the queue is re-used, so if it's not processing requests - start it again
            if( !this.hdaQueue.running ){ this.hdaQueue.start(); }
        }
    },

    /** put a text msg in the header */
    renderInfo : function( msg ){
        return this.$( '.header .header-info' ).text( msg );
    },

    // ------------------------------------------------------------------------ events/behaviors
    /**  */
    events : {
        // will move to the server root (gen. Analyze data)
        'click .done.btn'           : 'close',
        // creates a new empty history and makes it current
        'click .create-new.btn'     : 'create',
        'click #include-deleted'    : '_clickToggleDeletedHistories',
        // these change the collection and column sort order
        'click .order .set-order'   : '_chooseOrder',
        'click #toggle-deleted'     : '_clickToggleDeletedDatasets',
        'click #toggle-hidden'      : '_clickToggleHiddenDatasets',
        //'dragstart .list-item .title-bar'                       : function( e ){ console.debug( 'ok' ); }
    },

    close : function( ev ){
        //TODO: switch to pushState/router
        var destination = '/';
        if( Galaxy && Galaxy.options && Galaxy.options.root ){
            destination = Galaxy.options.root;
        } else if( galaxy_config && galaxy_config.root ){
            destination = galaxy_config.root;
        }
        window.location = destination;
    },

    _clickToggleDeletedHistories : function( ev ){
        this.toggleDeletedHistories( $( ev.currentTarget ).is( ':checked' ) );
        this.toggleOptionsPopover();
    },
    /** Include deleted histories in the collection */
    toggleDeletedHistories : function( show ){
        if( show ){
            window.location = Galaxy.options.root + 'history/view_multiple?include_deleted_histories=True';
        } else {
            window.location = Galaxy.options.root + 'history/view_multiple';
        }
    },

    _clickToggleDeletedDatasets : function( ev ){
        this.toggleDeletedDatasets( $( ev.currentTarget ).is( ':checked' ) );
        this.toggleOptionsPopover();
    },
    toggleDeletedDatasets : function( show ){
        show = show !== undefined? show : false;
        var multipanel = this;
        multipanel.sortedFilteredColumns().forEach( function( column, i ){
            _.delay( function(){
                column.panel.toggleShowDeleted( show, false );
            }, i * 200 );
        });
    },

    _clickToggleHiddenDatasets : function( ev ){
        this.toggleHiddenDatasets( $( ev.currentTarget ).is( ':checked' ) );
        this.toggleOptionsPopover();
    },
    toggleHiddenDatasets : function( show ){
        show = show !== undefined? show : false;
        var multipanel = this;
        multipanel.sortedFilteredColumns().forEach( function( column, i ){
            _.delay( function(){
                column.panel.toggleShowHidden( show, false );
            }, i * 200 );
        });
    },

    /** change the collection order and re-fetch when the drop down in the options menu is changed */
    _chooseOrder : function( ev ){
        var multipanel = this,
            collection = multipanel.collection,
            orderKey = $( ev.currentTarget ).data( 'order' );
        // set the sort order text also
        multipanel.$( '.current-order' ).text( multipanel.orderDescriptions[ orderKey ] );
        multipanel.toggleOptionsPopover();

        // set the order and re-fetch using the new order
        collection.setOrder( orderKey );
        collection.reset( collection.slice( 0, 1 ), { silent : true });
        multipanel.setCollection( collection );
        collection.fetch({ limit : multipanel.perPage });
        multipanel.once( 'columns-rendered', multipanel._scrollLeft, this );
        //TODO: check allFetched and do not reset if so - just sort instead
    },

    /** scroll the column container right or left */
    _scrollLeft : function( val ){
        this.$( '.outer-middle' ).scrollLeft( val || 0 );
    },

    /** Set up any view plugins */
    setUpBehaviors : function(){
        var multipanel = this;
        multipanel._moreOptionsPopover();

        // input to search histories
        multipanel.$( '#search-histories' ).searchInput({
            name        : 'search-histories',
            placeholder : _l( 'search histories' ),

            onfirstsearch : function( searchFor ){
                multipanel.$( '#search-histories' ).searchInput( 'toggle-loading' );
                multipanel.renderInfo( _l( 'loading all histories for search' ) );
                multipanel.collection.fetch()
                    .done( function(){
                        multipanel.$( '#search-histories' ).searchInput( 'toggle-loading' );
                        multipanel.renderInfo( '' );
                    });
            },
            onsearch    : function( searchFor ){
                multipanel.historySearch = searchFor;
                multipanel.filters = [ function(){
                    return this.model.matchesAll( multipanel.historySearch );
                }];
                multipanel.renderColumns( 0 );
            },
            onclear     : function( searchFor ){
                multipanel.historySearch = null;
                //TODO: remove specifically not just reset
                multipanel.filters = [];
                multipanel.renderColumns( 0 );
            }
        });

        // input to search datasets
        multipanel.$( '#search-datasets' ).searchInput({
            name        : 'search-datasets',
            placeholder : _l( 'search all datasets' ),

            onfirstsearch : function( searchFor ){
                multipanel.hdaQueue.clear();
                multipanel.$( '#search-datasets' ).searchInput( 'toggle-loading' );
                multipanel.datasetSearch = searchFor;
                multipanel.sortedFilteredColumns().forEach( function( column ){
                    column.panel.searchItems( searchFor );
                    // load details for them that need
                    multipanel.queueHdaFetchDetails( column );
                });
                multipanel.hdaQueue.progress( function( progress ){
                    multipanel.renderInfo([
                        _l( 'searching' ), ( progress.curr + 1 ), _l( 'of' ), progress.total
                    ].join( ' ' ));
                });
                multipanel.hdaQueue.deferred.done( function(){
                    multipanel.renderInfo( '' );
                    multipanel.$( '#search-datasets' ).searchInput( 'toggle-loading' );
                });
            },
            onsearch    : function( searchFor ){
                multipanel.datasetSearch = searchFor;
                multipanel.sortedFilteredColumns().forEach( function( column ){
                    column.panel.searchItems( searchFor );
                });
            },
            onclear     : function( searchFor ){
                multipanel.datasetSearch = null;
                multipanel.sortedFilteredColumns().forEach( function( column ){
                    column.panel.clearSearch();
                });
            }
        });

        // resize first (fixed position) column on page resize
        $( window ).resize( function(){
            multipanel._recalcFirstColumnHeight();
        });

        // when scrolling - check for histories now in view: they will fire 'in-view' and queueHdaLoading if necc.
        //TODO:?? might be able to simplify and not use pub-sub
        var debouncedInView = _.debounce( function _debouncedInner(){
            var viewport = multipanel._viewport();
            multipanel.checkColumnsInView( viewport );
            multipanel.checkForEndOfScroll( viewport );
        }, 100 );
        this.$( '.middle' ).parent().scroll( debouncedInView );
    },

    /** create the options popover */
    _moreOptionsPopover : function(){
        return this.$( '.open-more-options.btn' ).popover({
            container   : '.header',
            placement   : 'bottom',
            html        : true,
            content     : $( this.optionsPopoverTemplate( this ) )
        });
    },

    /** change the collection order and re-fetch when the drop down in the options menu is changed */
    toggleOptionsPopover : function( ev ){
        // hide seems broken in our version
        this.$( '.open-more-options.btn' ).popover( 'toggle' );
    },

    /** Adjust the height of the first, current column since flex-boxes won't work with fixed postiion elements */
    _recalcFirstColumnHeight : function(){
        var $firstColumn = this.$( '.history-column' ).first(),
            middleHeight = this.$( '.middle' ).height(),
            controlHeight = $firstColumn.find( '.panel-controls' ).height();
        $firstColumn.height( middleHeight )
            .find( '.inner' ).height( middleHeight - controlHeight );
    },

    /** Get the left and right pixel coords of the middle element */
    _viewport : function(){
        var $outerMiddle = this.$( '.middle' ).parent(),
            viewLeft = $outerMiddle.offset().left,
            width = $outerMiddle.width();
        return {
            left    : viewLeft,
            right   : viewLeft + width
        };
    },

    /** returns the columns currently in the viewport */
    columnsInView : function( viewport ){
        //TODO: uses offset which is render intensive
        //TODO: 2N - could use arg filter (sortedFilteredColumns( filter )) instead
        var vp = viewport || this._viewport();
        return this.sortedFilteredColumns().filter( function( column ){
            return column.currentHistory || column.inView( vp.left, vp.right );
        });
    },

    //TODO: sortByInView - return cols in view, then others
    /** trigger in-view from columns in-view */
    checkColumnsInView : function(){
        //TODO: assbackward - don't fire from the column, fire from here and listen from here
        this.columnsInView().forEach( function( column ){
            column.trigger( 'in-view', column );
        });
    },

    /**  */
    checkForEndOfScroll : function( viewport ){
        viewport = viewport || this._viewport();
        var END_PADDING = 16,
            $middle = this.$( '.middle' ),
            scrollRight = $middle.parent().scrollLeft() + viewport.right;
        if( scrollRight >= ( $middle.width() - END_PADDING ) ){
            this.trigger( 'end-of-scroll' );
        }
    },

    /** Show and enable the current columns drop target */
    currentColumnDropTargetOn : function(){
        var currentColumn = this.columnMap[ this.collection.currentHistoryId ];
        if( !currentColumn ){ return; }
        //TODO: fix this - shouldn't need monkeypatch
        currentColumn.panel.dataDropped = function( data ){};
        currentColumn.panel.dropTargetOn();
    },

    /** Hide and disable the current columns drop target */
    currentColumnDropTargetOff : function(){
        var currentColumn = this.columnMap[ this.collection.currentHistoryId ];
        if( !currentColumn ){ return; }
        currentColumn.panel.dataDropped = HPANEL_EDIT.HistoryPanelEdit.prototype.dataDrop;
        // slight override of dropTargetOff to not erase drop-target-help
        currentColumn.panel.dropTarget = false;
        currentColumn.panel.$( '.history-drop-target' ).remove();
    },

    // ------------------------------------------------------------------------ misc
    /** String rep */
    toString : function(){
        return 'MultiPanelColumns(' + ( this.columns? this.columns.length : 0 ) + ')';
    },

    // ------------------------------------------------------------------------ templates
    mainTemplate : _.template([
        '<div class="header flex-column-container">',
            '<div class="control-column control-column-left flex-column">',
                '<button class="done btn btn-default" tabindex="1">', _l( 'Done' ), '</button>',
                '<div id="search-histories" class="search-control"></div>',
                '<div id="search-datasets" class="search-control"></div>',
                '<a class="open-more-options btn btn-default" tabindex="3">',
                    '<span class="fa fa-ellipsis-h"></span>',
                '</a>',
            '</div>',
            // feedback
            '<div class="control-column control-column-center flex-column">',
                '<div class="header-info">', '</div>',
            '</div>',
            '<div class="control-column control-column-right flex-column">',
                '<button class="create-new btn btn-default" tabindex="4">', _l( 'Create new' ), '</button> ',
            '</div>',
        '</div>',
        // middle - where the columns go
        '<div class="outer-middle flex-row flex-row-container">',
            '<div class="middle flex-column-container flex-row"></div>',
        '</div>',
        // footer
        '<div class="footer flex-column-container"></div>'
    ].join(''), { variable: 'view' }),

    loadingIndicatorTemplate : _.template([
        '<div class="histories-loading-indicator">',
            '<span class="fa fa-spin fa-spinner"></span>', _l( 'Loading histories' ), '...',
        '</div>'
    ].join(''), { variable: 'view' }),

    orderDescriptions : {
        'update_time'       : _l( 'most recent first' ),
        'update_time-asc'   : _l( 'least recent first' ),
        'name'              : _l( 'name, a to z' ),
        'name-dsc'          : _l( 'name, z to a' ),
        'size'              : _l( 'size, large to small' ),
        'size-asc'          : _l( 'size, small to large' )
    },

    optionsPopoverTemplate : _.template([
        '<div class="more-options">',
            '<div class="order btn-group">',
                '<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown">',
                    _l( 'Order histories by' ) + ' ',
                    '<span class="current-order"><%= view.orderDescriptions[ view.collection.order ] %></span> ',
                    '<span class="caret"></span>',
                '</button>',
                '<ul class="dropdown-menu" role="menu">',
                    '<% _.each( view.orderDescriptions, function( text, order ){ %>',
                        '<li><a href="javascript:void(0);" class="set-order" data-order="<%= order %>">',
                            '<%= text %>',
                        '</a></li>',
                    '<% }); %>',
                '</ul>',
            '</div>',

            '<div class="checkbox"><label><input id="include-deleted" type="checkbox"',
                '<%= view.collection.includeDeleted? " checked" : "" %>>',
                _l( 'Include deleted histories' ),
            '</label></div>',

            '<hr />',

            '<div class="checkbox"><label><input id="toggle-deleted" type="checkbox">',
                _l( 'Include deleted datasets' ),
            '</label></div>',
            '<div class="checkbox"><label><input id="toggle-hidden" type="checkbox">',
                _l( 'Include hidden datasets' ),
            '</label></div>',
        '</div>'
    ].join(''), { variable: 'view' })

});


//==============================================================================
    return {
        MultiPanelColumns : MultiPanelColumns
    };
});
