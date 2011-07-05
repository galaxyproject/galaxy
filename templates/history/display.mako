<%inherit file="/display_base.mako"/>
<%namespace file="/root/history_common.mako" import="render_dataset" />

## Set vars so that there's no need to change the code below.
<% 
    history = published_item 
    datasets = published_item_data
%>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "history" )}
    <style type="text/css">
        .historyItemBody {
            display: none;
        }
        .column {
            float: left;
        	padding: 10px;
        	margin: 20px;
        	background: #666;
        	border: 5px solid #ccc;
        	width: 300px;
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

<%def name="render_item_links( history )">
    <a 
        href="${h.url_for( controller='/history', action='imp', id=trans.security.encode_id(history.id) )}"
        class="icon-button import"
        ## Needed to overwide initial width so that link is floated left appropriately.
        style="width: 100%"
        title="Import history">Import history</a>
</%def>

<%def name="render_item( history, datasets )">
    %if history.deleted:
        <div class="warningmessagesmall">
            ${_('You are currently viewing a deleted history!')}
        </div>
        <p></p>
    %endif

    %if not datasets:
        <div class="infomessagesmall" id="emptyHistoryMessage">
    %else:    
        ## Render requested datasets, ordered from newest to oldest, including annotations.
        <table class="annotated-item">
            <tr><th>Dataset</th><th class="annotation">Annotation</th></tr>
            %for data in datasets:
                <tr>
                    %if data.visible:
                        <td>
                            <div class="historyItemContainer visible-right-border" id="historyItemContainer-${data.id}">
                                ${render_dataset( data, data.hid, show_deleted_on_refresh = show_deleted, for_editing=False )}
                            </div>
                        </td>
                        <td class="annotation">
                        %if hasattr( data, "annotation") and data.annotation is not None:
                            ${data.annotation}
                        %endif
                        </td>
                    %endif
                </tr>
            %endfor
        </table>
        <div class="infomessagesmall" id="emptyHistoryMessage" style="display:none;">
    %endif
            ${_("This history is empty.")}
        </div>
</%def>