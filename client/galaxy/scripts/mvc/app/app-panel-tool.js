define(['utils/utils', 'mvc/tools', 'mvc/upload/upload-view'],
    function( Utils, Tools, Upload ) {

    // create form view
    return Backbone.View.extend({
        initialize: function( options ) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template() );

            // create tool search, tool panel, and tool panel view.
            if ( Galaxy.user.valid || !Galaxy.config.require_login ) {
                var tool_search = new Tools.ToolSearch({
                    spinner_url : options.spinner_url,
                    search_url  : options.search_url,
                    hidden      : false
                });
                var tools = new Tools.ToolCollection( options.toolbox );
                var tool_panel = new Tools.ToolPanel({
                    tool_search : tool_search,
                    tools       : tools,
                    layout      : options.toolbox_in_panel
                });
                tool_panel_view = new Tools.ToolPanelView({ model: tool_panel });
            
                // add tool panel to Galaxy object
                Galaxy.toolPanel = tool_panel;

                // if there are tools, render panel and display everything
                if (tool_panel.get( 'layout' ).size() > 0) {
                    tool_panel_view.render();
                    this.$( '.toolMenu' ).show();
                }
                this.$el.append( tool_panel_view.$el );

                // minsize init hint
                this.$( 'a[minsizehint]' ).click( function() {
                    if ( parent.handle_minwidth_hint ) {
                        parent.handle_minwidth_hint( $(this).attr( 'minsizehint' ) );
                    }
                });

                // add upload plugin
                Galaxy.upload = new Upload( options );

                // define components (is used in app-view.js)
                this.components = {
                    header  : {
                        title   : 'Tools',
                        buttons : [ Galaxy.upload ]
                    }
                }
            }
        },

        _template: function() {
            return  '<div class="toolMenuContainer">' +
                        '<div class="toolMenu" style="display: none">' +
                            '<div id="search-no-results" style="display: none; padding-top: 5px">' +
                                '<em><strong>Search did not match any tools.</strong></em>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
            /*%if t.user:
                <div class="toolSectionPad"></div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
                  <span>Workflows</span>
                </div>
                <div id="XXinternalXXworkflow" class="toolSectionBody">
                    <div class="toolSectionBg">
                        %if t.user.stored_workflow_menu_entries:
                            %for m in t.user.stored_workflow_menu_entries:
                                <div class="toolTitle">
                                    <a href="${h.url_for( controller='workflow', action='run', id=trans.security.encode_id(m.stored_workflow_id) )}" target="galaxy_main">${ util.unicodify( m.stored_workflow.name ) | h}</a>
                                </div>
                            %endfor
                        %endif
                        <div class="toolTitle">
                            <a href="${h.url_for( controller='workflow', action='list_for_run')}" target="galaxy_main">All workflows</a>
                        </div>
                    </div>
                </div>
            %endif*/
        }
    });
});
