var LeftPanel = require( 'layout/panel' ).LeftPanel,
    Tools = require( 'mvc/tool/tools' ),
    Upload = require( 'mvc/upload/upload-view' ),
    _l = require( 'utils/localization' );

/* Builds the tool menu panel on the left of the analysis page */
var ToolPanel = LeftPanel.extend({

    title : _l( 'Tools' ),

    initialize: function( options ){
        LeftPanel.prototype.initialize.call( this, options );
        this.log( this + '.initialize:', options );

        /** @type {Object[]} descriptions of user's workflows to be shown in the tool menu */
        this.stored_workflow_menu_entries = options.stored_workflow_menu_entries || [];

        // create tool search, tool panel, and tool panel view.
        var tool_search = new Tools.ToolSearch({
            hidden      : false
        });
        var tools = new Tools.ToolCollection( options.toolbox );
        this.tool_panel = new Tools.ToolPanel({
            tool_search : tool_search,
            tools       : tools,
            layout      : options.toolbox_in_panel
        });
        this.tool_panel_view = new Tools.ToolPanelView({ model: this.tool_panel });

        // add upload modal
        this.uploadButton = new Upload({
            nginx_upload_path   : options.nginx_upload_path,
            ftp_upload_site     : options.ftp_upload_site,
            default_genome      : options.default_genome,
            default_extension   : options.default_extension,
        });
    },

    render : function(){
        var self = this;
        LeftPanel.prototype.render.call( self );
        self.$( '.panel-header-buttons' ).append( self.uploadButton.$el );

        // if there are tools, render panel and display everything
        if (self.tool_panel.get( 'layout' ).size() > 0) {
            self.tool_panel_view.render();
            //TODO: why the hide/show?
            self.$( '.toolMenu' ).show();
        }
        self.$( '.toolMenuContainer' ).prepend( self.tool_panel_view.$el );

        self._renderWorkflowMenu();

        // if a tool link has the minsizehint attribute, handle it here (gen. by hiding the tool panel)
        self.$( 'a[minsizehint]' ).click( function() {
            if ( parent.handle_minwidth_hint ) {
                parent.handle_minwidth_hint( $( self ).attr( 'minsizehint' ) );
            }
        });
    },

    /** build the dom for the workflow portion of the tool menu */
    _renderWorkflowMenu : function(){
        var self = this;
        // add internal workflow list
        self.$( '#internal-workflows' ).append( self._templateTool({
            title   : _l( 'All workflows' ),
            href    : 'workflow/list_for_run'
        }));
        _.each( self.stored_workflow_menu_entries, function( menu_entry ){
            self.$( '#internal-workflows' ).append( self._templateTool({
                title : menu_entry.stored_workflow.name,
                href  : 'workflow/run?id=' + menu_entry.encoded_stored_workflow_id
            }));
        });
    },

    /** build a link to one tool */
    _templateTool: function( tool ) {
        return [
            '<div class="toolTitle">',
                // global
                '<a href="', Galaxy.root, tool.href, '" target="galaxy_main">', tool.title, '</a>',
            '</div>'
        ].join('');
    },

    /** override to include inital menu dom and workflow section */
    _templateBody : function(){
        return [
            '<div class="unified-panel-body unified-panel-body-background">',
                '<div class="toolMenuContainer">',
                    '<div class="toolMenu" style="display: none">',
                        '<div id="search-no-results" style="display: none; padding-top: 5px">',
                            '<em><strong>', _l( 'Search did not match any tools.' ), '</strong></em>',
                        '</div>',
                    '</div>',
                    '<div class="toolSectionPad"/>',
                    '<div class="toolSectionPad"/>',
                    '<div class="toolSectionTitle" id="title_XXinternalXXworkflow">',
                        '<span>', _l( 'Workflows' ), '</span>',
                    '</div>',
                    '<div id="internal-workflows" class="toolSectionBody">',
                        '<div class="toolSectionBg"/>',
                    '</div>',
                '</div>',
            '</div>'
        ].join('');
    },

    toString : function(){ return 'ToolPanel'; }
});

module.exports = ToolPanel;
