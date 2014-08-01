define([
    "mvc/dataset/states",
    "mvc/history/history-content-base-view",
    "mvc/data",
    "utils/localization"
], function( STATES, HCONTENT_BASE_VIEW, DATA, _l ){
/* global Backbone */
//==============================================================================
var _super = HCONTENT_BASE_VIEW.HistoryContentBaseView;
/** @class Read only view for HistoryDatasetAssociation.
 *  @name HDABaseView
 *
 *  @augments HistoryContentBaseView
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var HDABaseView = _super.extend(
/** @lends HDABaseView.prototype */{

    /** logger used to record this.log messages, commonly set to console */
    // comment this out to suppress log output
    //logger              : console,

    tagName     : "div",
    className   : "dataset hda history-content",
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

        _super.prototype.initialize.call( this, attributes );

        /** list of rendering functions for the default, primary icon-buttons. */
        this.defaultPrimaryActionButtonRenderers = [
            this._render_showParamsButton
        ];

        /** where should pages from links be displayed? (default to new tab/window) */
        this.linkTarget = attributes.linkTarget || '_blank';
        
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
     *  @returns {Object} this HDABaseView
     */
    render : function( fade ){
        //HACK: hover exit doesn't seem to be called on prev. tooltips when RE-rendering - so: no tooltip hide
        // handle that here by removing previous view's tooltips
        this.$el.find("[title]").tooltip( "destroy" );
        // re-get web controller urls for functions relating to this hda. (new model data may have changed this)
        this.urls = this.model.urls();

        return _super.prototype.render.call( this, fade );
    },
    
    // ................................................................................ titlebar buttons
    /** In this override, render the dataset display button
     *  @returns {jQuery} rendered DOM
     */
    _render_primaryActions : function(){
        // render just the display for read-only
        return [ this._render_displayButton() ];
    },

    /** Render icon-button to display this hda in the galaxy main iframe.
     *  @returns {jQuery} rendered DOM
     */
    _render_displayButton : function(){
        // don't show display if not viewable or not accessible
        // (do show if in error, running)
        if( ( this.model.get( 'state' ) === STATES.NOT_VIEWABLE )
        ||  ( this.model.get( 'state' ) === STATES.DISCARDED )
        ||  ( !this.model.get( 'accessible' ) ) ){
            return null;
        }
        
        var displayBtnData = {
            target      : this.linkTarget,
            classes     : 'display-btn'
        };

        // show a disabled display if the data's been purged
        if( this.model.get( 'purged' ) ){
            displayBtnData.disabled = true;
            displayBtnData.title = _l( 'Cannot display datasets removed from disk' );
            
        // disable if still uploading
        } else if( this.model.get( 'state' ) === STATES.UPLOAD ){
            displayBtnData.disabled = true;
            displayBtnData.title = _l( 'This dataset must finish uploading before it can be viewed' );

        // disable if still new
        } else if( this.model.get( 'state' ) === STATES.NEW ){
            displayBtnData.disabled = true;
            displayBtnData.title = _l( 'This dataset is not yet viewable' );

        } else {
            displayBtnData.title = _l( 'View data' );
            
            // default link for dataset
            displayBtnData.href  = this.urls.display;
            
            // add frame manager option onclick event
            var self = this;
            displayBtnData.onclick = function( ev ){
                if( Galaxy.frame && Galaxy.frame.active ){
                    // Create frame with TabularChunkedView.
                    Galaxy.frame.add({
                        title       : "Data Viewer: " + self.model.get( 'name' ),
                        type        : "other",
                        content     : function( parent_elt ){
                            var new_dataset = new DATA.TabularDataset({ id: self.model.get( 'id' ) });
                            $.when( new_dataset.fetch() ).then( function(){
                                DATA.createTabularDatasetChunkedView({
                                    model: new_dataset,
                                    parent_elt: parent_elt,
                                    embedded: true,
                                    height: '100%'
                                });
                            });
                        }
                    });
                    ev.preventDefault();
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
                    'class="icon-btn download-btn">',
                    '<span class="fa fa-floppy-o"></span>',
                '</a>'
            ].join( '' ) );
        }

        //  or a popupmenu with links to download assoc. meta files (if there are meta files)
        //TODO: Popupmenu
        var menuId = 'dataset-' + this.model.get( 'id' ) + '-popup',
            html = [
                '<div popupmenu="' + menuId + '">',
                    '<a href="' + urls.download + '">', _l( 'Download dataset' ), '</a>',
                    '<a>' + _l( 'Additional files' ) + '</a>',

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
                        'class="icon-btn download-btn">',
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
    _renderBody : function(){
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
        $body.find( '.actions .left' ).append(
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
            '<div>' + _l( 'This is a new dataset and not all of its data are available yet' ) + '</div>',
            this.defaultPrimaryActionButtonRenderers
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
        $body.find( '.actions .left' ).append(
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
    events : _.extend( _.clone( _super.prototype.events ), {
    }),

    /** Override for expanding hda details (within the panel)
     *      note: in this override, the fetch for details does *not* fire a change event (silent == true)
     *  @fires expanded when a body has been expanded
     */
    expand : function(){
        var hdaView = this;

        function _renderBodyAndExpand(){
            hdaView.$el.children( '.details' ).replaceWith( hdaView._renderBody() );
            //NOTE: needs to be set after the above or the slide will not show
            hdaView.expanded = true;
            hdaView.$el.children( '.details' ).slideDown( hdaView.fxSpeed, function(){
                    hdaView.trigger( 'expanded', hdaView );
                });
        }
        // fetch first if no details in the model
        if( this.model.inReadyState() && !this.model.hasDetails() ){
            this.model.fetch({ silent: true }).always( function( model ){
                // re-render urls based on new hda data
                hdaView.urls = hdaView.model.urls();
                _renderBodyAndExpand();
            });
        } else {
            _renderBodyAndExpand();
        }
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
//TODO: possibly break these out into a sep. module
var skeletonTemplate = _.template([
'<div class="dataset hda">',
    '<div class="warnings">',
        // error during index fetch - show error on dataset
        '<% if( hda.error ){ %>',
            '<div class="errormessagesmall">',
                _l( 'There was an error getting the data for this dataset' ), ': <%- hda.error %>',
            '</div>',
        '<% } %>',

        '<% if( hda.deleted ){ %>',
            // purged and deleted
            '<% if( hda.purged ){ %>',
                '<div class="purged-msg warningmessagesmall"><strong>',
                    _l( 'This dataset has been deleted and removed from disk' ) + '.',
                '</strong></div>',

            // deleted not purged
            '<% } else { %>',
                '<div class="deleted-msg warningmessagesmall"><strong>',
                    _l( 'This dataset has been deleted' ) + '.',
                '</strong></div>',
            '<% } %>',
        '<% } %>',

        // hidden
        '<% if( !hda.visible ){ %>',
            '<div class="hidden-msg warningmessagesmall"><strong>',
                _l( 'This dataset has been hidden' ) + '.',
            '</strong></div>',
        '<% } %>',
    '</div>',

    // multi-select checkbox
    '<div class="selector">',
        '<span class="fa fa-2x fa-square-o"></span>',
    '</div>',
    // space for title bar buttons
    '<div class="primary-actions"></div>',

    // adding a tabindex here allows focusing the title bar and the use of keydown to expand the dataset display
    '<div class="title-bar clear" tabindex="0">',
        '<span class="state-icon"></span>',
        '<div class="title">',
            //TODO: remove whitespace and use margin-right
            '<span class="hid"><%- hda.hid %></span> ',
            '<span class="name"><%- hda.name %></span>',
        '</div>',
    '</div>',

    '<div class="details"></div>',
'</div>'
].join( '' ));

var bodyTemplate = _.template([
'<div class="details">',
    '<% if( hda.body ){ %>',
        '<div class="summary">',
            '<%= hda.body %>',
        '</div>',
        '<div class="actions clear">',
            '<div class="left"></div>',
            '<div class="right"></div>',
        '</div>',

    '<% } else { %>',
        '<div class="summary">',
            '<% if( hda.misc_blurb ){ %>',
                '<div class="blurb">',
                    '<span class="value"><%- hda.misc_blurb %></span>',
                '</div>',
            '<% } %>',

            '<% if( hda.data_type ){ %>',
                '<div class="datatype">',
                    '<label class="prompt">', _l( 'format' ), '</label>',
                    '<span class="value"><%- hda.data_type %></span>',
                '</div>',
            '<% } %>',

            '<% if( hda.metadata_dbkey ){ %>',
                '<div class="dbkey">',
                    '<label class="prompt">', _l( 'database' ), '</label>',
                    '<span class="value">',
                        '<%- hda.metadata_dbkey %>',
                    '</span>',
                '</div>',
            '<% } %>',

            '<% if( hda.misc_info ){ %>',
                '<div class="info">',
                    '<span class="value"><%- hda.misc_info %></span>',
                '</div>',
            '<% } %>',
        '</div>',
        // end dataset-summary

        '<div class="actions clear">',
            '<div class="left"></div>',
            '<div class="right"></div>',
        '</div>',

        '<% if( !hda.deleted ){ %>',
            '<div class="tags-display"></div>',
            '<div class="annotation-display"></div>',

            '<div class="display-applications">',
                //TODO: the following two should be compacted
                '<% _.each( hda.display_apps, function( app ){ %>',
                    '<div class="display-application">',
                        '<span class="display-application-location"><%- app.label %></span> ',
                        '<span class="display-application-links">',
                            '<% _.each( app.links, function( link ){ %>',
                                '<a target="<%= link.target %>" href="<%= link.href %>">',
                                    '<% print( _l( link.text ) ); %>',
                                '</a> ',
                            '<% }); %>',
                        '</span>',
                    '</div>',
                '<% }); %>',

                '<% _.each( hda.display_types, function( app ){ %>',
                    '<div class="display-application">',
                        '<span class="display-application-location"><%- app.label %></span> ',
                        '<span class="display-application-links">',
                            '<% _.each( app.links, function( link ){ %>',
                                '<a target="<%= link.target %>" href="<%= link.href %>">',
                                    '<% print( _l( link.text ) ); %>',
                                '</a> ',
                            '<% }); %>',
                        '</span>',
                    '</div>',
                '<% }); %>',
            '</div>',

            '<div class="dataset-peek">',
                '<% if( hda.peek ){ %>',
                    '<pre class="peek"><%= hda.peek %></pre>',
                '<% } %>',
            '</div>',

        '<% } %>',
        // end if !deleted

    '<% } %>',
    // end if body
'</div>'
].join( '' ));

HDABaseView.templates = HDABaseView.prototype.templates = {
    // we override here in order to pass the localizer (_L) into the template scope - since we use it as a fn within
    skeleton            : function( hdaJSON ){
        return skeletonTemplate({ _l: _l, hda: hdaJSON });
    },
    body                : function( hdaJSON ){
        return bodyTemplate({ _l: _l, hda: hdaJSON });
    }
};

//==============================================================================
    return {
        HDABaseView  : HDABaseView
    };
});
