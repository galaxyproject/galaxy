<%inherit file="/embed_base.mako"/>
<%!
	from galaxy.web.framework.helpers import iff
%>

<%def name="content( dataset, data )">
    <ul>
        <li>Format : ${dataset.extension}
    </ul>
</%def>
