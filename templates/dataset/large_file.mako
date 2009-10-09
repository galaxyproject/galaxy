<%inherit file="/base.mako"/>

<div class="warningmessagelarge">
    This dataset is large and only the first megabyte is shown below.<br />
    <a href="${h.url_for( controller='dataset', action='display', dataset_id=data.id, show_all=True )}">Show all</a> |
    <a href="${h.url_for( controller='root', action='display', id=data.id, tofile='yes', toext=data.ext )}">Save</a>
</div>

<pre>
${ truncated_data }
</pre>
