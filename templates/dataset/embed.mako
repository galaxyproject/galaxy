<%inherit file="/embed_base.mako"/>
<%!
	from galaxy.web.framework.helpers import iff
%>

<%def name="render_item_links( dataset )">
    <a href="${h.url_for( controller='/dataset', action='display', dataset_id=trans.security.encode_id( dataset.id ), to_ext=dataset.ext )}" title="Save dataset" class="icon-button disk tooltip"></a>
    ## Links for importing and viewing an item.
    <a href="${h.url_for( controller='/dataset', action='imp', dataset_id=trans.security.encode_id( item.id ) )}" title="Import dataset" class="icon-button import tooltip"></a>
    <a class="icon-button go-to-full-screen tooltip" href="${h.url_for( controller='/dataset', action='display_by_username_and_slug', username=dataset.history.user.username, slug=trans.security.encode_id( dataset.id ) )}" title="Go to dataset"></a>
    
</%def>

<%def name="render_summary_content( dataset, data )">
##    <ul>
##        <li>Format : ${dataset.extension}
##        <pre>${dataset.peek}</pre>
##    </ul>
</%def>
