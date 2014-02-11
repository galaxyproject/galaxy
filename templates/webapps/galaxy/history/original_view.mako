<%namespace file="/display_common.mako" import="get_history_link, get_controller_name" />
<%namespace file="/root/history_common.mako" import="render_dataset" />
<%namespace file="/tagging_common.mako" import="render_individual_tagging_element, render_community_tagging_element" />

<%!
    def inherit(context):
        if context.get('use_panels'):
            return '/webapps/galaxy/base_panels.mako'
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/jquery/jstorage" )}
    <script type="text/javascript">
        $(function() {
            init_history_items( $("div.historyItemWrapper"), false, "nochanges" );
            $( '#switch-to-link' ).click( function( event ){
                var galaxy = window.Galaxy || window.parent.Galaxy;
                if( galaxy ){
                    galaxy.currHistoryPanel.switchToHistory( '${ trans.security.encode_id( history.id ) }' );
                }
            });
            $( '#refresh' ).click( function( event ){ window.location.reload( true ); })
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "history", "autocomplete_tagging" )}

    <style type="text/css">

        /* these don't appear to be used? */
        .page-body
        {
            padding: 10px;
            float: left;
            width: 65%;
        }
        .page-meta
        {
            float: right;
            width: 27%;
            padding: 0.5em;
            margin: 0.25em;
            vertical-align: text-top;
            border: 2px solid #DDDDDD;
            border-top: 4px solid #DDDDDD;
        }


        body {
            padding: 0px;
            margin: 0px;
        }

        div.unified-panel-body {
            position: absolute;
            top: 0px;
            width: 100%;
        }

        #history-name-area {
            margin: 12px 0px 0px 16px;
            font-size: 120%;
        }
        #top-links {
            margin: 4px 0px 8px 16px;
        }

        .historyItemContainer {
            /*padding-right: 3px;*/
        }
        .historyItemBody {
            display: none;
        }
        div.historyItemWrapper {
            margin: 0px 4px 0px 4px ;
            border-left: 1px solid #999999;
            border-right: 1px solid #999999;
        }
        /* TODO: unify with other history css and into .less */
    </style>

    <noscript>
        <style>
            .historyItemBody {
                display: block;
            }
        </style>
    </noscript>
</%def>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
%>
</%def>

<%def name="body()">
    ${center_panel()}
</%def>

<%def name="center_panel()">
    ## Get URL to other histories owned by user that owns this history.
    <%
        ##TODO: is there a better way to create this URL? Can't use 'f-username' as a key b/c it's not a valid identifier.
        href_to_published_histories = h.url_for( controller='/history', action='list_published')
        if history.user is not None:
            href_to_user_histories = h.url_for( controller='/history', action='list_published', xxx=history.user.username).replace( 'xxx', 'f-username')
        else:
            href_to_user_histories = h.url_for( controller='/history', action='list_published' )##should this instead be be None or empty string?
    %>
    
    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">
            ## Render view of history.
            <div id="history-name-area" class="historyLinks" style="color: gray; font-weight: bold; padding: 0px 0px 5px 0px">
                <div id="history-name">${history.get_display_name()}</div>
            </div>

            <div id="top-links" class="historyLinks" style="padding: 0px 0px 5px 0px">
                %if not history.purged and history.user != trans.user:
                    ##TODO: need to remove _top
                    <a href="${h.url_for(controller='history', action='imp', id=trans.security.encode_id(history.id) )}"
                       >import and start using history</a> |
                    <a id="refresh" href="javascript:void(0)" >${_('refresh')}</a> |
                %endif
                %if not history.purged and history.user == trans.user:
                    <a id="switch-to-link" href="javascript:void(0)">${_('switch to this history')}</a> |
                    <a id="refresh" href="javascript:void(0)" >${_('refresh')}</a> |
                %endif
                %if show_deleted:
                    <a href="${h.url_for(controller='history', action='view', id=trans.security.encode_id(history.id), show_deleted=False, use_panels=use_panels )}">${_('hide deleted')}</a> |
                %else:
                    <a href="${h.url_for(controller='history', action='view', id=trans.security.encode_id(history.id), show_deleted=True, use_panels=use_panels )}">${_('show deleted')}</a> |
                %endif
                <a href="#" class="toggle">collapse all</a>
            </div>

            %if history.deleted:
                <div class="warningmessagesmall">
                    ${_('You are currently viewing a deleted history!')}
                </div>
                <p></p>
            %endif

            %if not datasets:
                <div class="infomessagesmall" id="emptyHistoryMessage">

            %else:    
                ## Render requested datasets, ordered from newest to oldest
                %for data in datasets:
                    %if data.visible:
                        <div class="historyItemContainer visible-right-border" id="historyItemContainer-${data.id}">
                            ${render_dataset( data, data.hid, show_deleted_on_refresh = show_deleted, for_editing=False )}
                        </div>
                    %endif
                %endfor

                <div class="infomessagesmall" id="emptyHistoryMessage" style="display:none;">
            %endif
                    ${_("Your history is empty. Click 'Get Data' on the left pane to start")}
                </div>
        </div>
    </div>
</%def>
