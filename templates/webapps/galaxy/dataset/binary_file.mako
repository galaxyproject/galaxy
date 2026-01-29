<%inherit file="/base.mako"/>
<%namespace file="/dataset/display.mako" import="render_deleted_data_message" />

${ render_deleted_data_message( data ) }

<div class="warningmessagelarge">
    This is a binary (or unknown to Galaxy) dataset of size ${ file_size }. Preview is not implemented for this filetype. Displaying
    %if truncated:
first 100KB
    %endif
 as ASCII text<br/>
    <a href="${h.url_for( controller='dataset', action='display', dataset_id=trans.security.encode_id( data.id ), to_ext=data.ext )}">Download</a>
</div>

<pre>
${ util.unicodify( file_contents ) | h }
</pre>
