<%namespace file="/display_common.mako" import="*" />

## Some duplication with embed_base here, needed a way to override the main embedded-item html for histories
<%
    encoded_history_id = trans.security.encode_id( item.id )
    display_href = h.url_for( controller='history', action='display_by_username_and_slug',
        username=item.user.username, slug=item.slug )
%>
<div id="history-${encoded_history_id}" class='embedded-item display history'>
    <div class='title'>
        <div style="float: right;">
            <a title="View history" class="icon-button go-to-full-screen" href="${display_href}"></a>
        </div>
        <h4>
            <a class="toggle-embed" href="${display_href}" title="Show or hide history contents">
                Galaxy History | ${get_item_name( item ) | h}
            </a>
        </h4>
        %if hasattr( item, "annotation") and item.annotation:
        <div class="annotation">${ item.annotation | h }</div>
        %endif
    </div>
    <div class='summary-content'>
        ## currently, no summary content for history
    </div>
</div>
