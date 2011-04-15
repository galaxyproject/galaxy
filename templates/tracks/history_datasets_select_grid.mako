<%inherit file="/tracks/history_select_grid.mako"/>

<%def name="title()">
    <h2>History '${grid.get_current_item( trans, **kwargs ).name}'</h2>
</%def>