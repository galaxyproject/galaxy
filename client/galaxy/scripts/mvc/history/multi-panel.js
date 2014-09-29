define([
    "mvc/history/history-model",
    "mvc/history/history-panel-edit",
    "mvc/base-mvc",
    "utils/ajax-queue"
], function( HISTORY_MODEL, HPANEL_EDIT, baseMVC, ajaxQueue ){
window.HISTORY_MODEL = HISTORY_MODEL;
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
            'Copy'   : function(){
                var name = Galaxy.modal.$( '#copy-modal-title' ).val();
                if( !validateName( name ) ){ return; }
                copyHistory( name );
            }
        }
    }, options ));
    $( '#copy-modal-title' ).focus().select();
}


/* ==============================================================================
TODO:
    copy places old current in wrong location
    size not updating on dnd
    sort by size is broken
    handle delete current
        currently manual by user - delete then create new - make one step
    render
        move all columns over as one (agg. then html())
    loading indicator on startup
    loading indicators on histories (while queueHdaLoading)
        __panelPatchRenderEmptyMsg
    performance
        page load takes a while
            renders where blocking each other - used _.delay( 0 )
        sort takes a while
        rendering columns could be better
        lazy load history list
    move in-view from pubsub

    handle errors
    handle no histories
    handle no histories found

    handle anon
        no button
        error message on loading url direct
    include hidden/deleted
        allow toggling w/o setting in storage
    reloading with expanded collections doesn't get details of that collection

    change includeDeleted to an ajax call

    better narrowing

    privatize non-interface fns
    search for and drag and drop - should reset after dataset is loaded (or alt. clear search)
    better ajax error handling
    ?columns should be a panel, not have a panel

============================================================================== */
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
    /**  */
    initialize : function initialize( options ){
        options = options || {};

        //this.log( this + '.init', options );
        // if model, set up model
            // create panel sub-view
//TODO: use current-history-panel for current
        this.panel = options.panel || this.createPanel( options );
        this.setUpListeners();
    },

    /**  */
    createPanel : function createPanel( panelOptions ){
        panelOptions = _.extend({
            model       : this.model,
            //el          : this.$panel(),
            // non-current panels should set their hdas to draggable
            dragItems   : true
        }, panelOptions );
        //this.log( 'panelOptions:', panelOptions );
//TODO: use current-history-panel for current
        var panel = new HPANEL_EDIT.HistoryPanelEdit( panelOptions );
        panel._renderEmptyMessage = this.__patch_renderEmptyMessage;
        return panel;
    },

//TODO: needs work
    /**  */
    __patch_renderEmptyMessage : function( $whereTo ){
        var panel = this,
            hdaCount = _.chain( this.model.get( 'state_ids' ) ).values().flatten().value().length,
            $emptyMsg = panel.$emptyMessage( $whereTo );

        if( !_.isEmpty( panel.hdaViews ) ){
            $emptyMsg.hide();

        } else if( hdaCount && !this.model.contents.length ){
            $emptyMsg.empty()
                .append( $( '<span class="fa fa-spinner fa-spin"></span> <i>loading datasets...</i>' ) ).show();

        } else if( panel.searchFor ){
            $emptyMsg.text( panel.noneFoundMsg ).show();

        } else {
            $emptyMsg.text( panel.emptyMsg ).show();
        }
        return $emptyMsg;
    },

    /**  */
    setUpListeners : function setUpListeners(){
        var column = this;
        //this.log( 'setUpListeners', this );
        this.once( 'rendered', function(){
            column.trigger( 'rendered:initial', column );
        });
        this.setUpPanelListeners();
    },

    /**  */
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

    /**  */
    inView : function( viewLeft, viewRight ){
//TODO: offset is expensive
        var columnLeft = this.$el.offset().left,
            columnRight = columnLeft + this.$el.width();
        if( columnRight < viewLeft ){ return false; }
        if( columnLeft > viewRight ){ return false; }
        return true;
    },

    /**  */
    $panel : function $panel(){
        return this.$( '.history-panel' );
    },

    // ------------------------------------------------------------------------ render
    /**  */
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

    /**  */
    setUpBehaviors : function setUpBehaviors(){
        //this.log( 'setUpBehaviors:', this );
        //var column = this;
        // on panel size change, ...
    },

    /**  */
    template : function template( data ){
        data = data || {};
        var html = [
                '<div class="panel-controls clear flex-row">',
                    this.controlsLeftTemplate(),
                    //'<button class="btn btn-default">Herp</button>',
                    '<div class="pull-right">',
                        '<button class="delete-history btn btn-default">',
                            data.deleted? _l( 'Undelete' ): _l( 'Delete' ),
                        '</button>',
                        '<button class="copy-history btn btn-default">', _l( 'Copy' ), '</button>',
                    '</div>',
                '</div>',
                '<div class="inner flex-row flex-column-container">',
                    '<div id="history-', data.id, '" class="history-column history-panel flex-column"></div>',
                '</div>'
            ].join( '' );
        return $( html );
    },

    controlsLeftTemplate : function(){
        return ( this.currentHistory )?
            [
                '<div class="pull-left">',
                    '<button class="create-new btn btn-default">', _l( 'Create new' ), '</button> ',
                '</div>'
            ].join( '' )
            :[
                '<div class="pull-left">',
                    '<button class="switch-to btn btn-default">', _l( 'Switch to' ), '</button>',
                '</div>'
            ].join( '' );
    },

    /**  */
    renderPanel : function renderPanel( speed ){
        speed = ( speed !== undefined )?( speed ):( 'fast' );
        this.panel.setElement( this.$panel() ).render( speed );
        return this;
    },

    // ------------------------------------------------------------------------ behaviors and events
    /**  */
    events : {
        'click .switch-to.btn'      : function(){ this.model.setAsCurrent(); },
        'click .delete-history.btn' : function(){
                var column = this,
                    xhr;
                if( this.model.get( 'deleted' ) ){
                    xhr = this.model.undelete();
                } else {
                    xhr = this.model._delete();
                }
//TODO: better error handler
                xhr.fail( function( xhr, status, error ){
                    alert( _l( 'Could not delete the history' ) + ':\n' + error );
                })
                .done( function( data ){
                    column.render();
                });
            },
        'click .copy-history.btn'   : 'copy'
    },

    // ------------------------------------------------------------------------ non-current controls
    /**  */
    copy : function copy(){
        historyCopyDialog( this.model );
    },

    // ------------------------------------------------------------------------ misc
    /**  */
    toString : function(){
        return 'HistoryPanelColumn(' + ( this.panel? this.panel : '' ) + ')';
    }
});


//==============================================================================
// a multi-history view that displays histories in full
var MultiPanelColumns = Backbone.View.extend( baseMVC.LoggableMixin ).extend({

    //logger : console,

    // ------------------------------------------------------------------------ set up
    /**  */
    initialize : function initialize( options ){
        options = options || {};
        this.log( this + '.init', options );

        // --- instance vars
        if( !options.currentHistoryId ){
            throw new Error( this + ' requires a currentHistoryId in the options' );
        }
        this.currentHistoryId = options.currentHistoryId;

//TODO: move these to some defaults
        this.options = {
            columnWidth     : 312,
            borderWidth     : 1,
            columnGap       : 8,

            headerHeight    : 29,
            footerHeight    : 0,

            controlsHeight  : 20
        };

        /** the order that the collection is rendered in */
        this.order = options.order || 'update';

        /** named ajax queue for loading hdas */
        this.hdaQueue = new ajaxQueue.NamedAjaxQueue( [], false );

        // --- set up models, sub-views, and listeners
        /** the original unfiltered and unordered collection of histories */
        this.collection = null;
        this.setCollection( options.histories || [] );

        ///** the column views of histories */
        //this.columns = [];
        /** model id to column map */
        this.columnMap = {};
//TODO: why create here?
        this.createColumns( options.columnOptions );

        this.setUpListeners();
    },

    /**  */
    setUpListeners : function setUpListeners(){
        //var multipanel = this;
        //multipanel.log( 'setUpListeners', multipanel );
    },

    // ------------------------------------------------------------------------ collection
    /**  */
    setCollection : function setCollection( models ){
        var multipanel = this;
        multipanel.stopListening( multipanel.collection );
        multipanel.collection = models;
//TODO: slow... esp. on start up
        //if( multipanel.order !== 'update' ){
            multipanel.sortCollection( multipanel.order, { silent: true });
        //}
        multipanel.setUpCollectionListeners();
        multipanel.trigger( 'new-collection', multipanel );
        return multipanel;
    },

    setUpCollectionListeners : function(){
        var multipanel = this,
            collection = multipanel.collection;
        multipanel.listenTo( collection, {
            // handle addition of histories, triggered by column copy and create new
            'add': multipanel.addAsCurrentColumn,
            // handle setting a history as current, triggered by history.setAsCurrent
            'set-as-current': multipanel.setCurrentHistory,
            // handle deleting a history (depends on whether panels is including deleted or not)
            'change:deleted': multipanel.handleDeletedHistory,

            'sort' : function(){ multipanel.renderColumns( 0 ); },

            //'all' : function(){
            //    console.info( 'collection:', arguments );
            //}
        });
    },

    /**  */
    setCurrentHistory : function setCurrentHistory( history ){
        var oldCurrentColumn = this.columnMap[ this.currentHistoryId ];
        if( oldCurrentColumn ){
            oldCurrentColumn.currentHistory = false;
            oldCurrentColumn.$el.height( '' );
        }

        this.currentHistoryId = history.id;
        var newCurrentColumn = this.columnMap[ this.currentHistoryId ];
        newCurrentColumn.currentHistory = true;

        this.sortCollection();

////TODO: this actually means these render twice (1st from setCollection) - good enough for now
        //if( oldCurrentColumn ){ oldCurrentColumn.render().delegateEvents(); }
        //TODO:?? this occasionally causes race with hdaQueue
        //newCurrentColumn.panel.render( 'fast' ).delegateEvents();

        multipanel._recalcFirstColumnHeight();
        return newCurrentColumn;
    },

    /**  */
    handleDeletedHistory : function handleDeletedHistory( history ){
        if( history.get( 'deleted' ) ){
            this.log( 'handleDeletedHistory', this.collection.includeDeleted, history );
            var multipanel = this;
                column = multipanel.columnMap[ history.id ];
            if( !column ){ return; }

            // if it's the current column, create a new, empty history as the new current
            if( column.model.id === this.currentHistoryId ){
//TODO: figuring out the order of async here is tricky - for now let the user handle the two step process
                //multipanel.collection.create().done( function(){
                //    if( !multipanel.collection.includeDeleted ){ multipanel.removeColumn( column, false ); }
                //});
            } else if( !multipanel.collection.includeDeleted ){
                multipanel.removeColumn( column );
            }
//TODO: prob. be done better
       }
    },

    /**  */
    sortCollection : function( order, options ){
        order = order || this.order;
        var currentHistoryId = this.currentHistoryId;

        //note: h.id !== currentHistoryId allows the sort to put the current history first
        switch( order ){
            case 'name':
                //TODO: we can use a 2 arg version and return 1/0/-1
                //this.collection.comparator = function( h1, h2 ){
                this.collection.comparator = function( h ){
//TODO: this won't do reverse order well
                    return [ h.id !== currentHistoryId, h.get( 'name' ).toLowerCase() ];
                };
                break;
            case 'size':
                this.collection.comparator = function( h ){
//console.debug( 'name sort', arguments )
                    return [ h.id !== currentHistoryId, h.get( 'size' ) ];
                };
                break;
            default:
                this.collection.comparator = function( h ){
                    return [ h.id !== currentHistoryId, Date( h.get( 'update_time' ) ) ];
                };
        }
        //NOTE: auto fires 'sort' from collection
        this.collection.sort( options );
        return this.collection;
    },

    /**  */
    setOrder : function( order ){
        if( [ 'update', 'name', 'size' ].indexOf( order ) === -1 ){
            order = 'update';
        }
        this.order = order;
        this.sortCollection();
        return this;
    },

    /**  */
    create : function( ev ){
        return this.collection.create({ current: true });
    },

    ///**  */
    //deleteCurrent : function deleteCurrent(){
    //    var multipanel = this,
    //        currentColumn = multipanel.columnMap[ multipanel.currentHistoryId ];
    //    currentColumn.model._delete()
    //        .done( function(){
    //            multipanel.create();
    //        });
    //},

    // ------------------------------------------------------------------------ columns
    /** create columns from collection */
    createColumns : function createColumns( columnOptions ){
        columnOptions = columnOptions || {};
        var multipanel = this;
        // clear column map
        this.columnMap = {};
        multipanel.collection.each( function( model, i ){
            var column = multipanel.createColumn( model, columnOptions );
            multipanel.columnMap[ model.id ] = column;
        });
    },

    /**  */
    createColumn : function createColumn( history, options ){
        // options passed can be re-used, so extend them before adding the model to prevent pollution for the next
        options = _.extend( {}, options, { model: history });
        var column = new HistoryPanelColumn( options );
        if( history.id === this.currentHistoryId ){ column.currentHistory = true; }
        this.setUpColumnListeners( column );
        return column;
    },

    columnMapLength : function(){
        return Object.keys( this.columnMap ).length;
    },

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

    sortedColumns : function(){
        var multipanel = this;
        var sorted = this.collection.map( function( history, index ){
            return multipanel.columnMap[ history.id ];
        });
        return sorted;
    },

    /**  */
    addColumn : function add( history, render ){
//console.debug( 'adding column for:', history );
        render = render !== undefined? render: true;
        var newColumn = this.createColumn( history );
        this.columnMap[ history.id ] = newColumn;
        if( render ){
            this.renderColumns();
        }
        return newColumn;
    },

    /**  */
    addAsCurrentColumn : function add( history ){
//console.log( 'adding current column for:', history );
        var multipanel = this,
            newColumn = this.addColumn( history, false );
        this.setCurrentHistory( history );
        newColumn.once( 'rendered', function(){
            multipanel.queueHdaFetch( newColumn );
        });
        return newColumn;
    },

    /**  */
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

    /**  */
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
                var toCopy = multipanel._dropData.filter( function( json ){
                    return ( _.isObject( json ) && json.id && json.model_class === 'HistoryDatasetAssociation' );
                });
                multipanel._dropData = null;

                var queue = new ajaxQueue.NamedAjaxQueue();
                toCopy.forEach( function( hda ){
                    queue.add({
                        name : 'copy-' + hda.id,
                        fn : function(){
                            return panel.model.contents.copy( hda.id );
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

    // ------------------------------------------------------------------------ render
    /**  */
    render : function render( speed ){
        speed = speed !== undefined? speed: this.fxSpeed;
        var multipanel = this;

        multipanel.log( multipanel + '.render' );
        multipanel.$el.html( multipanel.template( multipanel.options ) );
        //console.debug( multipanel.$( '.loading-overlay' ).fadeIn( 0 ) );
        multipanel.renderColumns( speed );
        //console.debug( multipanel.$( '.loading-overlay' ).fadeOut( 'fast' ) );

        // set the columns to full height allowed and set up behaviors for thie multipanel
        multipanel.setUpBehaviors();
//TODO: wrong - has to wait for columns to render
        multipanel.trigger( 'rendered', multipanel );
        return multipanel;
    },

    /**  */
    template : function template( options ){
        options = options || {};
        var html = [];
        if( this.options.headerHeight ){
            html = html.concat([
                '<div class="loading-overlay flex-row"><div class="loading-overlay-message">loading...</div></div>',
                '<div class="header flex-column-container">',
                    '<div class="header-control header-control-left flex-column">',
                        '<button class="done btn btn-default">', _l( 'Done' ), '</button>',
                        '<button class="include-deleted btn btn-default"></button>',
                        '<div class="order btn-group">',
                            '<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown">',
                                _l( 'Order histories by' ) + '... <span class="caret"></span>',
                            '</button>',
                            '<ul class="dropdown-menu" role="menu">',
                                '<li><a href="javascript:void(0);" class="order-update">',
                                    _l( 'Time of last update' ),
                                '</a></li>',
                                '<li><a href="javascript:void(0);" class="order-name">',
                                    _l( 'Name' ),
                                '</a></li>',
                                '<li><a href="javascript:void(0);" class="order-size">',
                                    _l( 'Size' ),
                                '</a></li>',
                            '</ul>',
                        '</div>',
                        '<div id="search-histories" class="header-search"></div>',
                    '</div>',
                    '<div class="header-control header-control-center flex-column">',
                        '<div class="header-info">',
                        '</div>',
                    '</div>',
                    '<div class="header-control header-control-right flex-column">',
                        '<div id="search-datasets" class="header-search"></div>',
                        '<button id="toggle-deleted" class="btn btn-default">',
                            _l( 'Include deleted datasets' ),
                        '</button>',
                        '<button id="toggle-hidden" class="btn btn-default">',
                            _l( 'Include hidden datasets' ),
                        '</button>',
                    '</div>',
                '</div>'
            ]);
        }

        html = html.concat([
            '<div class="outer-middle flex-row flex-row-container">',
                '<div class="middle flex-column-container flex-row"></div>',
            '</div>',
            '<div class="footer flex-column-container">','</div>'
        ]);
        return $( html.join( '' ) );
    },

    /**  */
    renderColumns : function renderColumns( speed ){
        speed = speed !== undefined? speed: this.fxSpeed;
        //this.log( 'renderColumns:', speed );
        // render columns and track the total number rendered, firing an event when all are rendered
        var multipanel = this,
            sortedAndFiltered = multipanel.sortedFilteredColumns();
//console.log( '\t columnMapLength:', this.columnMapLength(), this.columnMap );
        //this.log( '\t sortedAndFiltered:', sortedAndFiltered );

        // set up width based on collection size
//console.debug( '(render) width before:', multipanel.$( '.middle' ).width() )
        multipanel.$( '.middle' ).width( sortedAndFiltered.length
            //TODO: magic number 16 === the amount that safely prevents stacking of columns when adding a new one
            * ( this.options.columnWidth + this.options.columnGap ) + this.options.columnGap + 16 );
//console.debug( '(render) width now:', multipanel.$( '.middle' ).width() )

//console.debug( 'sortedAndFiltered:', sortedAndFiltered )
        //multipanel.$( '.middle' ).empty();

//        this.$( '.middle' ).html( sortedAndFiltered.map( function( column, i ){
//            return column.$el.hide();
//        }));
//        sortedAndFiltered.forEach( function( column, i ){
////console.debug( 'rendering:', column, i )
//            //multipanel.$( '.middle' ).append( column.$el.hide() );
//            column.delegateEvents();
////TODO: current column in-view is never fired
//            multipanel.renderColumn( column, speed ).$el.show();
//        });

//        var $els = sortedAndFiltered.map( function( column, i ){
////console.debug( 'rendering:', column, i )
//            multipanel.renderColumn( column, speed );
//            return column.$el;
//        });
//// this breaks the event map
//        //this.$( '.middle' ).html( $els );
//// this doesn't
//        this.$( '.middle' ).append( $els );

        var $middle = multipanel.$( '.middle' );
        $middle.empty();
        sortedAndFiltered.forEach( function( column, i ){
//console.debug( 'rendering:', column, i, column.panel )

            column.$el.appendTo( $middle );
            column.delegateEvents();
            multipanel.renderColumn( column, speed );

            //column.$el.hide().appendTo( $middle );
            //multipanel.renderColumn( column, speed );
            //    //.panel.on( 'all', function(){
            //    //    console.debug( 'column rendered:', arguments );
            //    //});
            //// this won't work until we checkColumnsInView after the render
            ////column.$el.fadeIn( speed );
            //column.$el.show();
        });
        //this.log( 'column rendering done' );

//TODO: event columns-rendered

        if( this.searchFor && sortedAndFiltered.length <= 1 ){
        } else {
            multipanel.checkColumnsInView();
            this._recalcFirstColumnHeight();
        }

        return sortedAndFiltered;
    },

    /**  */
    renderColumn : function( column, speed ){
        speed = speed !== undefined? speed: this.fxSpeed;
        return _.delay( function(){ return column.render( speed ); }, 0 );
    },

//TODO: combine the following two more sensibly
//TODO: could have HistoryContents.haveDetails return false
//      if column.model.contents.length === 0 && !column.model.get( 'empty' ) then just check that
    /**  */
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

    /**  */
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

    /**  */
    allColumns : function allColumns(){
        return [ this.currentColumn ].concat( this.columns );
    },

    renderInfo : function( msg ){
        this.$( '.header .header-info' ).text( msg );
    },

    // ------------------------------------------------------------------------ events/behaviors
    /**  */
    events : {
        'click .done.btn'                                       : function(){ window.location = '/'; },
        //'click .done.btn'                                       : function(){ window.history.back(); },
        'click .create-new.btn'                                 : 'create',
        'click .order .order-update'                            : function( e ){ this.setOrder( 'update' ); },
        'click .order .order-name'                              : function( e ){ this.setOrder( 'name' ); },
        'click .order .order-size'                              : function( e ){ this.setOrder( 'size' ); }

        //'dragstart .list-item .title-bar'                       : function( e ){ console.debug( 'ok' ); }
    },

    includeDeletedHistories : function(){
        //TODO: better through API/limit+offset
        window.location += ( /\?/.test( window.location.toString() ) )?( '&' ):( '?' )
            + 'include_deleted_histories=True';
    },

    excludeDeletedHistories : function(){
        //TODO: better through API/limit+offset
        window.location = window.location.toString().replace( /[&\?]include_deleted_histories=True/g, '' );
    },

    /**  */
    setUpBehaviors : function(){
        var multipanel = this;

//TODO: currently doesn't need to be a mode button
        multipanel.$( '.include-deleted' ).modeButton({
            initialMode         : this.collection.includeDeleted? 'exclude' : 'include',
            switchModesOnClick  : false,
            modes: [
                { mode: 'include', html: _l( 'Include deleted histories' ),
                  onclick: _.bind( multipanel.includeDeletedHistories, multipanel )
                },
                { mode: 'exclude', html: _l( 'Exclude deleted histories' ),
                  onclick: _.bind( multipanel.excludeDeletedHistories, multipanel )
                }
            ]
        });

        // input to search histories
        multipanel.$( '#search-histories' ).searchInput({
            name        : 'search-histories',
            placeholder : _l( 'search histories' ),
            onsearch    : function( searchFor ){
                multipanel.searchFor = searchFor;
                multipanel.filters = [ function(){
                    return this.model.get( 'name' ).indexOf( multipanel.searchFor ) !== -1;
                }];
                multipanel.renderColumns( 0 );
            },
            onclear     : function( searchFor ){
                multipanel.searchFor = null;
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
                multipanel.searchFor = searchFor;
                multipanel.sortedFilteredColumns().forEach( function( column ){
                    column.panel.searchItems( searchFor );
                    // load details for them that need
                    multipanel.queueHdaFetchDetails( column );
                });
                multipanel.hdaQueue.progress( function( progress ){
                    multipanel.renderInfo([
                        _l( 'loading' ), ( progress.curr + 1 ), _l( 'of' ), progress.total
                    ].join( ' ' ));
                });
                multipanel.hdaQueue.deferred.done( function(){
                    multipanel.renderInfo( '' );
                    multipanel.$( '#search-datasets' ).searchInput( 'toggle-loading' );
                });
            },
            onsearch    : function( searchFor ){
                multipanel.searchFor = searchFor;
                multipanel.sortedFilteredColumns().forEach( function( column ){
                    column.panel.searchItems( searchFor );
                });
            },
            onclear     : function( searchFor ){
                multipanel.searchFor = null;
                multipanel.sortedFilteredColumns().forEach( function( column ){
                    column.panel.clearSearch();
                });
            }
        });

//TODO: each panel stores the hidden/deleted state - and that isn't reflected in the buttons
        multipanel.$( '#toggle-deleted' ).modeButton({
            initialMode : 'include',
            modes: [
                { mode: 'exclude', html: _l( 'Exclude deleted datasets' ) },
                { mode: 'include', html: _l( 'Include deleted datasets' ) }
            ]
        }).click( function(){
            var show = $( this ).modeButton( 'getMode' ).mode === 'exclude';
            multipanel.sortedFilteredColumns().forEach( function( column, i ){
                _.delay( function(){
                    column.panel.toggleShowDeleted( show, false );
                }, i * 200 );
            });
        });

        multipanel.$( '#toggle-hidden' ).modeButton({
            initialMode : 'include',
            modes: [
                { mode: 'exclude', html: _l( 'Exclude hidden datasets' ) },
                { mode: 'include', html: _l( 'Include hidden datasets' ) }
            ]
        }).click( function(){
            var show = $( this ).modeButton( 'getMode' ).mode === 'exclude';
            multipanel.sortedFilteredColumns().forEach( function( column, i ){
                _.delay( function(){
                    column.panel.toggleShowHidden( show, false );
                }, i * 200 );
            });
        });

        // resize first (fixed position) column on page resize
        $( window ).resize( function(){
            multipanel._recalcFirstColumnHeight();
        });

        // when scrolling - check for histories now in view: they will fire 'in-view' and queueHdaLoading if necc.
//TODO:?? might be able to simplify and not use pub-sub
        var debouncedInView = _.debounce( _.bind( this.checkColumnsInView, this ), 100 );
        this.$( '.middle' ).parent().scroll( debouncedInView );
    },

    //panelRenderQueue : function( columns, fn, args, renderEventName ){
    //},

    _recalcFirstColumnHeight : function(){
        //var currentColumn = this.columnMap[ this.currentHistoryId ];
        //if( !currentColumn ){ return; }
        var $firstColumn = this.$( '.history-column' ).first(),
            middleHeight = this.$( '.middle' ).height(),
            controlHeight = $firstColumn.find( '.panel-controls' ).height();
        $firstColumn.height( middleHeight )
            .find( '.inner' ).height( middleHeight - controlHeight );

//console.debug( '$firstColumn:', $firstColumn );
        //var currentColumn = this.columnMap[ this.currentHistoryId ];
        //if( !currentColumn ){ return; }
        //var middleHeight = this.$( '.middle' ).height(),
        //    controlHeight = currentColumn.$( '.panel-controls' ).height();
        //currentColumn.$el.height( middleHeight )
        //    .find( '.inner' ).height( middleHeight - controlHeight );
    },

    _viewport : function(){
        var viewLeft = this.$( '.middle' ).parent().offset().left;
        return { left: viewLeft, right: viewLeft + this.$( '.middle' ).parent().width() };
    },

    /**  */
    columnsInView : function(){
        //TODO: uses offset which is render intensive
//TODO: 2N - could use arg filter (sortedFilteredColumns( filter )) instead
        var vp = this._viewport();
        return this.sortedFilteredColumns().filter( function( column ){
            return column.currentHistory || column.inView( vp.left, vp.right );
        });
    },

//TODO: sortByInView - return cols in view, then others
    /**  */
    checkColumnsInView : function(){
//console.debug( 'checking columns in view', this.columnsInView() );
        this.columnsInView().forEach( function( column ){
            column.trigger( 'in-view', column );
        });
    },

    /**  */
    currentColumnDropTargetOn : function(){
        var currentColumn = this.columnMap[ this.currentHistoryId ];
        if( !currentColumn ){ return; }
//TODO: fix this - shouldn't need monkeypatch
        currentColumn.panel.dataDropped = function( data ){};
        currentColumn.panel.dropTargetOn();
    },

    /**  */
    currentColumnDropTargetOff : function(){
        var currentColumn = this.columnMap[ this.currentHistoryId ];
        if( !currentColumn ){ return; }
        currentColumn.panel.dataDropped = HPANEL_EDIT.HistoryPanelEdit.prototype.dataDrop;
        currentColumn.panel.dropTargetOff();
    },

    // ------------------------------------------------------------------------ misc
    /**  */
    toString : function(){
        return 'MultiPanelColumns(' + ( this.columns? this.columns.length : 0 ) + ')';
    }
});


//==============================================================================
    return {
        MultiPanelColumns : MultiPanelColumns
    };
});
