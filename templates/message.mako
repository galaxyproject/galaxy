<% _=n_ %>
<%inherit file="/base.mako"/>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">
%if 'masthead' in refresh_frames:
if ( parent.frames && parent.frames.galaxy_masthead ) {
    parent.frames.galaxy_masthead.location.href="${h.url_for( controller='root', action='masthead')}";
}
else if ( parent.parent && parent.parent.frames && parent.parent.frames.galaxy_masthead ) {
    parent.parent.frames.galaxy_masthead.location.href="${h.url_for( controller='root', action='masthead')}";
}
%endif
%if 'history' in refresh_frames:
if ( parent.frames && parent.frames.galaxy_history ) {
    parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history')}";
}
%endif
%if 'tools' in refresh_frames:
if ( parent.frames && parent.frames.galaxy_tools ) {
    parent.frames.galaxy_tools.location.href="${h.url_for( controller='root', action='tool_menu')}";
}
%endif

if ( parent.handle_minwidth_hint )
{
    parent.handle_minwidth_hint( -1 );
}
</script>
</%def>

<div class="${message_type}message">${_(message)}</div>
