<%inherit file="/embed_base.mako"/>
<%!
	from galaxy.web.framework.helpers import iff
%>

<%def name="render_item_specific_title_links( dataset )">
    <a href="${h.url_for( controller='/dataset', action='display', dataset_id=trans.security.encode_id( dataset.id ), to_ext=dataset.ext )}" title="Save dataset" class="icon-button disk tooltip"></a>
</%def>

<%def name="render_summary_content( dataset, data )">
##    <ul>
##        <li>Format : ${dataset.extension}
##        <pre>${dataset.peek}</pre>
##    </ul>
</%def>
