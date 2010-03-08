<%inherit file="/embed_base.mako"/>
<%!
	from galaxy.web.framework.helpers import iff
%>

<%def name="render_summary_content( history, datasets )">

##    <ul>
##        <% num_datasets = len ( datasets ) %>
##        <li>${num_datasets} dataset${iff( num_datasets != 1, "s", "" )}
##        <li>Operations: ...
##    </ul>
</%def>
