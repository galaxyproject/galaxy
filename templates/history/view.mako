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
    ${h.js( "galaxy.base", "jquery", "json2", "jstorage" )}
    <script type="text/javascript">
        $(function() {
            init_history_items( $("div.historyItemWrapper"), false, "nochanges" );
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "history", "autocomplete_tagging" )}
    <style type="text/css">
        .historyItemContainer {
          padding-right: 3px;
          border-right-style: solid;
          border-right-color: #66AA66;
        }
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
    </style>

    <style>
        .historyItemBody {
            display: none;
        }
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
    
    <div class="unified-panel-header" unselectable="on">
    </div>
    
    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">
            ## Render view of history.
            <div id="top-links" class="historyLinks" style="padding: 0px 0px 5px 0px">
                %if not history.purged:
                    <a href="${h.url_for( action='imp', id=trans.security.encode_id(history.id) )}">import and start using history</a> |
                    <a href="${get_history_link( history )}">${_('refresh')}</a> |
                %endif
                %if show_deleted:
                    <a href="${h.url_for( id=trans.security.encode_id(history.id), show_deleted=False, use_panels=use_panels )}">${_('hide deleted')}</a> |
                %else:
                    <a href="${h.url_for( id=trans.security.encode_id(history.id), show_deleted=True, use_panels=use_panels )}">${_('show deleted')}</a> |
                %endif
                <a href="#" class="toggle">collapse all</a>
            </div>

            <div id="history-name-area" class="historyLinks" style="color: gray; font-weight: bold; padding: 0px 0px 5px 0px">
                <div id="history-name">${history.get_display_name()}</div>
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
