<%inherit file="/tracks/history_select_grid.mako"/>

<%def name="title()">
    <%from galaxy.web.framework.helpers import escape%>
    <h2>History '${escape(grid.get_current_item( trans, **kwargs ).name)}'</h2>
</%def>
