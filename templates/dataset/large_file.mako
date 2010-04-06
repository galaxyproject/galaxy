<%inherit file="/base.mako"/>

<div class="warningmessagelarge">
    This dataset is large and only the first megabyte is shown below.<br />
    <a href="${h.url_for( controller='dataset', action='display', dataset_id=trans.security.encode_id( data.id ), filename='' )}">Show all</a> |
    <a href="${h.url_for( controller='dataset', action='display', dataset_id=trans.security.encode_id( data.id ), to_ext=data.ext )}">Save</a>
</div>

<pre>
${ unicode( truncated_data, 'utf-8' ) | h }
</pre>
