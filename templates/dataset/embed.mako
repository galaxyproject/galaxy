<%inherit file="/embed_base.mako"/>
<%!
	from galaxy.web.framework.helpers import iff
%>

<%def name="content( dataset, data )">
    %if annotation:
        <div class='annotation'>${annotation}</div>
    %endif
    <ul>
        <li>Format : ${dataset.extension}
    </ul>
</%def>
