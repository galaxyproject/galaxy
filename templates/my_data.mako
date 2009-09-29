<%inherit file="/base.mako"/>

<%def name="stylesheets()">
    ${h.css( "base" )}
</%def>

<h2>Available Galaxy Data</h2>

<ul>
    <li><a href='${h.url_for( controller='history', action='list' )}'>Histories</li>
    <li><a href='${h.url_for( controller='dataset', action='list' )}'>Datasets</li>
</ul>

