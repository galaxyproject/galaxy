<%inherit file="/embed_base.mako"/>
<%!
	from galaxy.web.framework.helpers import iff
%>

<%def name="content( workflow, steps )">
    %if annotation:
        <div class='annotation'>${annotation}</div>
    %endif
    <ul>
        <% num_steps = len ( steps ) %>
        <li>${num_steps} step${iff( num_steps != 1, "s", "" )}
        <li>Operations: ...
    </ul>
</%def>
