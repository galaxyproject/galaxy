define([
    "mvc/dataset/hda-model"
], function( hdaModel ){
/* global Backbone, LoggableMixin, HistoryDatasetAssociation, HDABaseView */
//==============================================================================
/** @class Read only view for HistoryDatasetAssociation.
 *  @name HDABaseView
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDABaseView = Backbone.View.extend( LoggableMixin ).extend(
/** @lends HDABaseView.prototype */{

    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    tagName     : "div",
    className   : "dataset hda history-panel-hda",
    id          : function(){ return 'hda-' + this.model.get( 'id' ); },

    fxSpeed     : 'fast',

    // ......................................................................... set up
    /** Set up the view, cache url templates, bind listeners
     *  @param {Object} attributes
     *  @config {Object} urlTemplates nested object containing url templates for this view
     *  @throws 'needs urlTemplates' if urlTemplates isn't present
     *  @see Backbone.View#initialize
     */
    initialize  : function( attributes ){
        if( attributes.logger ){ this.logger = this.model.logger = attributes.logger; }
        this.log( this + '.initialize:', attributes );

        /** list of rendering functions for the default, primary icon-buttons. */
        this.defaultPrimaryActionButtonRenderers = [
            this._render_showParamsButton
        ];

        /** where should pages from links be displayed? (default to new tab/window) */
        this.linkTarget = attributes.linkTarget || '_blank';
        
        /** is the view currently in selection mode? */
        this.selectable = attributes.selectable || false;
        //this.log( '\t selectable:', this.selectable );
        /** is the view currently selected? */
        this.selected   = attributes.selected || false;
        //this.log( '\t selected:', this.selected );
        /** is the body of this hda view expanded/not? */
        this.expanded   = attributes.expanded || false;
        //this.log( '\t expanded:', this.expanded );
        /** is the body of this hda view expanded/not? */
        this.draggable  = attributes.draggable || false;
        //this.log( '\t draggable:', this.draggable );
        
        this._setUpListeners();
    },

    /** event listeners */
    _setUpListeners : function(){

        // re-rendering on any model changes
        this.model.on( 'change', function( model, options ){

            // if the model moved into the ready state and is expanded without details, fetch those details now
            if( this.model.changedAttributes().state && this.model.inReadyState()
            &&  this.expanded && !this.model.hasDetails() ){
                this.model.fetch(); // will render automatically (due to lines below)

            } else {
                this.render();
            }
        }, this );

        //this.on( 'all', function( event ){
        //    this.log( event );
        //}, this );
    },

    // ......................................................................... render main
    /** Render this HDA, set up ui.
     *  @param {Boolean} fade   whether or not to fade out/in when re-rendering
     *  @fires rendered when rendered
     *  @fires rendered:ready when first rendered and NO running HDAs
     *  @returns {Object} this HDABaseView
     */
    render : function( fade ){
        fade = ( fade === undefined )?( true ):( fade );
        var view = this;

        //HACK: hover exit doesn't seem to be called on prev. tooltips when RE-rendering - so: no tooltip hide
        // handle that here by removing previous view's tooltips
        this.$el.find("[title]").tooltip( "destroy" );

        // re-get web controller urls for functions relating to this hda. (new model data may have changed this)
        this.urls = this.model.urls();
        var $newRender = this._buildNewRender();

        // fade the old render out (if desired)
        if( fade ){
            $( view ).queue( function( next ){ this.$el.fadeOut( view.fxSpeed, next ); });
        }
        // empty the old render, update to any new HDA state, swap in the new render contents, handle multi-select
        $( view ).queue( function( next ){
            this.$el.empty()
                .attr( 'class', view.className ).addClass( 'state-' + view.model.get( 'state' ) )
                .append( $newRender.children() );
            if( this.selectable ){ this.showSelector( 0 ); }
            next();
        });
        // fade the new in
        if( fade ){
            $( view ).queue( function( next ){ this.$el.fadeIn( view.fxSpeed, next ); });
        }
        // trigger an event to know we're ready
        $( view ).queue( function( next ){
            this.trigger( 'rendered', view );
            if( this.model.inReadyState() ){
                this.trigger( 'rendered:ready', view );
            }
            if( this.draggable ){ this.draggableOn(); }
            next();
        });
        return this;
    },
    
    _buildNewRender : function(){
        // create a new render using a skeleton template, render title buttons, render body, and set up events, etc.
        var $newRender = $( HDABaseView.templates.skeleton( this.model.toJSON() ) );
        $newRender.find( '.dataset-primary-actions' ).append( this._render_titleButtons() );
        $newRender.children( '.dataset-body' ).replaceWith( this._render_body() );
        this._setUpBehaviors( $newRender );
        //this._renderSelectable( $newRender );
        return $newRender;
    },

    /** set up js behaviors, event handlers for elements within the given container
     *  @param {jQuery} $container jq object that contains the elements to process (defaults to this.$el)
     */
    _setUpBehaviors : function( $container ){
        $container = $container || this.$el;
        // set up canned behavior on children (bootstrap, popupmenus, editable_text, etc.)
        make_popup_menus( $container );
        $container.find( '[title]' ).tooltip({ placement : 'bottom' });
    },

    // ................................................................................ titlebar buttons
    /** Render icon-button group for the common, most easily accessed actions.
     *  @returns {jQuery} rendered DOM
     */
    _render_titleButtons : function(){
        // render just the display for read-only
        return [ this._render_displayButton() ];
    },

    /** Render icon-button to display this hda in the galaxy main iframe.
     *  @returns {jQuery} rendered DOM
     */
    _render_displayButton : function(){
        // don't show display if not viewable or not accessible
        // (do show if in error, running)
        if( ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NOT_VIEWABLE )
        ||  ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.DISCARDED )
        ||  ( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.NEW )
        ||  ( !this.model.get( 'accessible' ) ) ){
            return null;
        }
        
        var displayBtnData = {
            target      : this.linkTarget,
            classes     : 'dataset-display'
        };

        // show a disabled display if the data's been purged
        if( this.model.get( 'purged' ) ){
            displayBtnData.disabled = true;
            displayBtnData.title = _l( 'Cannot display datasets removed from disk' );
            
        // disable if still uploading
        } else if( this.model.get( 'state' ) === hdaModel.HistoryDatasetAssociation.STATES.UPLOAD ){
            displayBtnData.disabled = true;
            displayBtnData.title = _l( 'This dataset must finish uploading before it can be viewed' );

        } else {
            displayBtnData.title = _l( 'View data' );
            
            // default link for dataset
            displayBtnData.href  = this.urls.display;
            
            // add frame manager option onclick event
            var self = this;
            displayBtnData.onclick = function(){
                if( Galaxy.frame && Galaxy.frame.active ){
                    Galaxy.frame.add({
                        title       : "Data Viewer: " + self.model.get('name'),
                        type        : "url",
                        content     : self.urls.display
                    });
                }
            };
        }
        displayBtnData.faIcon = 'fa-eye';
        return faIconButton( displayBtnData );
    },

    // ......................................................................... primary actions
    /** Render icon-button/popupmenu to download the data (and/or the associated meta files (bai, etc.)) for this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_downloadButton : function(){
        // don't show anything if the data's been purged
        if( this.model.get( 'purged' ) || !this.model.hasData() ){ return null; }
        var urls = this.urls,
            meta_files = this.model.get( 'meta_files' );

        // return either: a single download icon-button (if there are no meta files)
        if( _.isEmpty( meta_files ) ){
            return $([
                '<a href="' + urls.download + '" title="' + _l( 'Download' ) + '" ',
                    'class="icon-btn dataset-download-btn">',
                    '<span class="fa fa-floppy-o"></span>',
                '</a>'
            ].join( '' ) );
        }

        //  or a popupmenu with links to download assoc. meta files (if there are meta files)
        //TODO: Popupmenu
        var menuId = 'dataset-' + this.model.get( 'id' ) + '-popup',
            html = [
                '<div popupmenu="' + menuId + '">',
                    '<a href="' + urls.download + '">', _l( 'Download Dataset' ), '</a>',
                    '<a>' + _l( 'Additional Files' ) + '</a>',

                    _.map( meta_files, function( meta_file ){
                        return [
                            '<a class="action-button" href="', urls.meta_download + meta_file.file_type, '">',
                                _l( 'Download' ), ' ', meta_file.file_type,
                            '</a>'
                        ].join( '' );
                    }).join( '\n' ),
                '</div>',

                '<div class="icon-btn-group">',
                    '<a href="' + urls.download + '" title="' + _l( 'Download' ) + '" ',
                        'class="icon-btn dataset-download-btn">',
                        '<span class="fa fa-floppy-o"></span>',
                    // join these w/o whitespace or there'll be a gap when rendered
                    '</a><a class="icon-btn popup" id="' + menuId + '">',
                        '<span class="fa fa-caret-down"></span>',
                    '</a>',
                '</div>'
            ].join( '\n' );
        return $( html );
    },
    
    /** Render icon-button to show the input and output (stdout/err) for the job that created this hda.
     *  @returns {jQuery} rendered DOM
     */
    _render_showParamsButton : function(){
        // gen. safe to show in all cases
        return faIconButton({
            title       : _l( 'View details' ),
            classes     : 'dataset-params-btn',
            href        : this.urls.show_params,
            target      : this.linkTarget,
            faIcon      : 'fa-info-circle'
        });
    },
    
    // ......................................................................... state body renderers
    /** Render the enclosing div of the hda body and, if expanded, the html in the body
     *  @returns {jQuery} rendered DOM
     */
    _render_body : function(){
        var $body = $( '<div>Error: unknown dataset state "' + this.model.get( 'state' ) + '".</div>' ),
            // cheesy: get function by assumed matching name
            renderFn = this[ '_render_body_' + this.model.get( 'state' ) ];
        if( _.isFunction( renderFn ) ){
            $body = renderFn.call( this );
        }
        this._setUpBehaviors( $body );

        // only render the body html if it's being shown
        if( this.expanded ){
            $body.show();
        }
        return $body;
    },

    /** helper for rendering the body in the common cases */
    _render_stateBodyHelper : function( body, primaryButtonArray ){
        primaryButtonArray = primaryButtonArray || [];
        var view = this,
            $body = $( HDABaseView.templates.body( _.extend( this.model.toJSON(), { body: body })));
        $body.find( '.dataset-actions .left' ).append(
            _.map( primaryButtonArray, function( renderingFn ){
                return renderingFn.call( view );
            })
        );
        return $body;
    },

    /** Render a new dataset - this should be a transient state that's never shown
     *      in case it does tho, we'll make sure there's some information here
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_new : function(){
        return this._render_stateBodyHelper(
            '<div>' + _l( 'This is a new dataset and not all of its data are available yet' ) + '</div>'
        );
    },
    /** Render inaccessible, not-owned by curr user. */
    _render_body_noPermission : function(){
        return this._render_stateBodyHelper(
            '<div>' + _l( 'You do not have permission to view this dataset' ) + '</div>'
        );
    },
    /** Render an HDA which was deleted during upload. */
    _render_body_discarded : function(){
        return this._render_stateBodyHelper(
            '<div>' + _l( 'The job creating this dataset was cancelled before completion' ) + '</div>',
            this.defaultPrimaryActionButtonRenderers
        );
    },
    /** Render an HDA whose job is queued. */
    _render_body_queued : function(){
        return this._render_stateBodyHelper(
            '<div>' + _l( 'This job is waiting to run' ) + '</div>',
            this.defaultPrimaryActionButtonRenderers
        );
    },
    /** Render an HDA still being uploaded. */
    _render_body_upload : function(){
        return this._render_stateBodyHelper( '<div>' + _l( 'This dataset is currently uploading' ) + '</div>' );
    },
    /** Render an HDA where the metadata is still being determined. */
    _render_body_setting_metadata : function(){
        return this._render_stateBodyHelper( '<div>' + _l( 'Metadata is being auto-detected' ) + '</div>' );
    },
    /** Render an HDA whose job is running. */
    _render_body_running : function(){
        return this._render_stateBodyHelper(
            '<div>' + _l( 'This job is currently running' ) + '</div>',
            this.defaultPrimaryActionButtonRenderers
        );
    },
    /** Render an HDA whose job is paused. */
    _render_body_paused: function(){
        return this._render_stateBodyHelper(
            '<div>' + _l( 'This job is paused. Use the "Resume Paused Jobs" in the history menu to resume' ) + '</div>',
            this.defaultPrimaryActionButtonRenderers
        );
    },

    /** Render an HDA whose job has failed. */
    _render_body_error : function(){
        var html = [
            '<span class="help-text">', _l( 'An error occurred with this dataset' ), ':</span>',
            '<div class="job-error-text">', $.trim( this.model.get( 'misc_info' ) ), '</div>'
        ].join( '' );
        if( !this.model.get( 'purged' ) ){
            html = '<div>' + this.model.get( 'misc_blurb' ) + '</div>' + html;
        }
        return this._render_stateBodyHelper( html,
            [ this._render_downloadButton ].concat( this.defaultPrimaryActionButtonRenderers )
        );
    },
        
    /** Render an empty/no data HDA. */
    _render_body_empty : function(){
        return this._render_stateBodyHelper(
            '<div>' + _l( 'No data' ) + ': <i>' + this.model.get( 'misc_blurb' ) + '</i></div>',
            this.defaultPrimaryActionButtonRenderers
        );
    },
        
    /** Render an HDA where the metadata wasn't produced correctly. */
    _render_body_failed_metadata : function(){
        // add a message box about the failure at the top of the body then render the remaining body as STATES.OK
        var $warning = $( '<div class="warningmessagesmall"></div>' )
                .append( $( '<strong/>' ).text( _l( 'An error occurred setting the metadata for this dataset' ) ) ),
            $body = this._render_body_ok();
        $body.prepend( $warning );
        return $body;
    },
        
    /** Render an HDA that's done running and where everything worked.
     *  @param {jQuery} parent DOM to which to append this body
     */
    _render_body_ok : function(){
        // most common state renderer and the most complicated
        var view = this,
            $body = $( HDABaseView.templates.body( this.model.toJSON() ) ),
            // prepend the download btn to the defaults and render
            btnRenderers = [ this._render_downloadButton ].concat( this.defaultPrimaryActionButtonRenderers );
        $body.find( '.dataset-actions .left' ).append(
            _.map( btnRenderers, function( renderingFn ){
                return renderingFn.call( view );
            }));

        // return shortened form if del'd (no display apps or peek?)
        if( this.model.isDeletedOrPurged() ){
            return $body;
        }

        //this._render_displayApps( $body.children( '.dataset-display-applications' ) );
        return $body;
    },
    
    // ......................................................................... events
    /** event map */
    events : {
        // expand the body when the title is clicked or when in focus and space or enter is pressed
        'click .dataset-title-bar'      : 'toggleBodyVisibility',
        'keydown .dataset-title-bar'    : 'toggleBodyVisibility',

        // dragging - don't work, originalEvent === null
        //'dragstart .dataset-title-bar'  : 'dragStartHandler',
        //'dragend .dataset-title-bar'    : 'dragEndHandler'

        // toggle selected state
        'click .dataset-selector'       : 'toggleSelect'
    },

    /** Show or hide the body/details of an HDA.
     *      note: if the model does not have detailed data, fetch that data before showing the body
     *  @param {Event} event the event that triggered this (@link HDABaseView#events)
     *  @param {Boolean} expanded if true, expand; if false, collapse
     *  @fires body-expanded when a body has been expanded
     *  @fires body-collapsed when a body has been collapsed
     */
    toggleBodyVisibility : function( event, expand ){
        // bail (with propagation) if keydown and not space or enter
        var KEYCODE_SPACE = 32, KEYCODE_RETURN = 13;
        if( event && ( event.type === 'keydown' )
        &&  !( event.keyCode === KEYCODE_SPACE || event.keyCode === KEYCODE_RETURN ) ){
            return true;
        }

        var $body = this.$el.find( '.dataset-body' );
        expand = ( expand === undefined )?( !$body.is( ':visible' ) ):( expand );
        if( expand ){
            this.expandBody();
        } else {
            this.collapseBody();
        }
        return false;
    },

    /** Render and show the full, detailed body of this view including extra data and controls.
     *  @fires body-expanded when a body has been expanded
     */
    expandBody : function(){
        var hdaView = this;

        function _renderBodyAndExpand(){
            hdaView.$el.children( '.dataset-body' ).replaceWith( hdaView._render_body() );
            hdaView.$el.children( '.dataset-body' ).slideDown( hdaView.fxSpeed, function(){
                    hdaView.expanded = true;
                    hdaView.trigger( 'body-expanded', hdaView.model.get( 'id' ) );
                });

            //hdaView.render( false ).$el.children( '.dataset-body' ).slideDown( hdaView.fxSpeed, function(){
            //    hdaView.expanded = true;
            //    hdaView.trigger( 'body-expanded', hdaView.model.get( 'id' ) );
            //});
        }
        // fetch first if no details in the model
        if( this.model.inReadyState() && !this.model.hasDetails() ){
            this.model.fetch({ silent: true }).always( function( model ){
                _renderBodyAndExpand();
            });
        } else {
            _renderBodyAndExpand();
        }
    },

    /** Hide the body/details of an HDA.
     *  @fires body-collapsed when a body has been collapsed
     */
    collapseBody : function(){
        var hdaView = this;
        this.$el.children( '.dataset-body' ).slideUp( hdaView.fxSpeed, function(){
            hdaView.expanded = false;
            hdaView.trigger( 'body-collapsed', hdaView.model.get( 'id' ) );
        });
    },

    // ......................................................................... selection
    /** display a (fa-icon) checkbox on the left of the hda that fires events when checked
     *      Note: this also hides the primary actions
     */
    showSelector : function( speed ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );

        // make sure selected state is represented properly
        if( this.selected ){
            this.select( null, true );
        }

        // create a jq fx queue to do this sequentially: fadeout the buttons, embiggen the selector
        var hdaView = this,
            SELECTOR_WIDTH = 32;

        if( speed ){
            this.$el.queue( 'fx', function( next ){
                $( this ).find( '.dataset-primary-actions' ).fadeOut( speed, next );
            });
            this.$el.queue( 'fx', function( next ){
                $( this ).find( '.dataset-selector' ).show().animate({ width: SELECTOR_WIDTH }, speed, next );
                $( this ).find( '.dataset-title-bar' ).animate({ 'margin-left': SELECTOR_WIDTH }, speed, next );
                hdaView.selectable = true;
                hdaView.trigger( 'selectable', true, hdaView );
            });
        // no animation
        } else {
            this.$el.find( '.dataset-primary-actions' ).hide();
            this.$el.find( '.dataset-selector' ).show().css({ width : SELECTOR_WIDTH });
            this.$el.find( '.dataset-title-bar' ).show().css({ 'margin-left' : SELECTOR_WIDTH });
            hdaView.selectable = true;
            hdaView.trigger( 'selectable', true, hdaView );
        }
    },

    /** remove the selection checkbox */
    hideSelector : function( speed ){
        speed = ( speed !== undefined )?( speed ):( this.fxSpeed );

        // reverse the process from showSelect
        this.selectable = false;
        this.trigger( 'selectable', false, this );

        if( speed ){
            this.$el.queue( 'fx', function( next ){
                $( this ).find( '.dataset-title-bar' ).show().css({ 'margin-left' : '0' });
                $( this ).find( '.dataset-selector' ).animate({ width: '0px' }, speed, function(){
                    $( this ).hide();
                    next();
                });
            });
            this.$el.queue( 'fx', function( next ){
                $( this ).find( '.dataset-primary-actions' ).fadeIn( speed, next );
            });

        // no animation
        } else {
            $( this ).find( '.dataset-selector' ).css({ width : '0px' }).hide();
            $( this ).find( '.dataset-primary-actions' ).show();
        }
    },

    toggleSelector : function( speed ){
        if( !this.$el.find( '.dataset-selector' ).is( ':visible' ) ){
            this.showSelector( speed );
        } else {
            this.hideSelector( speed );
        }
    },

    /** event handler for selection (also programmatic selection)
     */
    select : function( event ){
        // switch icon, set selected, and trigger event
        this.$el.find( '.dataset-selector span' )
            .removeClass( 'fa-square-o' ).addClass( 'fa-check-square-o' );
        if( !this.selected ){
            this.trigger( 'selected', this );
            this.selected = true;
        }
        return false;
    },

    /** event handler for clearing selection (also programmatic deselection)
     */
    deselect : function( event ){
        // switch icon, set selected, and trigger event
        this.$el.find( '.dataset-selector span' )
            .removeClass( 'fa-check-square-o' ).addClass( 'fa-square-o' );
        if( this.selected ){
            this.trigger( 'de-selected', this );
            this.selected = false;
        }
        return false;
    },

    toggleSelect : function( event ){
        if( this.selected ){
            this.deselect( event );
        } else {
            this.select( event );
        }
    },

    // ......................................................................... drag/drop
    draggableOn : function(){
        this.draggable = true;
        //TODO: I have no idea why this doesn't work with the events hash or jq.on()...
        //this.$el.find( '.dataset-title-bar' )
        //    .attr( 'draggable', true )
        //    .bind( 'dragstart', this.dragStartHandler, false )
        //    .bind( 'dragend',   this.dragEndHandler,   false );
        this.dragStartHandler = _.bind( this._dragStartHandler, this );
        this.dragEndHandler   = _.bind( this._dragEndHandler,   this );

        var titleBar = this.$el.find( '.dataset-title-bar' ).attr( 'draggable', true ).get(0);
        titleBar.addEventListener( 'dragstart', this.dragStartHandler, false );
        titleBar.addEventListener( 'dragend',   this.dragEndHandler,   false );
    },
    draggableOff : function(){
        this.draggable = false;
        var titleBar = this.$el.find( '.dataset-title-bar' ).attr( 'draggable', false ).get(0);
        titleBar.removeEventListener( 'dragstart', this.dragStartHandler, false );
        titleBar.removeEventListener( 'dragend',   this.dragEndHandler,   false );
    },
    toggleDraggable : function(){
        if( this.draggable ){
            this.draggableOff();
        } else {
            this.draggableOn();
        }
    },
    _dragStartHandler : function( event ){
        //console.debug( 'dragStartHandler:', this, event, arguments )
        this.trigger( 'dragstart', this );
        event.dataTransfer.effectAllowed = 'move';
        //TODO: all except IE: should be 'application/json', IE: must be 'text'
        event.dataTransfer.setData( 'text', JSON.stringify( this.model.toJSON() ) );
        return false;
    },
    _dragEndHandler : function( event ){
        this.trigger( 'dragend', this );
        //console.debug( 'dragEndHandler:', event )
        return false;
    },

    // ......................................................................... removal
    /** Remove this view's html from the DOM and remove all event listeners.
     *  @param {Function} callback  an optional function called when removal is done
     */
    remove : function( callback ){
        var hdaView = this;
        this.$el.fadeOut( hdaView.fxSpeed, function(){
            hdaView.$el.remove();
            hdaView.off();
            if( callback ){ callback(); }
        });
    },

    // ......................................................................... misc
    /** String representation */
    toString : function(){
        var modelString = ( this.model )?( this.model + '' ):( '(no model)' );
        return 'HDABaseView(' + modelString + ')';
    }
});

//------------------------------------------------------------------------------ TEMPLATES
HDABaseView.templates = {
    skeleton            : Handlebars.templates[ 'template-hda-skeleton' ],
    body                : Handlebars.templates[ 'template-hda-body' ]
};

//==============================================================================
return {
    HDABaseView  : HDABaseView
};});
