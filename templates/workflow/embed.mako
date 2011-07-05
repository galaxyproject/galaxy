<%inherit file="/embed_base.mako"/>
<%!
	from galaxy.web.framework.helpers import iff
%>

<%def name="render_summary_content( workflow, steps )">

##    <ul>
##        <% num_steps = len ( steps ) %>
##        <li>${num_steps} step${iff( num_steps != 1, "s", "" )}
##        <li>Operations: ...
##    </ul>
</%def>
